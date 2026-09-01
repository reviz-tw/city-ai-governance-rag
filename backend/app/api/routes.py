import io
import logging
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pypdf import PdfReader
import docx

from app.models.schema import (
    GovernanceMetadata,
    DocumentCleanAndTagRequest,
    DocumentCleanAndTagResponse,
    IndexDocumentRequest,
    IndexDocumentResponse,
    RAGQueryRequest,
    RAGQueryResponse,
    ChunkPreview
)
from app.pipelines.cleaner import clean_and_annotate_document, preview_chunks
from app.pipelines.indexing import index_document_content
from app.pipelines.rag import query_rag

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
        # Plain text / Markdown
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
    """上傳文件、自動 AI 清理標註並寫入 Pgvector 向量庫"""
    try:
        content_bytes = await file.read()
        extracted_text = extract_text_from_file(content_bytes, file.filename)
        
        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="未能從檔案中讀取有效文字。")
            
        final_text = extracted_text
        if auto_ai_tag:
            ai_res = clean_and_annotate_document(extracted_text, file.filename)
            meta = ai_res.suggested_metadata
            final_text = ai_res.cleaned_text
            
            # 若使用者有明確手動覆蓋欄位則採用手動設定
            if city: meta.city = city
            if country: meta.country = country
            if policy_domain: meta.policy_domain = policy_domain
            if document_type: meta.document_type = document_type
            if language: meta.language = language
            if publication_year: meta.publication_year = publication_year
        else:
            meta = GovernanceMetadata(
                title=file.filename,
                city=city or "未知城市",
                country=country or "未知國家",
                policy_domain=policy_domain or "公共治理與智慧城市",
                document_type=document_type or "政策白皮書",
                language=language or "zh-TW",
                publication_year=publication_year or 2025
            )
            
        res = index_document_content(final_text, meta)
        return IndexDocumentResponse(
            success=True,
            document_id=res["document_id"],
            total_chunks=res["total_chunks"],
            message=f"文件《{meta.title}》已成功切分為 {res['total_chunks']} 個切片並寫入 Pgvector 知識庫！"
        )
    except Exception as e:
        logger.error(f"檔案上傳與索引失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rag/query", response_model=RAGQueryResponse)
async def api_query_rag(request: RAGQueryRequest):
    """執行多語治理 RAG 檢索與問答"""
    try:
        return query_rag(
            query=request.query,
            cities=request.cities,
            policy_domains=request.policy_domains,
            languages=request.languages,
            top_k=request.top_k,
            response_language=request.response_language or "zh-TW"
        )
    except Exception as e:
        logger.error(f"RAG 查詢失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "City AI Governance RAG & MCP Hub"}
