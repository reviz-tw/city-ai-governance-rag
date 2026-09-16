import json
from urllib.parse import urlsplit
from typing import Optional
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from app.core.config import settings
from app.pipelines.vertex_search import retrieve, query_city_governance_rag_vertex
from app.pipelines.cleaner import clean_and_annotate_document, preview_chunks
from app.services.auth import require_user, require_editor
from app.services.context import ResearchContext
from app.services import jobs, documents
from app.models.artifacts import ArtifactRequest

def transport_security(origins):
    return TransportSecuritySettings(enable_dns_rebinding_protection=True,
                 allowed_hosts=list(dict.fromkeys(['localhost','127.0.0.1','localhost:*','127.0.0.1:*'] +
                     [urlsplit(origin).netloc for origin in origins])), allowed_origins=origins)

mcp = FastMCP('City-AI-Governance-MCP', stateless_http=True, dependencies=['google-cloud-discoveryengine','google-genai'],
             transport_security=transport_security(settings.ALLOWED_ORIGINS))


def output(value):
    return json.dumps(value, ensure_ascii=False, default=str)

@mcp.tool()
def search_city_ai_governance_knowledge(query: str, city: Optional[str] = None,
                                        source_languages: Optional[list[str]] = None, top_k: int = 5) -> str:
    """Search original evidence. source_languages ONLY filters document language; omitted means all languages."""
    require_user()
    if not 1 <= top_k <= 20:
        raise ValueError('top_k must be between 1 and 20')
    return output(retrieve(query, city, source_languages)[:top_k])

@mcp.tool()
def ask_city_ai_governance_rag(question: str, city: Optional[str] = None,
                               response_language: str = 'auto', interface_language: Optional[str] = None,
                               source_languages: Optional[list[str]] = None,
                               research_context: Optional[ResearchContext] = None) -> str:
    """Answer using original evidence and return citations with document IDs and languages.

    response_language controls the answer; auto detects the question language.
    interface_language is only a fallback. source_languages independently filters sources.
    research_context contains only explicitly supplied bounded history; host conversations are never read.
    """
    require_user()
    return output(query_city_governance_rag_vertex(question, city, response_language, interface_language,
                                                    source_languages, research_context))

@mcp.tool()
def ai_clean_and_annotate_governance_doc(raw_text: str, filename: Optional[str] = None) -> str:
    """Editor-only document cleanup; this does not upload or publish any document."""
    require_editor()
    return output(clean_and_annotate_document(raw_text, filename).model_dump())

@mcp.tool()
def inspect_document_chunks(text: str, chunk_size: int = 500, chunk_overlap: int = 80) -> str:
    """Temporary automatic chunk preview, not the published search index."""
    require_user()
    if not 100 <= chunk_size <= 5000 or not 0 <= chunk_overlap < chunk_size or len(text) > 100000:
        raise ValueError('Invalid chunk preview size')
    return output([p.model_dump() for p in preview_chunks(text, {}, chunk_size, chunk_overlap)])


def artifact(kind, scope, message_ids, source_ids, language, context, audience='researchers', pages=6):
    return output(jobs.create(ArtifactRequest(kind=kind, scope=scope, message_ids=message_ids,
        source_ids=source_ids, language=language, context=context, audience=audience, pages=pages)))

@mcp.tool()
def create_governance_chart(scope: str, message_ids: list[str], source_ids: list[str],
                             language: str = 'zh-TW', context: str = '') -> str:
    """Create a chart draft from an explicitly selected answer/conversation and authorized source IDs.
    Numeric charts require traceable numbers. Review and confirm the draft before SVG/PNG rendering.
    """
    return artifact('chart', scope, message_ids, source_ids, language, context)

@mcp.tool()
def create_governance_report(scope: str, message_ids: list[str], source_ids: list[str],
                              language: str = 'zh-TW', context: str = '') -> str:
    """Create a report draft. Original evidence is reloaded; confirm it to render a downloadable PDF."""
    return artifact('pdf', scope, message_ids, source_ids, language, context)

@mcp.tool()
def create_governance_slides(scope: str, message_ids: list[str], source_ids: list[str],
                              language: str = 'zh-TW', context: str = '', audience: str = 'researchers', pages: int = 6) -> str:
    """Create an outline for editable PPTX slides. Review audience, page count and outline before confirming."""
    return artifact('pptx', scope, message_ids, source_ids, language, context, audience, pages)

@mcp.tool()
def translate_governance_document(document_id: str, target_language: str, mode: str,
                                    block_ids: Optional[list[str]] = None,
                                    acknowledge_extraction_limits: bool = False) -> str:
    """Translate an authorized original document in passage or document mode; never overwrite/index the translation.
    Full translation may fail if OCR is required. Outputs are AI-assisted, not official translations.
    """
    return output(jobs.create(ArtifactRequest(kind='translation', scope=mode, source_ids=[document_id],
        language=target_language, block_ids=block_ids or [], acknowledge_extraction_limits=acknowledge_extraction_limits)))

@mcp.tool()
def read_governance_document(document_id: str) -> str:
    """Read authorized original paragraphs, IDs, page locations, version and extraction limitations."""
    return output(documents.describe(documents.get(document_id), True))

@mcp.tool()
def get_governance_task(task_id: str) -> str:
    """Get this user's task status/draft and authenticated download paths. IDs do not grant access."""
    job = jobs.get(task_id)
    if job.kind != 'index':
        sources, _ = jobs.inputs(ArtifactRequest.model_validate(job.payload), require_user())
        if sources != job.payload['sources']:
            raise ValueError('Source version changed; regenerate this task')
    result = jobs.describe(job)
    for file in (result.get('result') or {}).get('files', []):
        file['download_path'] = f'/api/artifacts/{task_id}/download/{file["name"]}'
        file.pop('key', None)
    return output(result)

@mcp.tool()
def update_governance_task(task_id: str, action: str, revision: int, draft: Optional[dict] = None) -> str:
    """Cancel, retry, or confirm a reviewed draft. Confirmation triggers actual file rendering."""
    return output(jobs.mutate(task_id, action, revision, draft))

@mcp.tool()
def delete_governance_task(task_id: str) -> str:
    """Delete this user's task and generated files."""
    jobs.remove(task_id)
    return output({'success':True})
