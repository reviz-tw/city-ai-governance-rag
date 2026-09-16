import difflib
import hashlib
import json
import re
import time
import uuid
from fastapi import HTTPException
from sqlalchemy import select, func
from app.core.config import settings
from app.services import store, documents, cloud
from app.services.auth import require_user, User


class IndexImportRejected(ValueError):
    pass


def validate(chunks, blocks):
    if not chunks or len(chunks) > 1000:
        raise ValueError('A document needs 1–1000 chunks')
    known = {b['id']:b for b in blocks}
    ids = set()
    for index, chunk in enumerate(chunks):
        identifier = chunk.get('id', '')
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', identifier) or identifier in ids:
            raise ValueError('Chunk IDs must be unique and valid')
        ids.add(identifier)
        if chunk.get('order') != index or not chunk.get('content','').strip() or len(chunk['content']) > 12000:
            raise ValueError('Invalid chunk order or text length')
        if not chunk.get('refs'):
            raise ValueError('Original source ranges are required')
        for ref in chunk['refs']:
            block = known.get(ref.get('block_id'))
            if not block or not 0 <= ref.get('start',-1) < ref.get('end',-1) <= len(block['text']):
                raise ValueError('Invalid original source range')
            if ref.get('page') != block['page']:
                raise ValueError('Source page does not match the original')


def save(document_id, revision, chunks, reset=False):
    documents.get(document_id, edit=True)
    with store.session() as db:
        doc = db.scalar(select(store.Document).where(store.Document.id==document_id).with_for_update())
        if doc.draft_revision != revision:
            raise HTTPException(409, 'Draft changed; refresh before saving')
        chunks = documents.baseline(doc.blocks) if reset else chunks
        validate(chunks, doc.blocks)
        doc.draft, doc.draft_revision = chunks, doc.draft_revision+1
        db.add(store.DraftRevision(id=f'{doc.id}:{doc.draft_revision}', document_id=doc.id,
               revision=doc.draft_revision,chunks=chunks,operator=require_user().email))
        db.commit()
        return documents.describe(doc, True)


def diff(document_id):
    doc = documents.get(document_id, edit=True)
    with store.session() as db:
        previous = db.get(store.Publication, f'{doc.id}:{doc.published_version}')
        before = '\n\n'.join(c['content'] for c in previous.chunks) if previous else ''
    after = '\n\n'.join(c['content'] for c in doc.draft)
    return '\n'.join(difflib.unified_diff(before.splitlines(), after.splitlines(), fromfile='published', tofile='draft', lineterm=''))


def diff_hash(doc):
    return hashlib.sha256(json.dumps([doc.published_version,doc.draft_revision,doc.draft],sort_keys=True).encode()).hexdigest()


def publish(document_id, revision, rollback=False, reviewed_diff=None):
    user = require_user()
    documents.get(document_id, edit=True)
    if not settings.CHUNK_INDEX_ENABLED or not settings.CHUNK_DATA_STORE_ID:
        raise HTTPException(503, 'Chunk indexing is not enabled; configure the verified data store first')
    with store.session() as db:
        doc = db.scalar(select(store.Document).where(store.Document.id==document_id).with_for_update())
        if doc.draft_revision != revision:
            raise HTTPException(409, 'Draft changed; review the updated diff')
        if not rollback and reviewed_diff != diff_hash(doc):
            raise HTTPException(409, 'Review the current publication diff before publishing')
        active = db.scalar(select(store.Publication).where(store.Publication.document_id==document_id,
                                                          store.Publication.status=='pending'))
        if active:
            raise HTTPException(409, 'A publication is already pending')
        chunks = doc.draft
        if rollback:
            old = db.scalar(select(store.Publication).where(store.Publication.document_id==document_id,
                            store.Publication.status=='published', store.Publication.version < doc.published_version)
                            .order_by(store.Publication.version.desc()))
            if not old:
                raise HTTPException(409, 'No previous usable publication')
            chunks = old.chunks
        validate(chunks, doc.blocks)
        version = (db.scalar(select(func.max(store.Publication.version)).where(store.Publication.document_id==document_id)) or 0)+1
        publication = store.Publication(id=f'{doc.id}:{version}', document_id=doc.id, version=version,
                                        chunks=chunks, operator=user.email, previous_version=doc.published_version)
        job = store.Job(id=uuid.uuid4().hex, owner=user.id, email=user.email, kind='index',
                        payload={'publication_id':publication.id}, expires_at=time.time()+86400)
        doc.index_status = 'pending'
        db.add_all([publication, job])
        db.commit()
        from app.services.jobs import describe, dispatch_job
        dispatch_job(job)
        return describe(job)


def payload(doc, publication, original_uri):
    values = []
    for chunk in publication.chunks:
        value = {'id':chunk['id'], 'content':chunk['content']}
        pages = [r['page'] for r in chunk['refs'] if r['page'] is not None]
        if pages:
            value['pageSpan'] = {'pageStart':min(pages), 'pageEnd':max(pages)}
        values.append(value)
    return {'documentMetadata':{'title':doc.title, 'uri':original_uri}, 'chunks':values}


def list_index_chunks(index_id):
    values, page_token = [], ''
    from urllib.parse import quote
    while True:
        suffix = '?pageToken='+quote(page_token) if page_token else ''
        response = cloud.request(cloud.store_path()+f'/branches/0/documents/{index_id}/chunks'+suffix)
        values.extend(response.get('chunks',[]))
        page_token = response.get('nextPageToken')
        if not page_token:
            return values


def run_publication(job):
    from google.cloud import storage
    from app.services.jobs import checkpoint, defer
    with store.session() as db:
        pub = db.get(store.Publication, job.payload['publication_id'])
        doc = db.get(store.Document, pub.document_id)
        operator = User(job.owner, job.email)
        old = db.get(store.Publication, f'{doc.id}:{pub.previous_version}')
    index_id = f'{doc.id}-v{pub.version}'
    try:
        if not operator.editor or not (operator.admin or doc.owner == operator.id):
            raise ValueError('Document publishing permission revoked')
        if pub.previous_version != doc.published_version:
            raise ValueError('Publication base changed; review a new publication')
        checkpoint(job.id, job.attempt, 20)
        documents.evidence(doc.id,operator)
        operation = pub.operation
        if not operation:
            bucket = storage.Client(project=settings.GCP_PROJECT_ID).bucket(settings.GCS_BUCKET_NAME)
            prefix = f'managed-index/{doc.id}/v{pub.version}'
            original_uri = doc.original_key
            if not original_uri.startswith('gs://'):
                original_key = f'managed-originals/{doc.id}/{doc.original_hash}'
                bucket.blob(original_key).upload_from_string(store.get_bytes(doc.original_key), content_type=doc.mime)
                original_uri = f'gs://{bucket.name}/{original_key}'
            chunk_key = prefix+'/chunks.json'
            bucket.blob(chunk_key).upload_from_string(json.dumps(payload(doc,pub,original_uri), ensure_ascii=False), content_type='application/json')
            manifest = {'id':index_id, 'structData':{'title':doc.title,'language':doc.language,
                        'city':doc.metadata_json.get('city',''), 'document_id':doc.id, 'version':pub.version},
                        'content':{'mimeType':'application/json','uri':f'gs://{bucket.name}/{chunk_key}'}}
            manifest_key = prefix+'/manifest.jsonl'
            bucket.blob(manifest_key).upload_from_string(json.dumps(manifest)+'\n', content_type='application/x-ndjson')
            response = cloud.request(cloud.store_path()+'/branches/0/documents:import',
                        {'gcsSource':{'inputUris':[f'gs://{bucket.name}/{manifest_key}'],'dataSchema':'document'},
                         'reconciliationMode':'INCREMENTAL'}, 'POST')
            operation = response['name']
            with store.session() as db:
                active = db.get(store.Publication,pub.id)
                active.operation, active.index_document_id = operation, index_id
                db.commit()
        checkpoint(job.id,job.attempt,30)
        result = cloud.request(operation)
        if not result.get('done'):
            return defer(job, delay=120, progress=30)
        errors = result.get('response',{}).get('errorSamples',[])
        # Google can finish the import LRO with code 14 while the separately
        # running indexer still works. Only this explicit state is provisional;
        # actual chunk contents AND Search visibility remain mandatory.
        indexing_pending = bool(errors) and all(error.get('code') == 14 and
            'imported but not yet indexed' in error.get('message','').lower() for error in errors)
        if result.get('error') or ((errors or int(result.get('metadata',{}).get('failureCount',0))) and not indexing_pending):
            raise IndexImportRejected('Index import failed')
        expected = {c['id']:c['content'] for c in pub.chunks}
        checkpoint(job.id,job.attempt,70)
        actual = list_index_chunks(index_id)
        if {c['id']:c['content'] for c in actual} != expected:
            return defer(job, delay=120, progress=70)
        checkpoint(job.id,job.attempt,85)
        visible = cloud.request(cloud.search_path(), {'query':pub.chunks[0]['content'][:150], 'pageSize':30,
            'contentSearchSpec':{'searchResultMode':'CHUNKS'}}, 'POST')
        if not any(f'/documents/{index_id}/chunks/' in item.get('chunk',{}).get('name','')
                   for item in visible.get('results',[])):
            return defer(job, delay=120, progress=85)
        # Require both remote contents and search visibility before exposing the new version.
        with store.session() as db:
            current_job = db.scalar(select(store.Job).where(store.Job.id==job.id).with_for_update())
            if not current_job or current_job.status != 'running' or current_job.attempt != job.attempt or current_job.expires_at <= time.time():
                raise InterruptedError('Publication cancelled or replaced')
            active = db.scalar(select(store.Document).where(store.Document.id==doc.id).with_for_update())
            active.published_version, active.index_status = pub.version, 'indexed'
            publication = db.get(store.Publication,pub.id)
            publication.status = 'published'
            db.commit()
        if old and old.index_document_id and old.index_document_id != index_id:
            try:
                cloud.request(cloud.store_path()+f'/branches/0/documents/{old.index_document_id}', method='DELETE')
            except Exception:
                with store.session() as db:
                    db.get(store.Publication,pub.id).error = 'Old index cleanup pending; retrieval excludes the old version'
                    db.get(store.Document,doc.id).index_status = 'indexed_cleanup_pending'
                    db.commit()
        return {'document_id':doc.id,'published_version':pub.version,'verified_chunks':len(actual)}
    except Exception as exc:
        with store.session() as db:
            active = db.get(store.Publication,pub.id)
            if active.status == 'published':
                active.error = 'cleanup_pending'
                db.get(store.Document,doc.id).index_status = 'indexed_cleanup_pending'
            else:
                active.status, active.error = ('cancelled' if isinstance(exc,InterruptedError) else 'failed'), type(exc).__name__
                document=db.get(store.Document,doc.id)
                document.index_status = 'indexed' if document.published_version else active.status
            db.commit()
        raise


def search(query, city=None, languages=None):
    if not settings.CHUNK_INDEX_ENABLED or not settings.CHUNK_DATA_STORE_ID:
        return []
    from app.pipelines.vertex_search import build_filter
    response = cloud.request(cloud.search_path(),
        {'query':query,'pageSize':30,'filter':build_filter(city,languages) or '',
         'contentSearchSpec':{'searchResultMode':'CHUNKS'}}, 'POST')
    results = []
    user = require_user()
    with store.session() as db:
        for item in response.get('results',[]):
            chunk = item.get('chunk',{})
            index_id = chunk.get('name','').split('/documents/')[-1].split('/chunks/')[0]
            publication = db.scalar(select(store.Publication).where(store.Publication.index_document_id==index_id))
            if not publication:
                continue
            doc = db.get(store.Document,publication.document_id)
            if not documents.can_read(doc,user) or publication.version != doc.published_version or publication.status != 'published':
                continue
            if city and doc.metadata_json.get('city') != city or languages and doc.language not in languages:
                continue
            results.append(dict(id=doc.id, title=doc.title, link=f'/api/library/{doc.id}/original',
                snippets=[{'snippet':chunk.get('content','')}], chunk_id=chunk['id'],
                page_start=chunk.get('pageSpan',{}).get('pageStart'), page_end=chunk.get('pageSpan',{}).get('pageEnd'),
                metadata={'document_id':doc.id,'language':doc.language,'version':publication.version}))
    return results
