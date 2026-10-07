import hashlib
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from app.core.config import settings
from app.services import documents,docling_pipeline,rechunk,store,jobs,auth

@pytest.fixture
def parser(monkeypatch):
    monkeypatch.setattr(settings,'DOCLING_PYTHON','/isolated/python')
    def parse(data,filename):
        block=dict(id='dl-source',text='政策條文：高風險案件必須人工審查。',page=1,kind='paragraph')
        return dict(blocks=[block],chunks=[dict(id='dlc1',order=0,content='AI 治理\n'+block['text'],
            refs=[dict(block_id=block['id'],start=0,end=len(block['text']),page=1)],algorithm='docling-hybrid-v1')],
            warnings=[],original_hash=hashlib.sha256(data).hexdigest(),parser_version='2.134.0',tokenizer='cl100k_base',
            max_tokens=768,schema_version=1,source_reference_precision='document-element')
    monkeypatch.setattr(docling_pipeline,'parse',parse)
    return parse


def test_upload_routes_through_docling(parser):
    doc=documents.create(b'synthetic original','policy.pdf','application/pdf',{'language':'zh-TW'})
    value=documents.describe(documents.get(doc['id']),True)
    assert value['draft'][0]['algorithm']=='docling-hybrid-v1'
    assert value['metadata']['docling']['parser_version']=='2.134.0'
    assert value['original_hash']==hashlib.sha256(b'synthetic original').hexdigest()


def test_apply_preserves_published_blocks_and_original(source,parser):
    doc=documents.get(source['id'])
    with store.session() as db:
        publication=store.Publication(id=doc.id+':1',document_id=doc.id,version=1,chunks=doc.draft,operator='initial',status='published')
        saved=db.get(store.Document,doc.id);saved.published_version=1;saved.index_status='indexed'
        db.add(publication);db.commit()
    proposed=rechunk.generate(doc.id)
    assert proposed['chunks']==1
    result=rechunk.apply(doc.id,proposed['id'],doc.draft_revision,preserve_manual=True)
    assert result['status']=='applied'
    saved=documents.get(doc.id)
    assert saved.original_key==doc.original_key and saved.original_hash==doc.original_hash
    assert saved.blocks[:len(doc.blocks)]==doc.blocks
    assert saved.published_version==1 and saved.index_status=='indexed'
    with store.session() as db:
        assert db.get(store.Publication,doc.id+':1').chunks==doc.draft
        snapshots=list(db.scalars(select(store.DraftRevision).where(store.DraftRevision.document_id==doc.id)))
        assert any(s.chunks==doc.draft for s in snapshots)
    assert rechunk.generate(doc.id)['status']=='already-updated'


def test_any_review_protects_source_even_older_version(source,parser):
    with store.session() as db:
        db.add(store.DocumentReview(id='other-person',document_id=source['id'],version=1,
            reviewer_id='other-admin',reviewer_email='other@example.test'));db.commit()
    assert source['id'] not in rechunk.eligible_ids()
    with pytest.raises(HTTPException) as e:rechunk.generate(source['id'])
    assert e.value.status_code==409


def test_review_added_during_parse_rejects_candidate(source,parser,monkeypatch):
    def parse(data,filename):
        value=parser(data,filename)
        with store.session() as db:
            db.add(store.DocumentReview(id='new-review',document_id=source['id'],version=1,
                reviewer_id='other',reviewer_email='other@example.test'));db.commit()
        return value
    monkeypatch.setattr(docling_pipeline,'parse',parse)
    with pytest.raises(HTTPException):rechunk.generate(source['id'])
    assert rechunk.list_proposals(source['id'])==[]


def test_manual_draft_saved_as_candidate_without_overwrite(source,parser):
    from app.services import chunks
    doc=documents.get(source['id']);edited=[{**c,'content':c['content']+' 人工補充'} for c in doc.draft]
    chunks.save(doc.id,doc.draft_revision,edited)
    current=documents.get(doc.id)
    proposed=rechunk.generate(doc.id)
    result=rechunk.apply(doc.id,proposed['id'],current.draft_revision,preserve_manual=True)
    assert result['status']=='manual-draft-preserved'
    assert documents.get(doc.id).draft==edited
    assert rechunk.proposal_detail(doc.id,proposed['id'])['chunks'][0]['algorithm']=='docling-hybrid-v1'
    # Explicit editor action can apply the candidate; the saved draft remains in revisions.
    assert rechunk.apply(doc.id,proposed['id'],current.draft_revision)['status']=='applied'


def test_revision_conflict_and_original_hash_failure(source,parser):
    proposed=rechunk.generate(source['id'])
    with store.session() as db:
        db.get(store.Document,source['id']).draft_revision+=1;db.commit()
    with pytest.raises(HTTPException):rechunk.apply(source['id'],proposed['id'],source['draft_revision'])
    doc=documents.get(source['id']);store.put_bytes(doc.original_key,b'changed','text/plain')
    with pytest.raises(HTTPException):rechunk.generate(source['id'])


def test_worker_uses_job_owner_and_produces_durable_candidate(source,parser):
    queued=rechunk.enqueue(source['id'],source['draft_revision'])
    assert rechunk.enqueue(source['id'],source['draft_revision'])['id']==queued['id']
    token=auth.current_user.set(None)
    try:jobs.run(queued['id'])
    finally:auth.current_user.reset(token)
    with store.session() as db:
        job=db.get(store.Job,queued['id'])
        assert job.status=='completed'
        assert job.result['chunks']==1
    assert documents.get(source['id']).draft_revision==source['draft_revision']
    # Polling uses the same route as the browser, without artifact-source validation.
    from app.api.workspace import artifact
    assert artifact(queued['id'])['status']=='completed'


def test_unconfigured_processor_does_not_pretend_to_rechunk(source):
    with pytest.raises(HTTPException) as e:rechunk.generate(source['id'])
    assert e.value.status_code==503
    assert rechunk.list_proposals(source['id'])==[]


def test_deployed_batch_only_admin_can_apply_and_preserves_reviewed_sources(source,parser):
    with pytest.raises(HTTPException) as error:
        rechunk.enqueue(source['id'],source['draft_revision'],apply_unreviewed=True)
    assert error.value.status_code==403
    token=auth.current_user.set(auth.User('admin','admin@example.test'))
    try:
        job=rechunk.enqueue(source['id'],source['draft_revision'],apply_unreviewed=True)
        jobs.run(job['id'])
        assert documents.get(source['id']).draft_revision==source['draft_revision']+1
        from app.api.workspace import artifact
        assert artifact(job['id'])['result']['status']=='applied'
    finally:auth.current_user.reset(token)


def test_large_stored_source_uses_trusted_storage_not_http_upload(monkeypatch):
    import requests
    from google.oauth2 import id_token
    monkeypatch.setattr(settings,'DOCLING_SERVICE_URL','https://processor.example.test')
    monkeypatch.setattr(settings,'GCS_BUCKET_NAME','original-sources')
    monkeypatch.setattr(id_token,'fetch_id_token',lambda *args:'test-token')
    data=b'x'*(21*1024*1024)
    block=dict(id='b',text='Policy',page=1)
    payload=dict(schema_version=1,original_hash=hashlib.sha256(data).hexdigest(),blocks=[block],
        chunks=[dict(id='c',order=0,content='Policy',refs=[dict(block_id='b',start=0,end=6,page=1)])])
    captured={}
    class Response:
        status_code=200
        def json(self):return payload
    def post(url,**kwargs):captured.update(url=url,**kwargs);return Response()
    monkeypatch.setattr(requests,'post',post)
    uri='gs://original-sources/documents/report.pdf'
    assert docling_pipeline.parse(data,'report.pdf',source_uri=uri)==payload
    assert captured['url'].endswith('/parse-source') and captured['json']['source_uri']==uri
    assert 'files' not in captured
    monkeypatch.setattr(settings,'ARTIFACT_GCS_BUCKET','managed-sources')
    assert docling_pipeline.parse(data,'report.pdf',source_uri='gs://managed-sources/managed-originals/report.pdf')==payload
    with pytest.raises(HTTPException):docling_pipeline.parse(data,'report.pdf',source_uri='gs://other/documents/report.pdf')
    with pytest.raises(HTTPException):docling_pipeline.parse(data,'report.pdf')


def test_large_managed_original_normalizes_its_existing_storage_key(source,parser,monkeypatch):
    monkeypatch.setattr(settings,'DOCLING_SERVICE_URL','https://processor.example.test')
    monkeypatch.setattr(settings,'ARTIFACT_GCS_BUCKET','managed-sources')
    data=b'x'*(21*1024*1024)
    with store.session() as db:
        db.get(store.Document,source['id']).original_hash=hashlib.sha256(data).hexdigest();db.commit()
    monkeypatch.setattr(store,'get_bytes',lambda key:data)
    captured={}
    def parse(data,filename,**kwargs):captured.update(kwargs);return parser(data,filename)
    monkeypatch.setattr(docling_pipeline,'parse',parse)
    assert rechunk.generate(source['id'])['status']=='ready'
    assert captured['source_uri'].startswith('gs://managed-sources/managed-originals/')
