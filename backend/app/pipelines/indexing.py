import logging
import uuid
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from haystack.dataclasses import Document
from haystack_integrations.document_stores.pgvector import PgvectorDocumentStore

from app.core.config import settings
from app.models.schema import GovernanceMetadata
from app.pipelines.cleaner import preview_chunks

logger = logging.getLogger(__name__)

if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)

def get_document_store() -> PgvectorDocumentStore:
    """初始化並取得 Haystack PgvectorDocumentStore 實例"""
    return PgvectorDocumentStore(
        connection_string=settings.database_url,
        table_name="haystack_city_governance_docs",
        embedding_dimension=settings.EMBEDDING_DIMENSION,
        vector_function="cosine",
        recreate_table=False,
        search_strategy="hnsw"
    )

def generate_embeddings(texts: List[str], task_type: str = "retrieval_document") -> List[List[float]]:
    """使用 Google text-embedding-004 生成多語向量"""
    embeddings = []
    # 批次計算 Embeddings
    batch_size = 20
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        result = genai.embed_content(
            model=f"models/{settings.EMBEDDING_MODEL}",
            content=batch,
            task_type=task_type
        )
        if "embedding" in result:
            embeddings.extend(result["embedding"])
    return embeddings

def index_document_content(
    content: str, 
    metadata: GovernanceMetadata,
    chunk_size: int = 500,
    chunk_overlap: int = 80
) -> Dict[str, Any]:
    """將文件進行多語切片、向量計算並寫入 Pgvector"""
    doc_id = str(uuid.uuid4())
    meta_dict = metadata.model_dump()
    meta_dict["document_id"] = doc_id
    
    # 1. 產生 Chunks
    chunk_previews = preview_chunks(content, meta_dict, chunk_size, chunk_overlap)
    if not chunk_previews:
        raise ValueError("無法從提供之文字內容產出切片。")
        
    chunk_texts = [c.content for c in chunk_previews]
    
    # 2. 計算多語對齊向量 Embeddings (text-embedding-004)
    embeddings = generate_embeddings(chunk_texts, task_type="retrieval_document")
    
    # 3. 建立 Haystack Documents
    haystack_docs: List[Document] = []
    for idx, chunk in enumerate(chunk_previews):
        chunk_meta = dict(meta_dict)
        chunk_meta["chunk_index"] = idx + 1
        chunk_meta["total_chunks"] = len(chunk_previews)
        chunk_meta["char_count"] = chunk.char_count
        chunk_meta["token_count"] = chunk.token_count
        
        doc = Document(
            id=f"{doc_id}_{idx+1}",
            content=chunk.content,
            meta=chunk_meta,
            embedding=embeddings[idx] if idx < len(embeddings) else None
        )
        haystack_docs.append(doc)
        
    # 4. 存入 Pgvector Document Store
    doc_store = get_document_store()
    doc_store.write_documents(haystack_docs)
    
    logger.info(f"文件 {metadata.title} (ID: {doc_id}) 已成功索引 {len(haystack_docs)} 個切片至 Pgvector。")
    
    return {
        "document_id": doc_id,
        "total_chunks": len(haystack_docs),
        "title": metadata.title,
        "city": metadata.city
    }
