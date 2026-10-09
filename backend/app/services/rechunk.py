"""Version-guarded, auditable Docling drafts. Never modify a published snapshot."""
import hashlib
import uuid
from pathlib import Path
from app.core.config import settings
from fastapi import HTTPException
from sqlalchemy import select
from app.services import store, documents, docling_pipeline, chunks
from app.services.auth import require_editor


def reviewed(db, doc):
    # Any person's explicit review protects this source, including older versions.
    return db.scalar(select(store.DocumentReview.id).where(store.DocumentReview.document_id==doc.id).limit(1)) is not None


def eligible_ids():
    user=require_editor()
    admin=user.admin
    with store.session() as db:
        query=select(store.Document.id).where(~select(store.DocumentReview.id)
            .where(store.DocumentReview.document_id==store.Document.id).exists())
        if not admin:query=query.where(store.Document.owner==user.id)
        return list(db.scalars(query.order_by(store.Document.id)))


def list_proposals(document_id):
    documents.get(document_id,edit=True)
    with store.session() as db:
        return [dict(id=p.id,status=p.status,base_revision=p.base_revision,chunks=len(p.chunks),
            created_at=p.created_at,details=p.details) for p in db.scalars(select(store.DoclingProposal)
            .where(store.DoclingProposal.document_id==document_id).order_by(store.DoclingProposal.created_at.desc()))]


def generate(document_id,checkpoint=None):
    user=require_editor()
    doc=documents.get(document_id,edit=True)
    with store.session() as db:
        if reviewed(db,doc):raise HTTPException(409,'Human-reviewed documents are protected')
        if doc.index_status=='pending':raise HTTPException(409,'Index publication is pending')
        current_proposal=db.scalar(select(store.DoclingProposal).where(store.DoclingProposal.document_id==doc.id,store.DoclingProposal.status=='applied').order_by(store.DoclingProposal.created_at.desc()))
        if (current_proposal and current_proposal.original_hash==doc.original_hash and current_proposal.chunks==doc.draft
            and current_proposal.details.get('max_tokens')==settings.DOCLING_CHUNK_TOKENS
            and current_proposal.details.get('parser_version')=='2.134.0'):
            return {'id':current_proposal.id,'status':'already-updated','chunks':len(doc.draft),'reused':True}
        existing=db.scalar(select(store.DoclingProposal).where(store.DoclingProposal.document_id==doc.id,
            store.DoclingProposal.original_hash==doc.original_hash,store.DoclingProposal.base_revision==doc.draft_revision,
            store.DoclingProposal.status=='ready'))
        if existing:return {'id':existing.id,'status':'ready','chunks':len(existing.chunks),'reused':True}
    data=store.get_bytes(doc.original_key)
    if hashlib.sha256(data).hexdigest()!=doc.original_hash:raise HTTPException(409,'Original file changed')
    filename=Path(doc.original_key).name
    if settings.DOCLING_SERVICE_URL and len(data)>20*1024*1024:
        uri=doc.original_key if doc.original_key.startswith('gs://') else f'gs://{settings.ARTIFACT_GCS_BUCKET}/{doc.original_key}'
        parsed=docling_pipeline.parse(data,filename,source_uri=uri)
    else:parsed=docling_pipeline.parse(data,filename)
    if checkpoint: checkpoint()
    details={k:parsed[k] for k in ('parser_version','tokenizer','max_tokens','schema_version','warnings','source_reference_precision')}
    with store.session() as db:
        current=db.scalar(select(store.Document).where(store.Document.id==doc.id).with_for_update())
        if reviewed(db,current) or current.draft_revision!=doc.draft_revision or current.original_hash!=doc.original_hash:
            raise HTTPException(409,'Source or review state changed during parsing')
        proposal=store.DoclingProposal(id=uuid.uuid4().hex,document_id=doc.id,original_hash=doc.original_hash,
            base_revision=doc.draft_revision,blocks=parsed['blocks'],chunks=parsed['chunks'],details=details,operator=user.email)
        db.add(proposal);db.commit()
        return {'id':proposal.id,'status':'ready','chunks':len(proposal.chunks),'reused':False}


def apply(document_id, proposal_id, revision, *, preserve_manual=False):
    user=require_editor();documents.get(document_id,edit=True)
    with store.session() as db:
        doc=db.scalar(select(store.Document).where(store.Document.id==document_id).with_for_update())
        proposal=db.get(store.DoclingProposal,proposal_id)
        if not proposal or proposal.document_id!=doc.id:raise HTTPException(404,'Docling draft not found')
        if (proposal.status!='ready' or proposal.base_revision!=revision or doc.draft_revision!=revision
            or proposal.original_hash!=doc.original_hash or reviewed(db,doc) or doc.index_status=='pending'):
            raise HTTPException(409,'Draft, source, publication or review state changed')
        if preserve_manual:
            publication=db.get(store.Publication,f'{doc.id}:{doc.published_version}')
            saved=db.scalar(select(store.DraftRevision.id).where(store.DraftRevision.document_id==doc.id).limit(1))
            untouched=doc.draft_revision==1 and not saved
            source_blocks=[b for b in doc.blocks if not b.get('extraction','').startswith('docling-')]
            baselines=[documents.baseline(source_blocks,1500,reflow_pdf=mode) for mode in (False,True)]
            matches_publication=publication and doc.draft==publication.chunks and any(doc.draft==baseline for baseline in baselines)
            # Even a published human edit is preserved: it may not yet be marked reviewed.
            manual_algorithm=any(c.get('algorithm','').startswith(('human','manual')) for c in doc.draft)
            if manual_algorithm or not (untouched or matches_publication):
                return {'status':'manual-draft-preserved','proposal_id':proposal.id}
        known={b['id']:b for b in doc.blocks}
        for block in proposal.blocks:
            if block['id'] in known and known[block['id']]!=block:raise HTTPException(409,'Immutable source block collision')
            known[block['id']]=block
        # Old block IDs remain valid for current publications, reviews and citations.
        combined=list(known.values())
        chunks.validate(proposal.chunks,combined)
        db.add(store.DraftRevision(id=f'{doc.id}:{doc.draft_revision}:docling-backup-{proposal.id[:8]}',
            document_id=doc.id,revision=doc.draft_revision,chunks=doc.draft,operator=user.email))
        doc.blocks=combined;doc.draft=proposal.chunks;doc.draft_revision+=1
        doc.metadata_json={**doc.metadata_json,'docling':proposal.details,'docling_proposal_id':proposal.id}
        db.add(store.DraftRevision(id=f'{doc.id}:{doc.draft_revision}',document_id=doc.id,
            revision=doc.draft_revision,chunks=doc.draft,operator=user.email))
        proposal.status='applied'
        db.commit()
        return {'status':'applied','proposal_id':proposal.id,'revision':doc.draft_revision,'chunks':len(doc.draft)}


def proposal_detail(document_id,proposal_id):
    documents.get(document_id,edit=True)
    with store.session() as db:
        proposal=db.get(store.DoclingProposal,proposal_id)
        if not proposal or proposal.document_id!=document_id:raise HTTPException(404,'Docling draft not found')
        return dict(id=proposal.id,blocks=proposal.blocks,chunks=proposal.chunks,details=proposal.details)


def enqueue(document_id,revision,*,apply_unreviewed=False):
    import time
    from app.services.jobs import dispatch_job,describe
    user=require_editor();doc=documents.get(document_id,edit=True)
    if apply_unreviewed and not user.admin:raise HTTPException(403,'Administrator required for batch application')
    if not docling_pipeline.enabled():raise HTTPException(503,'Docling worker is not configured')
    if doc.draft_revision!=revision:raise HTTPException(409,'Draft changed')
    with store.session() as db:
        if reviewed(db,doc):raise HTTPException(409,'Human-reviewed documents are protected')
        db.scalar(select(store.Document).where(store.Document.id==doc.id).with_for_update())
        pending=db.scalar(select(store.Job).where(store.Job.kind=='rechunk',store.Job.status.in_(['queued','running']),
            store.Job.payload['document_id'].as_string()==doc.id))
        if pending and pending.payload.get('document_id')==doc.id:return describe(pending)
        job=store.Job(id=uuid.uuid4().hex,owner=user.id,email=user.email,kind='rechunk',
            payload={'document_id':doc.id,'revision':revision,'original_hash':doc.original_hash,'apply_unreviewed':apply_unreviewed},expires_at=time.time()+7*86400)
        db.add(job);db.commit()
        dispatch_job(job)
        return describe(job)
