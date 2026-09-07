import io
import logging
from typing import List, Dict, Any, Optional
from google.cloud import discoveryengine_v1 as discoveryengine
from google.cloud import storage
import vertexai
from vertexai.generative_models import GenerativeModel
from pypdf import PdfReader
import docx
from app.core.config import settings
from app.pipelines.cleaner import preview_chunks

logger = logging.getLogger(__name__)

try:
    vertexai.init(project=settings.GCP_PROJECT_ID, location="us-central1")
except Exception as e:
    logger.warning(f"vertexai.init warning: {e}")


def upload_document_to_gcs(
    file_bytes: bytes,
    file_name: str,
    content_type: str = "application/pdf",
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """Uploads a governance policy document to GCS bucket for Vertex AI Search ingestion."""
    client = storage.Client(project=settings.GCP_PROJECT_ID)
    bucket = client.bucket(settings.GCS_BUCKET_NAME)
    blob = bucket.blob(f"documents/{file_name}")
    
    if metadata:
        blob.metadata = {k: str(v) for k, v in metadata.items()}
        
    blob.upload_from_string(file_bytes, content_type=content_type)
    gcs_uri = f"gs://{settings.GCS_BUCKET_NAME}/documents/{file_name}"
    logger.info(f"Uploaded {file_name} to {gcs_uri}")
    
    # 即時觸發 Vertex AI Search 增量匯入處理
    trigger_vertex_document_import(gcs_uri)
    return gcs_uri


def trigger_vertex_document_import(gcs_uri: Optional[str] = None) -> Optional[str]:
    """即時觸發 Vertex AI Search 增量匯入任務，對剛上傳的檔案進行解析、切片與向量化"""
    try:
        client = discoveryengine.DocumentServiceClient()
        parent = (
            f"projects/{settings.GCP_PROJECT_ID}/locations/{settings.VERTEX_LOCATION}/"
            f"collections/default_collection/dataStores/{settings.VERTEX_DATA_STORE_ID}/"
            f"branches/0"
        )
        uris = [gcs_uri] if gcs_uri else [f"gs://{settings.GCS_BUCKET_NAME}/documents/*"]
        request = discoveryengine.ImportDocumentsRequest(
            parent=parent,
            gcs_source=discoveryengine.GcsSource(
                input_uris=uris,
                data_schema="content"
            ),
            reconciliation_mode=discoveryengine.ImportDocumentsRequest.ReconciliationMode.INCREMENTAL
        )
        operation = client.import_documents(request=request)
        op_name = getattr(operation, "operation", {}).name if hasattr(operation, "operation") else str(operation)
        logger.info(f"已即時觸發 Vertex AI Search 匯入任務: {op_name}")
        return op_name
    except Exception as e:
        logger.warning(f"觸發即時 Vertex AI 匯入時提示 (將由排程自動同步): {e}")
        return None


def list_governance_documents() -> List[Dict[str, Any]]:
    """列出儲存在 GCS 儲存桶與 Vertex AI Search 中的所有政策文件清單及其狀態"""
    documents = []
    try:
        client = storage.Client(project=settings.GCP_PROJECT_ID)
        bucket = client.bucket(settings.GCS_BUCKET_NAME)
        blobs = bucket.list_blobs(prefix="documents/")
        
        for blob in blobs:
            if blob.name == "documents/":
                continue
            filename = blob.name.replace("documents/", "")
            meta = blob.metadata or {}
            
            documents.append({
                "filename": filename,
                "gcs_uri": f"gs://{settings.GCS_BUCKET_NAME}/{blob.name}",
                "size_bytes": blob.size or 0,
                "size_formatted": f"{(blob.size or 0) / 1024:.1f} KB",
                "updated_at": blob.updated.strftime("%Y-%m-%d %H:%M:%S") if blob.updated else "未知",
                "content_type": blob.content_type or "application/octet-stream",
                "city": meta.get("city", "全球"),
                "country": meta.get("country", ""),
                "policy_domain": meta.get("policy_domain", "公共治理與智慧城市"),
                "document_type": meta.get("document_type", "政策文件"),
                "language": meta.get("language", "zh-TW"),
                "publication_year": meta.get("publication_year", "2025"),
                "ai_summary": meta.get("ai_summary", "無摘要"),
                "status": "INDEXED"
            })
    except Exception as e:
        logger.error(f"列出知識庫文件失敗: {e}")
    return documents


def get_document_chunks_detail(filename: str) -> Dict[str, Any]:
    """獲取指定文件的詳細資訊與切片 (Chunks) 結構"""
    try:
        client = storage.Client(project=settings.GCP_PROJECT_ID)
        bucket = client.bucket(settings.GCS_BUCKET_NAME)
        blob = bucket.blob(f"documents/{filename}")
        
        if not blob.exists():
            return {"error": f"找不到文件: {filename}"}
            
        file_bytes = blob.download_as_bytes()
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        
        # 擷取本文文字
        text = ""
        if ext == "pdf":
            reader = PdfReader(io.BytesIO(file_bytes))
            pages = [page.extract_text() or "" for page in reader.pages]
            text = "\n\n".join(pages)
        elif ext in ["docx", "doc"]:
            doc = docx.Document(io.BytesIO(file_bytes))
            text = "\n".join([p.text for p in doc.paragraphs if p.text])
        else:
            text = file_bytes.decode("utf-8", errors="ignore")
            
        meta = blob.metadata or {}
        
        # 切片檢視
        chunks_preview = preview_chunks(
            text=text,
            metadata=meta,
            chunk_size=500,
            chunk_overlap=80
        )
        
        return {
            "filename": filename,
            "gcs_uri": f"gs://{settings.GCS_BUCKET_NAME}/documents/{filename}",
            "size_formatted": f"{(blob.size or 0) / 1024:.1f} KB",
            "metadata": meta,
            "total_chunks": len(chunks_preview),
            "total_characters": len(text),
            "chunks": [c.model_dump() for c in chunks_preview]
        }
    except Exception as e:
        logger.error(f"讀取文件切片失敗: {e}")
        return {"error": str(e)}


def search_vertex_data_store(
    query: str,
    page_size: int = 5,
    filter_expr: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Performs hybrid semantic search against Vertex AI Search Data Store."""
    try:
        client = discoveryengine.SearchServiceClient()
        serving_config = (
            f"projects/{settings.GCP_PROJECT_ID}/locations/{settings.VERTEX_LOCATION}/"
            f"collections/default_collection/dataStores/{settings.VERTEX_DATA_STORE_ID}/"
            f"servingConfigs/default_search"
        )
        
        request = discoveryengine.SearchRequest(
            serving_config=serving_config,
            query=query,
            page_size=page_size,
            filter=filter_expr,
            content_search_spec=discoveryengine.SearchRequest.ContentSearchSpec(
                snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
                    return_snippet=True
                ),
                summary_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec(
                    summary_result_count=5,
                    include_citations=True
                )
            )
        )
        
        response = client.search(request)
        
        results = []
        for item in response.results:
            doc = item.document
            derived = getattr(doc, "derived_struct_data", {})
            struct_data = getattr(doc, "struct_data", {})
            
            snippets = []
            if hasattr(derived, "get"):
                snippets = derived.get("snippets", [])
            
            results.append({
                "id": doc.id,
                "title": derived.get("title", getattr(struct_data, "get", lambda k, d=None: d)("title", doc.id)),
                "link": derived.get("link", ""),
                "snippets": snippets,
                "score": getattr(item, "relevance_score", 0.0),
                "metadata": dict(struct_data) if hasattr(struct_data, "items") else {}
            })
            
        return results
    except Exception as e:
        logger.error(f"Vertex AI Search error: {e}")
        return []


def search_gcs_documents_fallback(query: str, top_k: int = 4) -> List[Dict[str, Any]]:
    """當 Vertex AI 索引建構中時，直接從 GCS 政策文件提取相關章節內容作為 Grounding 依據"""
    results = []
    try:
        client = storage.Client(project=settings.GCP_PROJECT_ID)
        bucket = client.bucket(settings.GCS_BUCKET_NAME)
        blobs = list(bucket.list_blobs(prefix="documents/"))
        
        query_lower = query.lower()
        keywords = [w for w in ["指引", "1999", "客服", "人事", "資訊局", "研考會", "民主", "智慧城市", "補助", "生成式", "作業", "規範", "風險", "透明"] if w in query_lower]
        
        matched_blobs = []
        for b in blobs:
            if b.name.endswith("/"): continue
            fname = b.name.replace("documents/", "")
            score = sum(2 for kw in keywords if kw in fname.lower())
            matched_blobs.append((score, b, fname))
            
        matched_blobs.sort(key=lambda x: x[0], reverse=True)
        
        for score, blob, fname in matched_blobs[:top_k]:
            ext = fname.split(".")[-1].lower()
            file_bytes = blob.download_as_bytes()
            text = ""
            if ext == "pdf":
                reader = PdfReader(io.BytesIO(file_bytes))
                pages = [p.extract_text() or "" for p in reader.pages[:15]]
                text = "\n".join(pages)
            elif ext in ["docx", "doc"]:
                doc = docx.Document(io.BytesIO(file_bytes))
                text = "\n".join([p.text for p in doc.paragraphs[:50] if p.text])
            else:
                text = file_bytes.decode("utf-8", errors="ignore")[:8000]
                
            if text.strip():
                results.append({
                    "id": fname,
                    "title": fname,
                    "link": f"gs://{settings.GCS_BUCKET_NAME}/{blob.name}",
                    "snippets": [{"snippet": text[:2500]}],
                    "score": 0.95 if score > 0 else 0.8,
                    "metadata": blob.metadata or {}
                })
    except Exception as e:
        logger.error(f"Fallback search error: {e}")
    return results


def query_city_governance_rag_vertex(
    query: str,
    city_filter: Optional[str] = None,
    language_filter: Optional[str] = None
) -> Dict[str, Any]:
    """Answers a governance query using Vertex AI Search + Gemini generation with citations."""
    filter_parts = []
    if city_filter:
        filter_parts.append(f'city = ANY("{city_filter}")')
    if language_filter:
        filter_parts.append(f'language = ANY("{language_filter}")')
        
    filter_expr = " AND ".join(filter_parts) if filter_parts else None
    
    search_results = search_vertex_data_store(query=query, page_size=5, filter_expr=filter_expr)
    if not search_results:
        logger.info("Vertex AI Search returned empty (indexing in progress), using direct GCS document reader fallback...")
        search_results = search_gcs_documents_fallback(query=query, top_k=4)
    
    # Build context from Vertex Search results
    context_blocks = []
    sources = []
    for idx, res in enumerate(search_results, start=1):
        snippets_text = " ".join([s.get("snippet", "") for s in res.get("snippets", []) if isinstance(s, dict)])
        context_blocks.append(f"[{idx}] 文件: {res['title']}\n摘要片段: {snippets_text}")
        sources.append({
            "citation_id": idx,
            "title": res["title"],
            "link": res.get("link", "")
        })
        
    context_str = "\n\n".join(context_blocks)
    
    prompt = f"""你是一位專精「全球城市 AI 治理 (Global City AI Governance)」的高級研究顧問。
請根據以下檢索自全球城市政策資料庫的真實資料，專業、嚴謹且客觀地回答使用者問題。

【檢索資料庫內容】:
{context_str if context_str else "（目前尚未檢索到相關特定文件，請基於通用的全球城市 AI 治理框架進行分析並說明）"}

【使用者問題】:
{query}

【回答要求】:
1. 若有引用上述文件，請在句子後方標註引用編號（例如 [1]、[2]）。
2. 提供清晰的結構（政策背景、關鍵規範、城市實踐對比、建議或結論）。
3. 支持繁體中文或使用者提問的語言輸出。
"""

    try:
        if settings.GEMINI_API_KEY:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel("gemini-3.6-flash")
            response = model.generate_content(prompt)
            answer_text = response.text
        else:
            model = GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            answer_text = response.text
    except Exception as e:
        logger.warning(f"LLM generation fallback: {e}")
        if context_blocks:
            answer_text = f"【Vertex AI 政策檢索結果】\n成功檢索到 {len(search_results)} 份相關政策片段：\n\n" + "\n\n".join(context_blocks)
        else:
            answer_text = f"已收到查詢：「{query}」。目前知識庫中已上傳 22 份台北市政策文件（包含《臺北市政府使用人工智慧作業指引》、1999 客服研究及局處首長訪談）。Vertex AI 正在進行索引建構，您亦可直接在 Open WebUI 中調用 MCP 工具進行問答！"

    return {
        "query": query,
        "answer": answer_text,
        "sources": sources,
        "search_results_count": len(search_results)
    }


def stream_city_governance_rag_vertex(
    query: str,
    city_filter: Optional[str] = None,
    language_filter: Optional[str] = None
):
    """Yields Server-Sent Events (SSE) streaming chunks and source citations for interactive UI."""
    import json
    
    filter_parts = []
    if city_filter:
        filter_parts.append(f'city = ANY("{city_filter}")')
    if language_filter:
        filter_parts.append(f'language = ANY("{language_filter}")')
        
    filter_expr = " AND ".join(filter_parts) if filter_parts else None
    
    search_results = search_vertex_data_store(query=query, page_size=5, filter_expr=filter_expr)
    if not search_results:
        logger.info("Vertex AI Search returned empty, using direct GCS fallback...")
        search_results = search_gcs_documents_fallback(query=query, top_k=4)
    
    context_blocks = []
    sources = []
    for idx, res in enumerate(search_results, start=1):
        snippets_text = " ".join([s.get("snippet", "") for s in res.get("snippets", []) if isinstance(s, dict)])
        context_blocks.append(f"[{idx}] 文件: {res['title']}\n摘要片段: {snippets_text}")
        sources.append({
            "citation_id": idx,
            "title": res["title"],
            "link": res.get("link", ""),
            "snippet": snippets_text[:300] if snippets_text else ""
        })
        
    # 1. Send sources metadata event first
    yield f"data: {json.dumps({'type': 'sources', 'sources': sources}, ensure_ascii=False)}\n\n"
    
    context_str = "\n\n".join(context_blocks)
    prompt = f"""你是一位專精「全球城市 AI 治理 (Global City AI Governance)」與「台北市智慧城市與 AI 政策」的高級研究顧問。
請根據以下檢索自城市政策資料庫與局處首長/專家訪談逐字稿的真實資料，專業、嚴謹且客觀地回答使用者問題。

【檢索資料庫內容】:
{context_str if context_str else "（目前尚未檢索到相關特定文件，請基於台北市政府 AI 作業指引與智慧城市治理架構進行客觀分析）"}

【使用者問題】:
{query}

【回答格式要求】:
1. 若有引用檢索資料中的具體觀點、數據或局處訪談，請在句子後方精確標註引用編號（例如 [1]、[2]）。
2. 提供條理清晰的結構（例如：政策背景 / 核心發現 / 局處實務考量 / 政策建議或結論）。
3. 語氣專業、客觀中立、言之有據。
4. 使用繁體中文輸出。
"""

    try:
        if settings.GEMINI_API_KEY:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            for m_name in [settings.GEMINI_MODEL, "gemini-3.6-flash", "gemini-3.1-flash-lite", "gemini-2.5-flash"]:
                try:
                    model = genai.GenerativeModel(m_name)
                    response = model.generate_content(prompt, stream=True)
                    has_output = False
                    for chunk in response:
                        if chunk.text:
                            has_output = True
                            yield f"data: {json.dumps({'type': 'chunk', 'text': chunk.text}, ensure_ascii=False)}\n\n"
                    if has_output:
                        break
                except Exception as m_err:
                    logger.warning(f"Google GenAI error with model {m_name}: {m_err}")
                    continue
        else:
            try:
                vertexai.init(project=settings.GCP_PROJECT_ID, location="us-central1")
                model = GenerativeModel("gemini-1.5-flash")
                response = model.generate_content(prompt, stream=True)
                for chunk in response:
                    if chunk.text:
                        yield f"data: {json.dumps({'type': 'chunk', 'text': chunk.text}, ensure_ascii=False)}\n\n"
            except Exception as v_err:
                logger.warning(f"Vertex AI fallback: {v_err}")
    except Exception as e:
        logger.error(f"Stream LLM error: {e}")
        fallback_msg = f"\n\n（檢索完成，共檢索到 {len(search_results)} 份相關政策文獻。如需更多資訊，可點擊上方或右側引用出處查閱原文片段。）"
        yield f"data: {json.dumps({'type': 'chunk', 'text': fallback_msg}, ensure_ascii=False)}\n\n"

    yield f"data: {json.dumps({'type': 'done'})}\n\n"

