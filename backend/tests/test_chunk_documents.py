import hashlib
from unittest.mock import Mock
import pytest
from app.core.config import settings
from app.services import chunks, documents, jobs, store
from app.services.auth import User, current_user
from test_publication import start, fake_index


def test_manifest_has_one_immutable_plain_text_document_per_chunk(source, monkeypatch):
    doc, task = start(source, monkeypatch)
    with store.session() as db:
        pub = db.get(store.Publication, doc.id+':1')
    pub.chunks = [{**c, 'id': 'x'*100+str(i)} for i,c in enumerate(doc.draft)]
    records = chunks.manifest(doc, pub, 'gs://original/file.pdf')
    assert len(records) == len(pub.chunks)
    for record, chunk in zip(records, pub.chunks):
        assert len(record['id']) <= 128
        assert 'chunks' not in record and record['content']['mimeType'] == 'text/plain'
        assert record['content']['uri'].endswith('/'+record['id']+'.txt')
        assert record['structData']['content_sha256'] == hashlib.sha256(chunk['content'].encode()).hexdigest()
        assert record['structData']['original_sha256'] == doc.original_hash


def test_schema_propagation_delay_keeps_publication_pending(source, monkeypatch):
    doc, task = start(source, monkeypatch)
    fake_index(monkeypatch, doc)
    request = chunks.cloud.request
    def delayed(path, *args, **kwargs):
        if path.endswith(':search'):
            raise chunks.cloud.IndexNotReady('metadata propagation')
        return request(path, *args, **kwargs)
    monkeypatch.setattr(chunks.cloud, 'request', delayed)
    jobs.run(task['id'])
    assert jobs.get(task['id']).status == 'queued'
    assert documents.get(doc.id).published_version == 0
    with store.session() as db:
        assert db.get(store.Publication, doc.id+':1').status == 'pending'


def test_search_enumerates_all_pages_without_wildcard(source, monkeypatch):
    doc, task = start(source, monkeypatch)
    with store.session() as db:
        pub = db.get(store.Publication, doc.id+':1')
    records = chunks.manifest(doc, pub, 'gs://original/file')
    seen = []
    def request(path, payload, method):
        assert payload['query'] == ''
        assert payload['contentSearchSpec']['searchResultMode'] == 'DOCUMENTS'
        seen.append(payload['pageToken'])
        if not payload['pageToken']:
            return {'results': [{'document': records[0]}], 'nextPageToken': 'page-2'}
        return {'results': []}
    monkeypatch.setattr(chunks.cloud, 'request', request)
    remote = chunks.search_publication(pub)
    assert seen == ['', 'page-2'] and chunks.matches(pub, remote)
    remote[records[0]['id']]['structData']['content_sha256'] = 'wrong'
    assert not chunks.matches(pub, remote)


def test_search_prefilters_permissions_and_rejects_stale_versions(source, monkeypatch):
    doc, task = start(source, monkeypatch)
    fake_index(monkeypatch, doc)
    jobs.run(task['id'])
    with store.session() as db:
        pub = db.get(store.Publication, doc.id+':1')
        db.get(store.Document, doc.id).shared = True
        db.commit()
    private = documents.create(b'Private unrelated policy.', 'private.txt', 'text/plain', {'language': 'ja'})
    private_doc = documents.get(private['id'])
    with store.session() as db:
        hidden = store.Publication(id=private_doc.id+':1', document_id=private_doc.id, version=1,
            index_document_id=chunks.index_prefix(private_doc.id, 1), chunks=private_doc.draft,
            operator='editor@example.test', status='published')
        db.add(hidden); db.get(store.Document, private_doc.id).published_version = 1; db.commit()
    public_record = chunks.manifest(doc, pub, 'gs://original/file')[0]
    hidden_record = chunks.manifest(private_doc, hidden, 'gs://original/private')[0]
    stale = {**public_record, 'id': 'old-id'}
    calls = []
    def request(path, payload, method):
        calls.append(payload)
        assert pub.index_document_id in payload['filter']
        assert hidden.index_document_id not in payload['filter']
        return {'results': [{'document': r} for r in [stale, hidden_record, public_record]]}
    monkeypatch.setattr(chunks.cloud, 'request', request)
    token = current_user.set(User('reader', 'reader@example.test'))
    try:
        result = chunks.search('市府使用人工智慧前應評估什麼？', languages=['en'])
        assert len(result) == 1
        assert result[0]['snippets'][0]['snippet'] == pub.chunks[0]['content']
        assert result[0]['metadata']['version'] == 1 and result[0]['refs'] == pub.chunks[0]['refs']
        assert chunks.search('privacy', city='unknown') == [] and len(calls) == 1
    finally:
        current_user.reset(token)


def test_cleanup_failure_does_not_undo_promotion_and_is_retried(source, monkeypatch):
    doc, task = start(source, monkeypatch)
    fake_index(monkeypatch, doc)
    cleanup = Mock(side_effect=RuntimeError('temporary deletion error'))
    monkeypatch.setattr(chunks, 'cleanup_previous', cleanup)
    jobs.run(task['id'])
    assert jobs.get(task['id']).status == 'completed'
    assert documents.get(doc.id).index_status == 'indexed_cleanup_pending'
    cleanup.side_effect = None
    chunks.cleanup_pending()
    assert documents.get(doc.id).index_status == 'indexed'
    assert cleanup.call_count == 2


def test_frozen_upload_is_idempotent_but_never_overwrites_changed_content():
    from google.api_core.exceptions import PreconditionFailed
    bucket = Mock()
    blob = bucket.blob.return_value
    blob.upload_from_string.side_effect = PreconditionFailed('already exists')
    blob.download_as_bytes.return_value = b'original'
    chunks.upload_immutable(bucket, 'version/chunk.txt', 'original', 'text/plain')
    assert blob.upload_from_string.call_args.kwargs['if_generation_match'] == 0
    with pytest.raises(ValueError, match='frozen'):
        chunks.upload_immutable(bucket, 'version/chunk.txt', 'changed', 'text/plain')


def test_shared_retrieve_never_reintroduces_legacy_snippets_after_publication(source, monkeypatch):
    from app.pipelines import vertex_search
    doc, task = start(source, monkeypatch)
    fake_index(monkeypatch, doc)
    jobs.run(task['id'])
    expected = [{'id': doc.id, 'chunk_id': 'reviewed', 'snippets': [{'snippet': 'Reviewed current content'}]}]
    monkeypatch.setattr(chunks, 'search', lambda *args: expected)
    monkeypatch.setattr(vertex_search, 'search_vertex_data_store', lambda *args, **kwargs: [{'id': 'legacy-id', 'snippets': [{'snippet': 'Outdated original'}]}])
    monkeypatch.setattr(documents, 'register_legacy', lambda result: doc.id)
    assert vertex_search.retrieve('policy') == expected


def test_old_cleanup_still_retries_after_another_publication_starts(source, monkeypatch):
    doc, task = start(source, monkeypatch)
    fake_index(monkeypatch, doc)
    monkeypatch.setattr(chunks, 'cleanup_previous', Mock(side_effect=RuntimeError('temporary')))
    jobs.run(task['id'])
    chunks.publish(doc.id, doc.draft_revision, reviewed_diff=chunks.diff_hash(documents.get(doc.id)))
    cleanup=Mock();monkeypatch.setattr(chunks, 'cleanup_previous', cleanup)
    chunks.cleanup_pending()
    assert cleanup.call_count==1
    assert documents.get(doc.id).index_status=='pending'
    with store.session() as db:
        assert db.get(store.Publication, doc.id+':1').error is None


def test_diff_exposes_boundary_and_provenance_changes_when_full_text_is_identical(source):
    doc=documents.get(source['id'])
    original=[dict(id='c'+str(i+1),order=i,content=b['text'],refs=[dict(block_id=b['id'],start=0,end=len(b['text']),page=b['page'])]) for i,b in enumerate(doc.blocks)]
    merged=[dict(id='c1',order=0,content='\n\n'.join(c['content'] for c in original),refs=[r for c in original for r in c['refs']])]
    with store.session() as db:
        db.add(store.Publication(id=doc.id+':1',document_id=doc.id,version=1,chunks=original,operator='editor@example.test',status='published'))
        active=db.get(store.Document,doc.id);active.published_version=1;active.draft=merged;db.commit()
    result=chunks.diff(doc.id)
    assert '-切片 2 · c2' in result and '原文範圍' in result
