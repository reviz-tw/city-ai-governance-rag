from typing import Annotated, Literal
from pydantic import BaseModel, Field, field_validator, model_validator
from app.services.languages import normalize_language

class ArtifactRequest(BaseModel):
    kind: Literal['chart', 'pdf', 'pptx', 'translation']
    scope: Literal['answer', 'conversation', 'passage', 'document']
    message_ids: list[str] = Field(default_factory=list, max_length=12)
    source_ids: list[str] = Field(min_length=1, max_length=12)
    source_passages: dict[str, Annotated[list[str], Field(min_length=1, max_length=50)]] = Field(default_factory=dict, max_length=12)
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

SlideLayout = Literal['briefing', 'comparison', 'process', 'evidence', 'chart']

class SlidePoint(BaseModel):
    label: str = Field(min_length=1, max_length=70)
    detail: str = Field(min_length=1, max_length=220)

class Slide(BaseModel):
    layout: SlideLayout
    title: str = Field(min_length=1, max_length=110)
    takeaway: str = Field(min_length=1, max_length=180)
    reasoning: Literal['evidence', 'inference', 'recommendation'] = 'evidence'
    points: list[SlidePoint] = Field(default_factory=list, max_length=5,
        description='REQUIRED for briefing (2–4 points), process (2–5 steps) and evidence (1–2 explanations). Empty for comparison and chart. Each point must have a label AND a substantive detail.')
    columns: list[str] = Field(default_factory=list, max_length=3, description='Comparison requires 2–3 column headings. Otherwise empty.')
    rows: list[list[str]] = Field(default_factory=list, max_length=4, description='Comparison requires 2–4 rows, each matching the column count. Otherwise empty.')
    quote: str = Field('', max_length=320, description='REQUIRED and nonempty for evidence layout: a verbatim quotation in the original source language. Otherwise empty.')
    chart: ChartSpec | None = None
    citations: list[CitationRef] = Field(min_length=1, max_length=6)
    notes: str = Field(min_length=1, max_length=1800, description='Presenter explanation; preserve qualifications and distinguish proposals from source facts.')

    @model_validator(mode='after')
    def layout_content(self):
        if self.layout in {'briefing', 'process'}:
            if not 2 <= len(self.points) <= (5 if self.layout == 'process' else 4):
                raise ValueError('Briefing needs 2–4 points; process needs 2–5 steps')
        elif self.layout == 'comparison':
            if not 2 <= len(self.columns) <= 3 or not 2 <= len(self.rows) <= 4:
                raise ValueError('Comparison needs 2–3 columns and 2–4 rows')
            if any(len(row) != len(self.columns) for row in self.rows):
                raise ValueError('Every comparison row must match the column count')
            if any(not cell.strip() or len(cell) > 160 for row in [self.columns, *self.rows] for cell in row):
                raise ValueError('Comparison cells must be nonempty and concise')
        elif self.layout == 'evidence':
            if not self.quote.strip() or not 1 <= len(self.points) <= 2:
                raise ValueError(f'Evidence layout requires nonempty quote and 1–2 points with label/detail; got quote={bool(self.quote.strip())}, points={len(self.points)}')
        elif self.layout == 'chart':
            if not self.chart or self.chart.type != 'bar' or not 2 <= len(self.chart.points) <= 6:
                raise ValueError('Slide charts need 2–6 comparable, sourced numeric points')
        if self.layout not in {'briefing','process','evidence'} and self.points:
            raise ValueError('This layout cannot display points')
        if self.layout != 'comparison' and (self.columns or self.rows):
            raise ValueError('Only comparison slides display table data')
        if self.layout != 'evidence' and self.quote:
            raise ValueError('Only evidence slides display a quotation')
        if self.layout != 'chart' and self.chart:
            raise ValueError('Only chart slides display chart data')
        return self

class SlideOutline(BaseModel):
    title: str = Field(max_length=110)
    purpose: str = Field(max_length=240)
    layout: SlideLayout
    citations: list[CitationRef] = Field(min_length=1, max_length=6)

class DeckOutline(BaseModel):
    audience_goal: str = Field(min_length=1, max_length=300)
    slides: list[SlideOutline] = Field(min_length=1, max_length=12)
    coverage_note: str = Field('', max_length=500)

class SlideDeckDraft(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    summary: str = Field(min_length=1, max_length=600)
    audience_goal: str = Field(min_length=1, max_length=300)
    slides: list[Slide] = Field(min_length=1, max_length=12)
    limitations: str = Field(min_length=1, max_length=600)
    coverage_note: str = Field('', max_length=500)

class SlideAssessment(BaseModel):
    slide_number: int = Field(ge=1, le=12)
    supported: bool
    assessment: str = Field(min_length=1, max_length=350, description='Brief evidence-based verdict. Check exact obligations, conditions and factual details against the cited blocks, including presenter notes. If unsupported, explain the correction.')

class SlideReview(BaseModel):
    slides: list[SlideAssessment] = Field(min_length=1, max_length=12)
    issues: list[str] = Field(default_factory=list, max_length=8,
        description='Actionable defects with slide numbers: unsupported facts, missing material, repetition, weak explanations or unsuitable layouts. Empty only if suitable to present.')

class ArtifactDraft(ReportDraft):
    # Existing report/legacy-slide drafts still use sections. New decks use slides exclusively.
    sections: list[Section] = Field(default_factory=list, max_length=14)
    chart: ChartSpec | None = None
    slides: list[Slide] = Field(default_factory=list, max_length=12)
    audience_goal: str = Field('', max_length=300)
    coverage_note: str = Field('', max_length=500)

class TranslatedBlock(BaseModel):
    id: str
    text: str = Field(max_length=12000)
    cells: list[list[str]] | None = None
    ambiguity: str = Field('', max_length=500)

class TranslationBatch(BaseModel):
    blocks: list[TranslatedBlock]
    glossary: dict[str, str] = Field(default_factory=dict)
