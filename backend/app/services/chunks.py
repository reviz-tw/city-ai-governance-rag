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
from app.services.auth import require_user, User, allowed_user


class IndexImportRejected(ValueError):
    pass


def validate(chunks, blocks):
    if not chunks or len(chunks) > 10000:
        raise ValueError('A draft needs 1–10000 chunks')
    known = {b['id']:b for b in blocks}
    ids = set()
    total_chars = 0
    for index, chunk in enumerate(chunks):
        identifier = chunk.get('id', '')
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', identifier) or identifier in ids:
            raise ValueError('Chunk IDs must be unique and valid')
        ids.add(identifier)
        if chunk.get('order') != index or not chunk.get('content','').strip() or len(chunk['content']) > 12000:
            raise ValueError('Invalid chunk order or text length')
        total_chars += len(chunk['content'])
        if total_chars > 2000000:
            raise ValueError('Draft text exceeds 2000000 characters')
        if not chunk.get('refs'):
            raise ValueError('Original source ranges are required')
        for ref in chunk['refs']:
            block = known.get(ref.get('block_id'))
            if not block or not 0 <= ref.get('start',-1) < ref.get('end',-1) <= len(block['text']):
                raise ValueError('Invalid original source range')
            if ref.get('page') != block['page']:
                raise ValueError('Source page does not match the original')


def save(document_id, revision, chunks, reset=False, chunk_size=1500):
    documents.get(document_id, edit=True)
    with store.session() as db:
        doc = db.scalar(select(store.Document).where(store.Document.id==document_id).with_for_update())
        if doc.draft_revision != revision:
            raise HTTPException(409, 'Draft changed; refresh before saving')
        chunks = documents.baseline(doc.blocks, chunk_size, reflow_pdf=doc.mime == 'application/pdf' or doc.original_key.lower().endswith('.pdf')) if reset else chunks
        validate(chunks, doc.blocks)
        doc.draft, doc.draft_revision = chunks, doc.draft_revision+1
        db.add(store.DraftRevision(id=f'{doc.id}:{doc.draft_revision}', document_id=doc.id,
               revision=doc.draft_revision,chunks=chunks,operator=require_user().email))
        db.commit()
        return documents.describe(doc, True)


def preview_reflow(document_id, revision, values):
    """Preview the current editor contents without saving or publishing them."""
    from app.services.text_layout import reflow
    doc = documents.get(document_id, edit=True)
    if doc.draft_revision != revision:
        raise HTTPException(409, 'Draft changed; refresh before saving')
    validate(values, doc.blocks)
    protected = {b['id'] for b in doc.blocks if b.get('kind') in {'table', 'code'}}
    result, changed = [], 0
    for chunk in values:
        content = chunk['content']
        if not any(r['block_id'] in protected for r in chunk['refs']):
            content, _ = reflow(content)
        changed += content != chunk['content']
        # Reflow is an edit; keep the original ranges, never invent new offsets.
        result.append({**chunk, 'content': content})
    validate(result, doc.blocks)
    return {'chunks': result, 'changed': changed}


def diff(document_id, language='zh'):
    chunk_label, reference_label, page_label, published_label, draft_label = {
        'zh': ('切片', '原文範圍', '頁', '已發布', '草稿'),
        'en': ('Chunk', 'Original range', 'Page', 'Published', 'Draft'),
        'ja': ('チャンク', '原文範囲', 'ページ', '公開済み', '下書き'),
        'fr': ('Segment', 'Plage originale', 'Page', 'Publié', 'Brouillon'),
        'es': ('Fragmento', 'Rango original', 'Página', 'Publicado', 'Borrador'),
        'ru': ('Фрагмент', 'Диапазон оригинала', 'Страница', 'Опубликовано', 'Черновик'),
    }.get(language, ('Chunk', 'Original range', 'Page', 'Published', 'Draft'))
    doc = documents.get(document_id, edit=True)
    def snapshot(values):
        rendered=[]
        for index,chunk in enumerate(values):
            refs=', '.join(f"{r['block_id']}[{r['start']}:{r['end']}] {page_label} {r['page'] if r['page'] is not None else '—'}" for r in chunk['refs'])
            rendered.append(f"{chunk_label} {index+1} · {chunk['id']}\n{reference_label}: {refs}\n{chunk['content']}")
        return '\n\n'.join(rendered)
    with store.session() as db:
        previous = db.get(store.Publication, f'{doc.id}:{doc.published_version}')
        before = snapshot(previous.chunks) if previous else ''
    after = snapshot(doc.draft)
    return '\n'.join(difflib.unified_diff(before.splitlines(), after.splitlines(), fromfile=published_label, tofile=draft_label, lineterm=''))


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
        if len(chunks) > 1000:
            raise HTTPException(422, 'Reduce the draft to 1000 or fewer chunks before indexing')
        validate(chunks, doc.blocks)
        version = (db.scalar(select(func.max(store.Publication.version)).where(store.Publication.document_id==document_id)) or 0)+1
        publication = store.Publication(id=f'{doc.id}:{version}', document_id=doc.id, version=version,
                                        chunks=chunks, operator=user.email, previous_version=doc.published_version,
                                        index_document_id=index_prefix(doc.id,version))
        job = store.Job(id=uuid.uuid4().hex, owner=user.id, email=user.email, kind='index',
                        payload={'publication_id':publication.id,'index_format':'chunk-documents-v1',
                                 'data_store':settings.CHUNK_DATA_STORE_ID}, expires_at=time.time()+86400)
        doc.index_status = 'pending'
        db.add_all([publication, job])
        db.commit()
        from app.services.jobs import describe, dispatch_job
        dispatch_job(job)
        return describe(job)


def index_prefix(document_id, version):
    return f'cad-{hashlib.sha256(document_id.encode()).hexdigest()[:24]}-v{version}'


def index_id(publication, chunk):
    # Both caller IDs may be 100 characters; hashed IDs remain within the provider limit.
    return publication.index_document_id+'-'+hashlib.sha256(chunk['id'].encode()).hexdigest()[:24]


def manifest(doc, publication, original_uri):
    values=[]
    for chunk in publication.chunks:
        identifier=index_id(publication,chunk)
        pages=[r['page'] for r in chunk['refs'] if r['page'] is not None]
        metadata=dict(document_id=doc.id,version=publication.version,chunk_id=chunk['id'],
            publication_key=publication.index_document_id,title=doc.title,language=doc.language,
            city=doc.metadata_json.get('city',''),original_uri=original_uri,original_sha256=doc.original_hash,
            content_sha256=hashlib.sha256(chunk['content'].encode()).hexdigest())
        if pages:metadata.update(page_start=min(pages),page_end=max(pages))
        values.append({'id':identifier,'structData':metadata,'content':{'mimeType':'text/plain',
            'uri':f'gs://{settings.GCS_BUCKET_NAME}/managed-chunks/{doc.id}/v{publication.version}/{identifier}.txt'}})
    return values


def upload_immutable(bucket, key, content, mime):
    from google.api_core.exceptions import PreconditionFailed
    blob=bucket.blob(key)
    try:
        blob.upload_from_string(content,content_type=mime,if_generation_match=0)
    except PreconditionFailed:
        expected=content.encode() if isinstance(content,str) else content
        if blob.download_as_bytes()!=expected:
            raise ValueError('A frozen publication file was modified') from None


def search_publication(publication, checkpoint_fn=None):
    """Every document must appear in standard Search, not just Documents.get/list."""
    found={};page_token='';seen_tokens=set()
    while True:
        if checkpoint_fn:checkpoint_fn()
        response=cloud.request(cloud.search_path(),{
            'query':'','pageSize':100,'pageToken':page_token,
            'filter':'publication_key: ANY('+json.dumps(publication.index_document_id)+')',
            'contentSearchSpec':{'searchResultMode':'DOCUMENTS'}},'POST')
        for item in response.get('results',[]):
            remote=item.get('document',{})
            found[remote.get('id')]=remote
        page_token=response.get('nextPageToken')
        if not page_token:break
        if page_token in seen_tokens:raise ValueError('Search repeated its pagination token')
        seen_tokens.add(page_token)
        if len(found)>1000:raise ValueError('Unexpected publication document count')
    return found


def matches(publication, remote):
    expected={index_id(publication,c):c for c in publication.chunks}
    if set(remote)!=set(expected):return False
    for identifier,chunk in expected.items():
        metadata=remote[identifier].get('structData',{})
        if (metadata.get('document_id')!=publication.document_id or metadata.get('version')!=publication.version
            or metadata.get('chunk_id')!=chunk['id'] or metadata.get('publication_key')!=publication.index_document_id
            or metadata.get('content_sha256')!=hashlib.sha256(chunk['content'].encode()).hexdigest()):
            return False
    return True


def cleanup_previous(publication):
    if not publication.previous_version:return
    with store.session() as db:
        old=db.get(store.Publication,f'{publication.document_id}:{publication.previous_version}')
    if not old or not (old.index_document_id or '').startswith('cad-'):return
    for chunk in old.chunks:
        cloud.request(cloud.store_path()+'/branches/0/documents/'+index_id(old,chunk),method='DELETE',allow_missing=True)


def cleanup_pending():
    if not settings.CHUNK_INDEX_ENABLED:return
    with store.session() as db:
        pending=list(db.scalars(select(store.Publication).where(
            store.Publication.status=='published',
            store.Publication.error.like('Old index cleanup pending%')).limit(5)))
    for publication in pending:
        try:
            cleanup_previous(publication)
        except Exception:
            continue
        with store.session() as db:
            doc=db.get(store.Document,publication.document_id)
            db.get(store.Publication,publication.id).error=None
            if doc.published_version==publication.version and doc.index_status=='indexed_cleanup_pending':
                doc.index_status='indexed'
            db.commit()


def run_publication(job):
    from google.cloud import storage
    from app.services.jobs import checkpoint, defer
    with store.session() as db:
        pub=db.get(store.Publication,job.payload['publication_id'])
        doc=db.get(store.Document,pub.document_id)
    try:
        if (not settings.CHUNK_INDEX_ENABLED or job.payload.get('index_format')!='chunk-documents-v1'
            or job.payload.get('data_store')!=settings.CHUNK_DATA_STORE_ID):
            raise ValueError('Publication backend changed; create a new publication')
        operator=allowed_user(User(job.owner,job.email))
        if not operator.editor or not (operator.admin or doc.owner==operator.id):
            raise ValueError('Document publishing permission revoked')
        if pub.status!='pending' or pub.previous_version!=doc.published_version:
            raise ValueError('Publication base changed; review a new publication')
        checkpoint(job.id,job.attempt,10)
        documents.evidence(doc.id,operator)
        if not pub.operation:
            bucket=storage.Client(project=settings.GCP_PROJECT_ID).bucket(settings.GCS_BUCKET_NAME)
            original_uri=doc.original_key
            if not original_uri.startswith('gs://'):
                original_key=f'managed-originals/{doc.id}/{doc.original_hash}'
                upload_immutable(bucket,original_key,store.get_bytes(doc.original_key),doc.mime)
                original_uri=f'gs://{bucket.name}/{original_key}'
            records=manifest(doc,pub,original_uri)
            for position,(chunk,record) in enumerate(zip(pub.chunks,records)):
                key=record['content']['uri'].split('/',3)[-1]
                upload_immutable(bucket,key,chunk['content'],'text/plain; charset=utf-8')
                if position%20==0:checkpoint(job.id,job.attempt,20)
            manifest_key=f'managed-chunks/{doc.id}/v{pub.version}/manifest.jsonl'
            upload_immutable(bucket,manifest_key,'\n'.join(json.dumps(r,ensure_ascii=False) for r in records)+'\n','application/x-ndjson')
            result=cloud.request(cloud.store_path()+'/branches/0/documents:import',{
                'gcsSource':{'inputUris':[f'gs://{bucket.name}/{manifest_key}'],'dataSchema':'document'},
                'reconciliationMode':'INCREMENTAL'},'POST')
            with store.session() as db:
                db.get(store.Publication,pub.id).operation=result['name'];db.commit()
            pub.operation=result['name']
        result=cloud.request(pub.operation)
        if not result.get('done'):return defer(job,delay=120,progress=30)
        errors=result.get('response',{}).get('errorSamples',[])
        pending=bool(errors) and all(e.get('code')==14 and 'imported but not yet indexed' in e.get('message','').lower() for e in errors)
        if result.get('error') or ((errors or int(result.get('metadata',{}).get('failureCount',0))) and not pending):
            raise IndexImportRejected('Standard document import failed')
        checkpoint(job.id,job.attempt,70)
        if not matches(pub,search_publication(pub,lambda:checkpoint(job.id,job.attempt,70))):
            return defer(job,delay=120,progress=70)
        documents.evidence(doc.id,operator)
        with store.session() as db:
            active_job=db.scalar(select(store.Job).where(store.Job.id==job.id).with_for_update())
            if not active_job or active_job.status!='running' or active_job.attempt!=job.attempt or active_job.expires_at<=time.time():
                raise InterruptedError('Publication cancelled or replaced')
            active=db.scalar(select(store.Document).where(store.Document.id==doc.id).with_for_update())
            publication=db.scalar(select(store.Publication).where(store.Publication.id==pub.id).with_for_update())
            if publication.status!='pending' or active.published_version!=pub.previous_version:
                raise ValueError('Publication base changed')
            if not operator.editor or not (operator.admin or active.owner==operator.id):
                raise ValueError('Document publishing permission revoked')
            active.published_version,active.index_status=pub.version,'indexed'
            publication.status,publication.error='published',None
            completed=dict(document_id=doc.id,published_version=pub.version,verified_chunks=len(pub.chunks),index_format='chunk-documents-v1')
            active_job.status,active_job.progress,active_job.result='completed',100,completed
            active_job.revision,active_job.updated_at=active_job.revision+1,time.time()
            db.commit()
        try:
            cleanup_previous(pub)
        except Exception:
            with store.session() as db:
                db.get(store.Publication,pub.id).error='Old index cleanup pending; retrieval excludes old versions'
                db.get(store.Document,doc.id).index_status='indexed_cleanup_pending';db.commit()
        return completed
    except cloud.IndexNotReady:
        return defer(job,delay=120,progress=70)
    except Exception as exc:
        with store.session() as db:
            active=db.get(store.Publication,pub.id)
            if active and active.status=='pending':
                active.status,active.error=('cancelled' if isinstance(exc,InterruptedError) else 'failed'),type(exc).__name__
                document=db.get(store.Document,doc.id)
                document.index_status='indexed' if document.published_version else active.status
                db.commit()
        raise


def indexed(document_id):
    doc=documents.get(document_id,edit=True)
    with store.session() as db:
        pub=db.get(store.Publication,f'{doc.id}:{doc.published_version}')
    if not pub or not (pub.index_document_id or '').startswith('cad-'):
        return dict(version=doc.published_version,chunks=[],verified=False)
    remote=search_publication(pub)
    verified=matches(pub,remote)
    return dict(version=pub.version,chunks=pub.chunks if verified else [],verified=verified,
                indexed_documents=len(remote),index_format='chunk-documents-v1')


def search(query, city=None, languages=None):
    if not settings.CHUNK_INDEX_ENABLED or not settings.CHUNK_DATA_STORE_ID:return []
    user=require_user()
    with store.session() as db:
        eligible={p.index_document_id:(d,p) for d,p in db.execute(select(store.Document,store.Publication).join(
            store.Publication,store.Publication.document_id==store.Document.id).where(
            store.Publication.version==store.Document.published_version,store.Publication.status=='published'))
            if documents.can_read(d,user) and (p.index_document_id or '').startswith('cad-')
            and (not city or d.metadata_json.get('city')==city) and (not languages or d.language in languages)}
    if not eligible:return []
    keys=list(eligible);ranked=[]
    # Scope Search BEFORE ranking, so private/stale documents cannot crowd out allowed evidence.
    for offset in range(0,len(keys),25):
        scope='publication_key: ANY('+', '.join(json.dumps(k) for k in keys[offset:offset+25])+')'
        response=cloud.request(cloud.search_path(),{'query':query,'pageSize':30,'filter':scope,
            'contentSearchSpec':{'searchResultMode':'DOCUMENTS'}},'POST')
        ranked.extend((rank,item) for rank,item in enumerate(response.get('results',[])))
    results=[];seen=set()
    with store.session() as db:
        for rank,item in sorted(ranked,key=lambda pair:pair[0]):
            remote=item.get('document',{});meta=remote.get('structData',{})
            pair=eligible.get(meta.get('publication_key'))
            if not pair:continue
            snapshot,pub=pair
            doc=db.get(store.Document,snapshot.id)
            if not doc or not documents.can_read(doc,user) or doc.published_version!=pub.version:continue
            chunk=next((c for c in pub.chunks if c['id']==meta.get('chunk_id')),None)
            if not chunk or remote.get('id')!=index_id(pub,chunk):continue
            if meta.get('content_sha256')!=hashlib.sha256(chunk['content'].encode()).hexdigest():continue
            if meta.get('document_id')!=doc.id or meta.get('version')!=pub.version:continue
            if (doc.id,chunk['id']) in seen:continue
            seen.add((doc.id,chunk['id']))
            pages=[r['page'] for r in chunk['refs'] if r['page'] is not None]
            results.append(dict(id=doc.id,title=doc.title,link=f'/api/library/{doc.id}/original',
                snippets=[{'snippet':chunk['content']}],chunk_id=chunk['id'],refs=chunk['refs'],
                page_start=min(pages) if pages else None,page_end=max(pages) if pages else None,
                metadata={'document_id':doc.id,'language':doc.language,'version':pub.version}))
            if len(results)==30:break
    return results
