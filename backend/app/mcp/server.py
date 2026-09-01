import json
import logging
from typing import Any, List, Optional
from mcp.server.fastmcp import FastMCP
from app.pipelines.rag import query_rag
from app.pipelines.cleaner import clean_and_annotate_document, preview_chunks
from app.pipelines.indexing import index_document_content
from app.models.schema import GovernanceMetadata

logger = logging.getLogger(__name__)

# Initialize FastMCP Server
mcp = FastMCP("City-AI-Governance-RAG-MCP", dependencies=["haystack-ai", "pgvector-haystack"])

@mcp.tool()
def search_city_ai_governance_knowledge(
    query: str,
    cities: Optional[List[str]] = None,
    policy_domains: Optional[List[str]] = None,
    top_k: int = 5
) -> str:
    """
    搜尋全球城市 AI 治理知識庫中的政策法規、白皮書與標竿案例片段。
    
    :param query: 檢索關鍵字或語意查詢句 (例如: '公務機關使用生成式AI之指引', '演算法透明度法規比較')
    :param cities: 指定過濾的城市列表 (例如: ['台北', '倫敦', '紐約', '新加坡', '東京'])
    :param policy_domains: 指定政策領域 (例如: ['演算法透明度', '資料隱私', '公共治理', '採購指引'])
    :param top_k: 回傳最相關的片段數量 (預設 5)
    """
    try:
        rag_res = query_rag(
            query=query,
            cities=cities,
            policy_domains=policy_domains,
            top_k=top_k
        )
        
        results = []
        for idx, src in enumerate(rag_res.sources):
            meta = src.metadata
            results.append({
                "index": idx + 1,
                "city": meta.get("city"),
                "country": meta.get("country"),
                "policy_title": meta.get("title"),
                "year": meta.get("publication_year"),
                "domain": meta.get("policy_domain"),
                "similarity_score": src.score,
                "content": src.content
            })
        return json.dumps(results, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"MCP search error: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)

@mcp.tool()
def ask_city_ai_governance_rag(
    question: str,
    cities: Optional[List[str]] = None,
    policy_domains: Optional[List[str]] = None,
    response_language: str = "zh-TW"
) -> str:
    """
    向全球城市 AI 治理 RAG 系統提問，獲取基於各國城市真實政策文件的國際比較與深入分析。
    
    :param question: 研究或諮詢問題 (例如: '比較新加坡與紐約在公共安全 AI 應用的監管機制差異')
    :param cities: 限定特定城市 (若為全球比較則留空)
    :param policy_domains: 限定特定政策領域
    :param response_language: 回答目標語言 (預設 'zh-TW', 支援 'en', 'ja' 等)
    """
    try:
        rag_res = query_rag(
            query=question,
            cities=cities,
            policy_domains=policy_domains,
            response_language=response_language
        )
        return rag_res.answer
    except Exception as e:
        logger.error(f"MCP ask error: {e}")
        return f"RAG 查詢發生錯誤: {str(e)}"

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
