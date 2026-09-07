import io
import logging
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Body
from fastapi.responses import StreamingResponse
from pypdf import PdfReader
import docx

from app.models.schema import (
    GovernanceMetadata,
    DocumentCleanAndTagRequest,
    DocumentCleanAndTagResponse,
    IndexDocumentResponse,
    ChunkPreview,
    ChatStreamRequest
)
from app.pipelines.cleaner import clean_and_annotate_document, preview_chunks
from app.pipelines.vertex_search import (
    upload_document_to_gcs,
    search_vertex_data_store,
    query_city_governance_rag_vertex,
    stream_city_governance_rag_vertex
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Governance RAG & Ops"])

def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    """從上傳檔案 (PDF / DOCX / TXT / MD) 擷取文字"""
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    
    if ext == "pdf":
        reader = PdfReader(io.BytesIO(file_bytes))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(pages)
    elif ext in ["docx", "doc"]:
        doc = docx.Document(io.BytesIO(file_bytes))
        return "\n".join([p.text for p in doc.paragraphs if p.text])
    else:
        return file_bytes.decode("utf-8", errors="ignore")

@router.post("/documents/clean-and-tag", response_model=DocumentCleanAndTagResponse)
async def api_clean_and_tag(request: DocumentCleanAndTagRequest):
    """使用 LLM 預清理文件並自動標註 Metadata"""
    if not request.raw_text.strip():
        raise HTTPException(status_code=400, detail="文件內容不能為空。")
    return clean_and_annotate_document(request.raw_text, request.filename)

@router.post("/documents/preview-chunks", response_model=List[ChunkPreview])
async def api_preview_chunks(
    text: str = Form(...),
    chunk_size: int = Form(500),
    chunk_overlap: int = Form(80)
):
    """預覽切片結果與長度分佈"""
    return preview_chunks(text, {}, chunk_size, chunk_overlap)

@router.post("/documents/upload-and-index", response_model=IndexDocumentResponse)
async def api_upload_and_index(
    file: UploadFile = File(...),
    city: Optional[str] = Form(None),
    country: Optional[str] = Form(None),
    policy_domain: Optional[str] = Form(None),
    document_type: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    publication_year: Optional[int] = Form(None),
    auto_ai_tag: bool = Form(True)
):
    """上傳文件至 GCS 並透過 Vertex AI Search 進行自動建構與索引"""
    try:
        content_bytes = await file.read()
        extracted_text = extract_text_from_file(content_bytes, file.filename)
        
        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="未能從檔案中讀取有效文字。")
            
        metadata_dict = {
            "city": city or "全球",
            "country": country or "",
            "policy_domain": policy_domain or "公共治理與智慧城市",
            "document_type": document_type or "政策白皮書",
            "language": language or "zh-TW",
            "publication_year": str(publication_year or 2025)
        }
        
        if auto_ai_tag:
            ai_res = clean_and_annotate_document(extracted_text, file.filename)
            meta = ai_res.suggested_metadata
            metadata_dict.update({
                "city": city or meta.city,
                "country": country or meta.country,
                "policy_domain": policy_domain or meta.policy_domain,
                "document_type": document_type or meta.document_type,
                "language": language or meta.language,
                "publication_year": str(publication_year or meta.publication_year),
                "ai_summary": meta.summary
            })
            
        # Upload original bytes to GCS bucket for Vertex AI Search ingestion
        gcs_uri = upload_document_to_gcs(
            file_bytes=content_bytes,
            file_name=file.filename,
            content_type=file.content_type or "application/pdf",
            metadata=metadata_dict
        )
        
        return IndexDocumentResponse(
            success=True,
            document_id=file.filename,
            total_chunks=1,
            message=f"文件《{file.filename}》已成功上傳至 Cloud Storage ({gcs_uri}) 並同步至 Vertex AI Search 知識庫！"
        )
    except Exception as e:
        logger.error(f"檔案上傳與索引失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rag/query")
async def api_query_rag(
    query: str = Form(...),
    city: Optional[str] = Form(None),
    language: Optional[str] = Form(None)
):
    """執行 Vertex AI Search 治理檢索與問答"""
    try:
        return query_city_governance_rag_vertex(
            query=query,
            city_filter=city,
            language_filter=language
        )
    except Exception as e:
        logger.error(f"Vertex AI RAG 查詢失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/list")
async def api_list_documents():
    """列出儲存在 GCS 儲存桶與 Vertex AI Search 中的所有政策文件清單"""
    try:
        from app.pipelines.vertex_search import list_governance_documents
        return list_governance_documents()
    except Exception as e:
        logger.error(f"獲取文件清單失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/documents/sync-vertex")
async def api_sync_vertex():
    """手動觸發 Vertex AI Search 對 GCS 儲存桶進行全量/增量掃描與索引建構"""
    try:
        from app.pipelines.vertex_search import trigger_vertex_document_import
        op = trigger_vertex_document_import()
        return {"success": True, "message": "已成功觸發 Vertex AI Search 增量建構任務！", "operation": op}
    except Exception as e:
        logger.error(f"觸發 Vertex AI 同步失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/chunks/{filename:path}")
async def api_get_document_chunks(filename: str):
    """獲取指定文件的詳細資訊與切片 (Chunks) 結構"""
    try:
        from app.pipelines.vertex_search import get_document_chunks_detail
        res = get_document_chunks_detail(filename)
        if "error" in res:
            raise HTTPException(status_code=404, detail=res["error"])
        return res
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"獲取切片資訊失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

GOVERNANCE_TOPICS = [
    {
        "id": "taipei-1999-ai",
        "category": "市民服務與智慧客服",
        "title": "1999 市民當家熱線導入 AI 效益與評估",
        "description": "深入剖析台北市 1999 市民熱線導入語音辨識、意圖分類與 AI 客服之效益研究，以及研考會話務管理組在第一線的實務考量與限制。",
        "tags": ["1999市民熱線", "研考會", "AI語音客服", "智慧派工", "情緒辨識", "效益評估"],
        "documentsCount": 5,
        "sampleQuestions": [
            "台北市 1999 導入 AI 的效益評估研究主要結論與建議是什麼？",
            "研考會話務管理組蔡組長在訪談中提到哪些導入 AI 的實務挑戰與局限？",
            "1999 熱線導入 AI 技術後，話務人員的角色發生了什麼轉變？"
        ],
        "keyCruxes": [
            {
                "title": "AI 效益 vs. 真人情感撫慰的不可替代性",
                "description": "AI 能夠快速處理重複性市政查詢與派工，但市民撥打 1999 常伴隨焦慮、不滿等情緒，AI 無法完全取代具備同理心之真人話務員。",
                "proPoints": [
                    "針對路燈不亮、垃圾清運等標準化題型，AI 可 24 小時自動派工分流，顯著降低話務負載",
                    "語音轉文字 (STT) 能大幅縮短話務人員記錄與打字時間，提升每通通話處理效率",
                    "大數據與意圖分析有助於市府提前預警熱點民怨問題"
                ],
                "conPoints": [
                    "民眾在緊急或情緒激動時，聽到機器人語音容易引發更大反彈與抱怨",
                    "複雜陳情案牽涉多個局處權責，現階段 AI 語意理解難以精準判斷跨局處歸屬",
                    "部分長者或特定口音市民在語音辨識系統上面臨使用門檻"
                ]
            },
            {
                "title": "市政動態知識庫的維護成本與正確性責任",
                "description": "市政法規與各局處業務隨時變更，AI 訓練與知識庫維護若不及時，恐導致回答錯誤引發民怨爭議。",
                "proPoints": [
                    "透過統一的知識管理系統 (KMS) 結構化市政問答，促使各局處定期審查業務常見問題",
                    "導入 RAG 檢索增強生成架構，回答時強制附帶法規來源出處，提高可信度"
                ],
                "conPoints": [
                    "各局處常未能即時同步最新法令或施工公告，導致 AI 回應產生幻覺或落後資訊",
                    "若 AI 誤導民眾權益（如補助申請資格），行政責任與民怨承擔機制仍不明確"
                ]
            }
        ]
    },
    {
        "id": "taipei-genai-guidelines",
        "category": "政策指引與治理規範",
        "title": "臺北市政府使用人工智慧作業指引與生成式 AI 規範",
        "description": "分析台北市政府頒布之 AI 作業指引，涵蓋資安防護、民眾個人資料保護、智慧財產權歸屬以及公務人員使用生成式 AI 之倫理與法律責任界線。",
        "tags": ["AI作業指引", "生成式AI", "資安防護", "個資隱私", "行政責任", "公文輔助"],
        "documentsCount": 4,
        "sampleQuestions": [
            "《臺北市政府使用人工智慧作業指引》對於公務員使用生成式 AI 有哪些核心規範與禁令？",
            "在公文撰寫與民眾陳情回覆中，指引如何規範人工審核 (Human-in-the-loop) 責任？",
            "市府如何防範公務機密與民眾個資因使用外部 AI 雲端模型而外洩？"
        ],
        "keyCruxes": [
            {
                "title": "機密資安防護 vs. 公務行政效率提升",
                "description": "嚴格禁止公務機密與未公開資料上傳公開雲端 AI，與公務員渴望利用先進 LLM 提升文書與分析效率之間的拉鋸。",
                "proPoints": [
                    "嚴格規範可防止重大市政機密、人事資料或市民敏感個資流出",
                    "建立地端/私有雲或政府專用通道模型，在確保資安前提下提供安全推論環境"
                ],
                "conPoints": [
                    "過於嚴格的禁令可能導致公務人員轉入「影子 AI」(Shadow AI) 私下使用個人帳號",
                    "地端部署成本高昂且模型更新速度往往落後公開商業頂尖模型"
                ]
            },
            {
                "title": "AI 輔助 vs. 公務員最終法律與行政責任",
                "description": "明確界定 AI 僅能作為「輔助工具」，所有對外正式公文、陳情答覆或行政處分均必須經由公務員實質審查並自行負責。",
                "proPoints": [
                    "堅守「人機協同 (Human-in-the-loop)」原則，避免演算法黑箱與行政卸責",
                    "維護行政處分之合法性與公信力"
                ],
                "conPoints": [
                    "公務員若過度信任 AI 輸出而未仔細覆核，可能衍生行政瑕疵甚至國賠爭議",
                    "需要持續對公務員進行 AI 素養與 Prompt 查核訓練"
                ]
            }
        ]
    },
    {
        "id": "taipei-bureau-interviews",
        "category": "局處實務與首長訪談",
        "title": "局處 AI 實務推動與首長訪談洞察",
        "description": "彙整資訊局局長、人事處、觀傳局、都更處、自來水事業處等局處首長與主管之一線訪談，剖析跨局處推動 AI 的痛點與轉型歷程。",
        "tags": ["資訊局", "人事處", "觀傳局", "首長訪談", "組織文化", "AI素養培訓"],
        "documentsCount": 10,
        "sampleQuestions": [
            "資訊局長在訪談中針對市府推動 AI 治理與基礎設施有何策略規劃？",
            "人事處在推廣公務人員 AI 賦能與教育訓練上遇到了哪些挑戰與規劃？",
            "觀傳局在實際應用 AI 於智慧旅遊與行銷時有哪些實務考量與經驗？"
        ],
        "keyCruxes": [
            {
                "title": "資訊局統一集中納管 vs. 各業務局處自主採購開發",
                "description": "市府整體 AI 基礎設施、算力與共通 API 是否應由資訊局統一統籌，還是允許各局處依特定業務自行招標建置。",
                "proPoints": [
                    "統一平台可避免重複投資、確保資安標準一致，並發揮市府資料整合綜效",
                    "有利於建立跨局處通用之 RAG 知識庫與共享基礎模型"
                ],
                "conPoints": [
                    "資訊局人力與專案排程有限，可能無法即時滿足各局處高度特化的業務時效需求",
                    "業務局處最懂自身痛點，自主採購更能快速對接業界專屬解決方案"
                ]
            },
            {
                "title": "公務體系內部文化與 AI 素養跨越",
                "description": "公務員對新科技的抗拒、對出錯懲處的恐懼，以及人事處推動 AI 研習的普及度成效。",
                "proPoints": [
                    "人事處推動系統化培訓與案例競賽，逐步消除同仁對 AI 取代人力的焦慮",
                    "透過標準作業 SOP 降低公務員使用 AI 的心理負擔"
                ],
                "conPoints": [
                    "部分資深同仁數位落差明顯，學習曲線較長",
                    "缺乏明確的激勵機制促使基層公務員主動投入流程創新"
                ]
            }
        ]
    },
    {
        "id": "taipei-tpmo-smartcity",
        "category": "概念驗證與公私協力",
        "title": "TPMO 台北智慧城市專案辦公室與概念驗證 (PoC)",
        "description": "探討台北智慧城市專案辦公室 (TPMO) 採行之「1+7 智慧領域」架構、民間提案 PoC 試辦機制以及國際智慧城市評比經驗。",
        "tags": ["TPMO", "智慧城市", "PoC試辦", "公私協力", "創新實驗場域", "國際評比"],
        "documentsCount": 3,
        "sampleQuestions": [
            "TPMO 在台北智慧城市推動架構中扮演什麼角色？其 1+7 領域機制如何運作？",
            "民間企業如何透過 TPMO 機制參與台北市的智慧城市與 AI 概念驗證 (PoC)？",
            "台北市在國際智慧城市評比中的優勢與持續改進方向為何？"
        ],
        "keyCruxes": [
            {
                "title": "PoC 創新概念驗證到常態公務採購的銜接斷層 (Valley of Death)",
                "description": "民間透過 TPMO 成功驗證的創新 AI 專案，在轉化為各局處正式預算招標時面臨採購法與預算編列門檻。",
                "proPoints": [
                    "由政府提供實體場域供民間零成本快速試錯，激發產業創新動能",
                    "讓市府先驗證效益再決定是否大規模推廣，降低採購風險"
                ],
                "conPoints": [
                    "受限於政府採購法規，提案廠商完成 PoC 後仍須參與公開競標，無法直接獲取合約",
                    "各局處若無後續長期維運預算支持，容易使優秀試辦方案淪為一次性展演"
                ]
            }
        ]
    }
]

@router.get("/topics")
async def api_get_topics():
    """獲取台北市 AI 治理焦點專題、核心爭點與建議提問"""
    return GOVERNANCE_TOPICS

@router.post("/chat/stream")
async def api_chat_stream(request: ChatStreamRequest):
    """執行即時 SSE 串流問答與文獻出處引用"""
    try:
        return StreamingResponse(
            stream_city_governance_rag_vertex(
                query=request.query,
                city_filter=request.city,
                language_filter=request.language
            ),
            media_type="text/event-stream"
        )
    except Exception as e:
        logger.error(f"Chat stream error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "City AI Governance Vertex AI Search & MCP Hub"}

