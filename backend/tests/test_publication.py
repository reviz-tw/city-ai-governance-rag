from unittest.mock import Mock
import pytest
from fastapi import HTTPException
from app.core.config import settings
from app.services import chunks,documents,jobs,store
from app.services.auth import User,current_user


def start(source,monkeypatch):
    monkeypatch.setattr(settings,'CHUNK_INDEX_ENABLED',True)
    monkeypatch.setattr(settings,'CHUNK_DATA_STORE_ID','synthetic-store')
    doc=documents.get(source['id'])
    task=chunks.publish(doc.id,doc.draft_revision,reviewed_diff=chunks.diff_hash(doc))
    return doc,task


def fake_index(monkeypatch,doc,visible=True,cancel=False):
    from google.cloud import storage
    client=Mock();client.bucket.return_value.name='synthetic-bucket'
    monkeypatch.setattr(storage,'Client',Mock(return_value=client))
    index_id=doc.id+'-v1'
    def request(path,payload=None,method='GET'):
        if path.endswith('documents:import'):
            return {'name':'synthetic-operation'}
        if path=='synthetic-operation':
            return {'done':True,'metadata':{'successCount':'1'}}
        if path.endswith('/chunks'):
            return {'chunks':[{'id':c['id'],'content':c['content']} for c in doc.draft]}
        if path.endswith(':search'):
            if cancel:
                with store.session() as db:
                    job=db.query(store.Job).filter_by(kind='index').one()
                    job.status='cancelled';db.commit()
            return {'results':[{'chunk':{'name':f'path/documents/{index_id}/chunks/c1'}}]} if visible else {}
        raise AssertionError(path)
    monkeypatch.setattr(chunks.cloud,'request',request)


def test_publish_requires_review_and_remote_search_visibility(source,monkeypatch):
    doc,task=start(source,monkeypatch)
    fake_index(monkeypatch,doc)
    jobs.run(task['id'])
    assert jobs.get(task['id']).status=='completed'
    assert documents.get(doc.id).published_version==1
    assert chunks.list_index_chunks(doc.id+'-v1')[0]['content']==doc.draft[0]['content']
    with pytest.raises(HTTPException) as exc:
        chunks.publish(doc.id,doc.draft_revision,reviewed_diff='stale')
    assert exc.value.status_code==409


def test_import_success_without_search_visibility_is_not_publication(source,monkeypatch):
    doc,task=start(source,monkeypatch)
    fake_index(monkeypatch,doc,visible=False)
    jobs.run(task['id'])
    assert jobs.get(task['id']).status=='queued'
    assert jobs.get(task['id']).payload['resume_at']>chunks.time.time()
    assert documents.get(doc.id).published_version==0
    assert jobs.poll_once() is None


@pytest.mark.parametrize('operation_result',[
    {'metadata':{'totalCount':'1'}},
    {'done':True,'metadata':{'failureCount':'1'},'response':{'errorSamples':[
        {'code':14,'message':'Document is imported but not yet indexed. Document indexing is working in progress.'}]}}
])
def test_delayed_index_resumes_same_import_until_search_is_visible(source,monkeypatch,operation_result):
    doc,task=start(source,monkeypatch)
    fake_index(monkeypatch,doc)
    request=chunks.cloud.request
    imports=[]
    ready=[False]
    def delayed(path,payload=None,method='GET'):
        if path.endswith('documents:import'):
            imports.append(path)
        if path=='synthetic-operation' and not ready[0]:
            return operation_result
        if path.endswith(':search') and not ready[0]:
            return {}
        return request(path,payload,method)
    monkeypatch.setattr(chunks.cloud,'request',delayed)
    jobs.run(task['id'])
    assert jobs.get(task['id']).status=='queued'
    assert documents.get(doc.id).published_version==0
    with store.session() as db:
        assert db.get(store.Publication,doc.id+':1').status=='pending'
    ready[0]=True
    jobs.run(task['id'])
    assert len(imports)==1
    assert jobs.get(task['id']).status=='completed'
    assert documents.get(doc.id).published_version==1


def test_fatal_import_error_requires_fresh_import_on_explicit_retry(source,monkeypatch):
    doc,task=start(source,monkeypatch)
    fake_index(monkeypatch,doc)
    request=chunks.cloud.request
    def rejected(path,payload=None,method='GET'):
        if path=='synthetic-operation':
            return {'done':True,'response':{'errorSamples':[{'code':3,'message':'Invalid chunk format'}]}}
        return request(path,payload,method)
    monkeypatch.setattr(chunks.cloud,'request',rejected)
    jobs.run(task['id'])
    failed=jobs.get(task['id'])
    assert failed.status=='failed'
    assert documents.get(doc.id).published_version==0
    jobs.mutate(task['id'],'retry',failed.revision)
    with store.session() as db:
        publication=db.get(store.Publication,doc.id+':1')
        assert publication.status=='pending' and publication.operation is None


@pytest.mark.parametrize('cleanup',['remove','expire','worker_stopped'])
def test_abandoned_index_task_does_not_strand_document(source,monkeypatch,cleanup):
    doc,task=start(source,monkeypatch)
    if cleanup=='remove':
        jobs.remove(task['id'])
    else:
        with store.session() as db:
            job=db.get(store.Job,task['id'])
            if cleanup=='expire':
                job.expires_at=0
            else:
                job.status,job.lease_until='running',0
            db.commit()
        (jobs.purge_expired if cleanup=='expire' else jobs.poll_once)()
    with store.session() as db:
        assert db.get(store.Publication,doc.id+':1').status=='failed'
    next_task=chunks.publish(doc.id,doc.draft_revision,reviewed_diff=chunks.diff_hash(documents.get(doc.id)))
    assert next_task['status']=='queued'


def test_cancellation_cannot_move_publication_pointer(source,monkeypatch):
    doc,task=start(source,monkeypatch)
    fake_index(monkeypatch,doc,cancel=True)
    jobs.run(task['id'])
    assert jobs.get(task['id']).status=='cancelled'
    assert documents.get(doc.id).published_version==0


def test_reader_cannot_see_unpublished_draft(source):
    with store.session() as db:
        doc=db.get(store.Document,source['id']);doc.shared=True;db.commit()
    token=current_user.set(User('reader','reader@example.test'))
    try:
        view=documents.describe(documents.get(source['id']),True)
        assert 'blocks' in view and 'draft' not in view and not view['editable']
    finally:
        current_user.reset(token)


def test_long_translation_segments_preserve_exact_original_ranges():
    text=('這是保留条件與數字 2026 的長篇測試段落。'*600)
    segments=jobs.translation_segments([{'id':'p1','text':text,'page':7,'kind':'paragraph','cells':None}])
    assert ''.join(s['text'] for s in segments)==text
    assert all(s['text']==text[s['start']:s['end']] and len(s['text'])<=4000 for s in segments)
    assert all(s['original_block_id']=='p1' and s['page']==7 for s in segments)

def test_rollback_reimports_previous_content_and_retry_rejects_new_base(source,monkeypatch):
    doc,task=start(source,monkeypatch)
    fake_index(monkeypatch,doc)
    jobs.run(task['id'])
    with store.session() as db:
        original=db.get(store.Publication,doc.id+':1')
        newer=store.Publication(id=doc.id+':2',document_id=doc.id,version=2,previous_version=1,
            chunks=[{**doc.draft[0],'content':'Reviewed replacement'}],operator='editor@example.test',
            status='published',index_document_id=doc.id+'-v2')
        db.add(newer)
        db.get(store.Document,doc.id).published_version=2
        db.commit()
    rollback=chunks.publish(doc.id,doc.draft_revision,rollback=True)
    with store.session() as db:
        candidate=db.get(store.Publication,doc.id+':3')
        assert candidate.chunks==original.chunks and candidate.previous_version==2
        assert db.get(store.Document,doc.id).published_version==2
    cancelled=jobs.mutate(rollback['id'],'cancel',rollback['revision'])
    retried=jobs.mutate(rollback['id'],'retry',cancelled['revision'])
    assert retried['status']=='queued'
    cancelled=jobs.mutate(rollback['id'],'cancel',retried['revision'])
    with store.session() as db:
        db.get(store.Document,doc.id).published_version=4
        db.commit()
    with pytest.raises(HTTPException) as error:
        jobs.mutate(rollback['id'],'retry',cancelled['revision'])
    assert error.value.status_code==409
