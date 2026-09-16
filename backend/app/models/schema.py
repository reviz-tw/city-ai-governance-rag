from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, AliasChoices, field_validator
from app.services.languages import normalize_language, source_languages as normalize_sources
from app.services.context import ResearchContext

class GovernanceMetadata(BaseModel):
    title: str = Field(..., description="文件標題")
    city: str = Field(..., description="城市名稱 (如: 台北, 倫敦, 紐約, 新加坡, 東京, 首爾, 巴塞隆納)")
    country: str = Field(..., description="國家名稱")
    region: Optional[str] = Field("全球", description="地區/洲別 (如: 亞太, 歐洲, 北美)")
    policy_domain: str = Field(
        ..., 
        description="政策領域 (如: 演算法透明度, 資料隱私與安全, 公共治理與智慧城市, 倫理審查與風險分級, 生成式AI規範, 採購指引)"
    )
    document_type: str = Field(
        "政策白皮書", 
        description="文件類型 (如: 市政府自治法規, 政策白皮書, 框架指引, 顧問評估報告, 標竿案例)"
    )
    language: str = Field("zh-TW", description="原文語言代碼 (如: zh-TW, en, ja, ko, es)")
    publication_year: Optional[int] = Field(None, description="發布年份；未記載則為 null")
    source_url: Optional[str] = Field(None, description="原始來源或發布機關網址")
    tags: List[str] = Field(default_factory=list, description="標籤關鍵字")

class ChunkPreview(BaseModel):
    chunk_index: int
    content: str
    token_count: int
    char_count: int
    metadata: Dict[str, Any]

class DocumentCleanAndTagRequest(BaseModel):
    raw_text: str = Field(..., max_length=15000, description="原始文字內容；超過上限請分批清理")
    filename: Optional[str] = Field(None, description="檔案名稱")

class DocumentCleanAndTagResponse(BaseModel):
    cleaned_text: str
    suggested_metadata: GovernanceMetadata
    summary: str
    key_takeaways: List[str]

class IndexDocumentRequest(BaseModel):
    content: str
    metadata: GovernanceMetadata
    chunk_size: Optional[int] = 500
    chunk_overlap: Optional[int] = 80

class IndexDocumentResponse(BaseModel):
    success: bool
    document_id: str
    total_chunks: int
    message: str

class LanguageRequest(BaseModel):
    response_language: str = Field("auto", validation_alias=AliasChoices("response_language", "language"))
    interface_language: str | None = None
    source_languages: List[str] = Field(default_factory=list, max_length=10)
    research_context: ResearchContext | None = None

    @field_validator("response_language", mode="before")
    @classmethod
    def validate_response(cls, value):
        return normalize_language(value, auto=True)

    @field_validator("interface_language")
    @classmethod
    def validate_interface(cls, value):
        return normalize_language(value) if value else None

    @field_validator("source_languages")
    @classmethod
    def validate_sources(cls, value):
        return normalize_sources(value)

class RAGQueryRequest(LanguageRequest):
    query: str = Field(min_length=1, max_length=8000)
    city: str | None = Field(None, max_length=100)

class RetrievedSource(BaseModel):
    content: str
    score: float
    metadata: Dict[str, Any]

class RAGQueryResponse(BaseModel):
    answer: str
    query: str
    sources: List[RetrievedSource]
    model_used: str

class ChatStreamRequest(RAGQueryRequest):
    topic_id: Optional[str] = Field(None, description="Deprecated; no implicit research scope")
