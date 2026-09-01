import logging
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from haystack_integrations.document_stores.pgvector import PgvectorDocumentStore

from app.core.config import settings
from app.models.schema import RAGQueryResponse, RetrievedSource
from app.pipelines.indexing import get_document_store, generate_embeddings

logger = logging.getLogger(__name__)

if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)

RAG_PROMPT_TEMPLATE = """你是一位專精於「全球城市 AI 治理研究」的國際政策顧問與資深分析師。
請根據以下檢索自全球各城市（如台北、倫敦、紐約、新加坡、首爾、東京、阿姆斯特丹、巴塞隆納等）的官方政策法規與評估報告，回答使用者的提問。

【檢索來源文件片段 (Context)】:
{context}

【分析指引】:
1. 回答需具備國際比較視野（例如比較不同城市的政策工具、治理策略或倫理法規）。
2. 明確指出資訊來源（標註城市名稱、政策名稱與發布年份）。
3. 若檢索資料中有跨語言內容（如英文/日文政策），請翻譯並以指定目標語言 ({response_language}) 清晰呈現。
4. 若檢索片段不足以回答問題，請誠實說明「目前知識庫尚無該城市或領域之確切規範」，切勿憑空捏造。

【使用者問題】:
{query}

【回答 ({response_language})】:
"""

def query_rag(
    query: str,
    cities: Optional[List[str]] = None,
    policy_domains: Optional[List[str]] = None,
    languages: Optional[List[str]] = None,
    top_k: int = 5,
    response_language: str = "zh-TW"
) -> RAGQueryResponse:
    """執行多語向量檢索與 Gemini 治理問答生成"""
    # 1. 生成 Query 的向量 (task_type="retrieval_query")
    query_embedding = generate_embeddings([query], task_type="retrieval_query")[0]
    
    # 2. 構建 Metadata Filters
    filters: Dict[str, Any] = {}
    conditions = []
    if cities:
        conditions.append({"field": "meta.city", "operator": "in", "value": cities})
    if policy_domains:
        conditions.append({"field": "meta.policy_domain", "operator": "in", "value": policy_domains})
    if languages:
        conditions.append({"field": "meta.language", "operator": "in", "value": languages})
        
    if len(conditions) == 1:
        filters = conditions[0]
    elif len(conditions) > 1:
        filters = {"operator": "AND", "conditions": conditions}
        
    # 3. 透過 Pgvector 進行向量檢索
    doc_store = get_document_store()
    retrieved_docs = doc_store._embedding_retrieval(
        query_embedding=query_embedding,
        top_k=top_k,
        filters=filters if filters else None
    )
    
    # 4. 組織 Context 片段
    sources: List[RetrievedSource] = []
    context_chunks = []
    for idx, doc in enumerate(retrieved_docs):
        meta = doc.meta or {}
        score = getattr(doc, "score", 0.0) or 0.0
        sources.append(RetrievedSource(
            content=doc.content or "",
            score=round(score, 4),
            metadata=meta
        ))
        
        city = meta.get("city", "全球")
        title = meta.get("title", "未命名文件")
        domain = meta.get("policy_domain", "AI治理")
        year = meta.get("publication_year", "")
        
        context_chunks.append(
            f"[來源 {idx+1}] 【城市: {city} | 政策: {title} ({year}) | 領域: {domain}】\n{doc.content}"
        )
        
    context_str = "\n\n".join(context_chunks) if context_chunks else "（未檢索到相關知識庫文件）"
    
    # 5. Gemini 生成回答
    prompt = RAG_PROMPT_TEMPLATE.format(
        context=context_str,
        query=query,
        response_language=response_language
    )
    
    model = genai.GenerativeModel(model_name=settings.GEMINI_MODEL)
    response = model.generate_content(prompt)
    answer_text = response.text if response else "無法生成回答。"
    
    return RAGQueryResponse(
        answer=answer_text,
        query=query,
        sources=sources,
        model_used=settings.GEMINI_MODEL
    )
