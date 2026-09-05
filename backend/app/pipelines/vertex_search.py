import logging
from typing import List, Dict, Any, Optional
from google.cloud import discoveryengine_v1 as discoveryengine
from google.cloud import storage
import google.generativeai as genai
from app.core.config import settings

logger = logging.getLogger(__name__)

if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)


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

    model = genai.GenerativeModel(settings.GEMINI_PRO_MODEL)
    response = model.generate_content(prompt)
    
    return {
        "query": query,
        "answer": response.text if response else "無法生成回答",
        "sources": sources,
        "search_results_count": len(search_results)
    }
