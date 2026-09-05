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
    IndexDocumentResponse,
    ChunkPreview
)
from app.pipelines.cleaner import clean_and_annotate_document, preview_chunks
from app.pipelines.vertex_search import (
    upload_document_to_gcs,
    search_vertex_data_store,
    query_city_governance_rag_vertex
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

@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "City AI Governance Vertex AI Search & MCP Hub"}
