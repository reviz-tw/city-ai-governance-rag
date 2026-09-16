from typing import Literal
from pydantic import BaseModel, Field, field_validator
from app.services.languages import normalize_language

class ArtifactRequest(BaseModel):
    kind: Literal['chart', 'pdf', 'pptx', 'translation']
    scope: Literal['answer', 'conversation', 'passage', 'document']
    message_ids: list[str] = Field(default_factory=list, max_length=12)
    source_ids: list[str] = Field(min_length=1, max_length=12)
    context: str = Field('', max_length=6000)
    language: str = 'zh-TW'
    template: Literal['research-v1'] = 'research-v1'
    audience: str = Field('研究與政策工作者', max_length=200)
    pages: int = Field(6, ge=3, le=12)
    block_ids: list[str] = Field(default_factory=list, max_length=50)
    acknowledge_extraction_limits: bool = False

    @field_validator('language')
    @classmethod
    def valid_language(cls, value):
        return normalize_language(value)

class CitationRef(BaseModel):
    document_id: str
    block_id: str

class Section(BaseModel):
    heading: str = Field(max_length=120)
    body: str = Field(max_length=2500)
    citations: list[CitationRef] = Field(default_factory=list, max_length=12)

class SeriesPoint(BaseModel):
    label: str = Field(max_length=100)
    value: float
    unit: str = Field(max_length=50, description='Exact unit substring from quote, in the ORIGINAL source language; never translate this field.')
    period: str = Field(max_length=100, description='Exact time period substring from quote, e.g. 2026; do not add translated suffixes.')
    source: CitationRef
    quote: str = Field(max_length=500)

class ChartSpec(BaseModel):
    type: Literal['bar', 'comparison', 'flow', 'architecture']
    title: str = Field(max_length=120)
    points: list[SeriesPoint] = Field(default_factory=list, max_length=12)
    labels: list[str] = Field(default_factory=list, max_length=12)
    rows: list[list[str]] = Field(default_factory=list, max_length=15)
    edges: list[list[int]] = Field(default_factory=list, max_length=24)
    citations: list[CitationRef] = Field(default_factory=list, max_length=20)

class ReportDraft(BaseModel):
    title: str = Field(max_length=160)
    summary: str = Field(max_length=1500)
    sections: list[Section] = Field(min_length=1, max_length=14)
    limitations: str = Field(max_length=1500)

class ArtifactDraft(ReportDraft):
    chart: ChartSpec | None = None

class TranslatedBlock(BaseModel):
    id: str
    text: str = Field(max_length=12000)
    cells: list[list[str]] | None = None
    ambiguity: str = Field('', max_length=500)

class TranslationBatch(BaseModel):
    blocks: list[TranslatedBlock]
    glossary: dict[str, str] = Field(default_factory=dict)
