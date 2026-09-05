import json
import logging
from typing import Any, List, Optional
from mcp.server.fastmcp import FastMCP
from app.pipelines.vertex_search import search_vertex_data_store, query_city_governance_rag_vertex
from app.pipelines.cleaner import clean_and_annotate_document, preview_chunks

logger = logging.getLogger(__name__)

# Initialize FastMCP Server backed by Vertex AI Search
mcp = FastMCP("City-AI-Governance-Vertex-MCP", dependencies=["google-cloud-discoveryengine", "google-generativeai"])

@mcp.tool()
def search_city_ai_governance_knowledge(
    query: str,
    city: Optional[str] = None,
    language: Optional[str] = None,
    top_k: int = 5
) -> str:
    """
    搜尋全球城市 AI 治理 Vertex AI 知識庫中的政策法規、白皮書與標竿案例。
    
    :param query: 檢索關鍵字或語意查詢句 (例如: '公務機關使用生成式AI之指引', '演算法透明度法規比較')
    :param city: 指定過濾的城市名稱 (例如: '台北', '倫敦', '紐約', '新加坡', '東京')
    :param language: 指定語言代碼 (例如: 'zh', 'en', 'ja')
    :param top_k: 回傳最相關的片段數量 (預設 5)
    """
    try:
        filter_parts = []
        if city:
            filter_parts.append(f'city = ANY("{city}")')
        if language:
            filter_parts.append(f'language = ANY("{language}")')
        filter_expr = " AND ".join(filter_parts) if filter_parts else None

        results = search_vertex_data_store(
            query=query,
            page_size=top_k,
            filter_expr=filter_expr
        )
        return json.dumps(results, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"MCP search error: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)

@mcp.tool()
def ask_city_ai_governance_rag(
    question: str,
    city: Optional[str] = None,
    language: Optional[str] = None
) -> str:
    """
    向全球城市 AI 治理 RAG 系統提問，獲取由 Google Vertex AI Search & Gemini Grounding 支援的政策比較與深度分析（附帶精確引文來源）。
    
    :param question: 研究或諮詢問題 (例如: '比較新加坡與紐約在公共安全 AI 應用的監管機制差異')
    :param city: 限定特定城市 (若為全球比較則留空)
    :param language: 限定語言代碼
    """
    try:
        res = query_city_governance_rag_vertex(
            query=question,
            city_filter=city,
            language_filter=language
        )
        return res["answer"]
    except Exception as e:
        logger.error(f"MCP ask error: {e}")
        return f"Vertex AI RAG 查詢發生錯誤: {str(e)}"

@mcp.tool()
def ai_clean_and_annotate_governance_doc(
    raw_text: str,
    filename: Optional[str] = None
) -> str:
    """
    透過 AI 協助研究員預清理政策文件、去除雜訊，並自動萃取城市 AI 治理專業 Metadata（城市、領域、類型、摘要與標籤）。
    
    :param raw_text: 原始文件文字
    :param filename: 檔案名稱
    """
    try:
        res = clean_and_annotate_document(raw_text=raw_text, filename=filename)
        return json.dumps(res.model_dump(), ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"MCP clean error: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)

@mcp.tool()
def inspect_document_chunks(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 80
) -> str:
    """
    預覽文件切片 (Chunking) 的切分狀況、長度與 Token 估算，用於確認切片邊界合理性。
    
    :param text: 欲切片之本文內容
    :param chunk_size: 每個切片字元長度 (預設 500)
    :param chunk_overlap: 重疊字元數 (預設 80)
    """
    try:
        previews = preview_chunks(text, {}, chunk_size, chunk_overlap)
        return json.dumps([p.model_dump() for p in previews], ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"MCP chunk preview error: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
