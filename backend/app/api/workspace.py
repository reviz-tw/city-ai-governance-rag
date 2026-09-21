import time
from pathlib import Path
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from app.models.artifacts import ArtifactRequest
from app.services import documents, jobs, store
from app.services.auth import require_user, require_editor

router = APIRouter(prefix='/api')

@router.get('/library')
def library():
    return documents.list_documents()

@router.get('/library/legacy')
def legacy_library():
    require_user()
    from app.pipelines.vertex_search import list_governance_documents
    return list_governance_documents()

class LegacyDraftRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=1024)

@router.post('/library/legacy-draft')
def legacy_draft(body: LegacyDraftRequest):
    user = require_editor()
    # The historical shared collection belongs to the workspace, not an individual editor.
    if not user.admin:
        raise HTTPException(403, 'Only an administrator can manage the historical collection')
    from app.pipelines.vertex_search import list_governance_documents
    item = next((item for item in list_governance_documents() if item['filename'] == body.filename), None)
    if item is None:
        raise HTTPException(404, 'Document not found')
    identifier = documents.register_legacy(dict(link=item['gcs_uri'], title=item['filename'], metadata=item))
    return documents.describe(documents.get(identifier, edit=True), include_content=True)

@router.post('/library')
async def upload(file: UploadFile = File(...), language: str = Form(''), city: str = Form(''),
                 cleaned_text: str | None = Form(None), rights_confirmed: bool = Form(False)):
    require_editor()
    if not rights_confirmed:
        raise HTTPException(422, 'Confirm the rights to process and translate this document')
    data = await file.read(20*1024*1024+1)
    return documents.create(data, file.filename or 'document.txt', file.content_type or 'application/octet-stream',
                            dict(language=language, city=city), cleaned_text)

@router.get('/library/{document_id}')
def document(document_id: str):
    return documents.describe(documents.get(document_id), include_content=True)

@router.get('/library/{document_id}/original')
def original(document_id: str):
    doc = documents.get(document_id)
    return Response(store.get_bytes(doc.original_key), media_type=doc.mime,
                    headers={'Content-Disposition':'attachment', 'Cache-Control':'private, no-store',
                             'X-Content-Type-Options':'nosniff'})

class SharingRequest(BaseModel):
    shared: bool = False
    readers: list[str] = Field(default_factory=list, max_length=100)
    revision: int

@router.patch('/library/{document_id}/sharing')
def sharing(document_id: str, body: SharingRequest):
    doc = documents.get(document_id, edit=True)
    with store.session() as db:
        active = db.scalar(select(store.Document).where(store.Document.id==doc.id).with_for_update())
        if active.draft_revision != body.revision:
            raise HTTPException(409, 'Document changed')
        active.shared, active.readers = body.shared, [s.strip().lower() for s in body.readers]
        active.draft_revision += 1
        db.commit()
        return documents.describe(active, True)

@router.post('/artifacts')
def create_artifact(body: ArtifactRequest):
    return jobs.create(body)

@router.get('/artifacts')
def list_artifacts():
    user = require_user()
    with store.session() as db:
        return [{k:v for k,v in jobs.describe(j).items() if k not in {'draft','result'}} for j in db.scalars(select(store.Job).where(store.Job.owner==user.id,
                    store.Job.expires_at > time.time()).order_by(store.Job.created_at.desc()).limit(50))]

@router.get('/artifacts/{job_id}')
def artifact(job_id: str):
    job = jobs.get(job_id)
    if job.kind != 'index':
        sources, _ = jobs.inputs(ArtifactRequest.model_validate(job.payload), require_user())
        result = jobs.describe(job)
        result['stale'] = sources != job.payload['sources']
        return result
    return jobs.describe(job)

class JobAction(BaseModel):
    revision: int
    draft: dict | None = None

@router.post('/artifacts/{job_id}/preview-draft')
def preview_draft(job_id: str, body: JobAction):
    from app.models.artifacts import ArtifactDraft
    from app.services import renderers
    job = jobs.get(job_id)
    if job.status != 'awaiting_review' or job.revision != body.revision:
        raise HTTPException(409, 'Draft changed; refresh before reviewing')
    try:
        draft = ArtifactDraft.model_validate(body.draft)
        _, blocks = jobs.inputs(ArtifactRequest.model_validate(job.payload), require_user())
        jobs.validate_draft(draft, blocks, job.kind)
        if draft.slides:
            renderers.pptx(draft.model_dump(), job.payload['language'], job.payload['sources'])
    except ValueError as exc:
        if 'readable slide area' in str(exc) or 'Shorten chart category' in str(exc):
            raise HTTPException(422, 'Slide text exceeds readable layout') from None
        raise HTTPException(422, 'Check draft fields and original citations') from None
    return {'slide_count':len(renderers.slide_plan(draft.model_dump(), job.payload['sources'])) if job.kind=='pptx' else None}

@router.post('/artifacts/{job_id}/{action}')
def artifact_action(job_id: str, action: str, body: JobAction):
    try:
        return jobs.mutate(job_id, action, body.revision, body.draft)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None

@router.delete('/artifacts/{job_id}')
def delete_artifact(job_id: str):
    jobs.remove(job_id)
    return {'success': True}

@router.get('/artifacts/{job_id}/download/{name}')
def download(job_id: str, name: str, inline: bool = False):
    job = jobs.get(job_id)
    if job.status != 'completed':
        raise HTTPException(409, 'File rendering is not complete')
    if job.kind != 'index':
        sources, _ = jobs.inputs(ArtifactRequest.model_validate(job.payload), require_user())
        if sources != job.payload['sources']:
            raise HTTPException(409, 'Source version changed; regenerate this artifact')
    file = next((f for f in (job.result or {}).get('files',[]) if f['name']==name), None)
    if not file:
        raise HTTPException(404, 'File not found')
    disposition = 'inline' if inline and file['mime'] == 'application/pdf' else 'attachment'
    return Response(store.get_bytes(file['key']), media_type=file['mime'],
                    headers={'Content-Disposition':f'{disposition}; filename="{name}"',
                             'Cache-Control':'private, no-store', 'X-Content-Type-Options':'nosniff'})

class ChunkDraftRequest(BaseModel):
    revision: int
    chunks: list[dict] = Field(default_factory=list, max_length=10000)
    reset: bool = False
    chunk_size: int = Field(default=1500, ge=100, le=5000)

@router.post('/library/{document_id}/draft')
def save_draft(document_id: str, body: ChunkDraftRequest):
    from app.services import chunks
    try:
        return chunks.save(document_id, body.revision, body.chunks, body.reset, body.chunk_size)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None

@router.post('/library/{document_id}/preview-reflow')
def preview_reflow(document_id: str, body: ChunkDraftRequest):
    from app.services import chunks
    try:
        return chunks.preview_reflow(document_id, body.revision, body.chunks)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None

@router.get('/library/{document_id}/diff')
def chunk_diff(document_id: str, language: str = 'zh'):
    from app.services import chunks
    doc=documents.get(document_id,edit=True)
    return {'diff':chunks.diff(document_id, language), 'hash':chunks.diff_hash(doc)}

class PublishRequest(BaseModel):
    revision: int
    reviewed_diff: str

@router.post('/library/{document_id}/publish')
def publish(document_id: str, body: PublishRequest):
    from app.services import chunks
    return chunks.publish(document_id, body.revision, reviewed_diff=body.reviewed_diff)

@router.post('/library/{document_id}/rollback')
def rollback(document_id: str, body: JobAction):
    from app.services import chunks
    return chunks.publish(document_id, body.revision, rollback=True)

@router.get('/library/{document_id}/publications')
def publications(document_id: str):
    doc = documents.get(document_id, edit=True)
    with store.session() as db:
        return [dict(version=p.version,status=p.status,operator=p.operator,created_at=p.created_at,
                     operation=p.operation,error=p.error,chunks=p.chunks)
                for p in db.scalars(select(store.Publication).where(store.Publication.document_id==doc.id)
                                    .order_by(store.Publication.version.desc()))]

@router.get('/library/{document_id}/revisions')
def draft_revisions(document_id: str):
    doc = documents.get(document_id, edit=True)
    with store.session() as db:
        return [dict(revision=r.revision,operator=r.operator,created_at=r.created_at,chunks=r.chunks)
                for r in db.scalars(select(store.DraftRevision).where(store.DraftRevision.document_id==doc.id)
                                    .order_by(store.DraftRevision.revision.desc()))]

@router.get('/library/{document_id}/indexed-chunks')
def indexed_chunks(document_id: str):
    from app.services.chunks import indexed
    return indexed(document_id)
