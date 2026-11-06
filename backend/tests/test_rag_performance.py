from sqlalchemy import event
from app.services import auth,accounts,chunks,store
from app.pipelines import vertex_search


def test_permissions_resolved_once_per_request_and_refreshed_after_disable(monkeypatch):
    calls=[];original=accounts.role_for
    def role(email):calls.append(email);return original(email)
    monkeypatch.setattr(accounts,'role_for',role)
    user=auth.allowed_user(auth.User('admin','admin@example.test'))
    for _ in range(100):assert user.admin and user.editor
    assert calls==['admin@example.test']
    with store.session() as db:
        db.get(store.WorkspaceAccount,'admin@example.test').active=False;db.commit()
    import pytest
    from fastapi import HTTPException
    with pytest.raises(HTTPException):auth.allowed_user(user)


def test_more_than_25_publications_use_one_scoped_search_without_loading_source_bodies(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings,'CHUNK_INDEX_ENABLED',True)
    monkeypatch.setattr(settings,'CHUNK_DATA_STORE_ID','test-store')
    with store.session() as db:
        for i in range(60):
            identifier='doc-'+str(i)
            db.add(store.Document(id=identifier,owner='editor',title=identifier,language='en',original_key='unused',original_hash='a'*64,mime='text/plain',published_version=1,blocks=[{'text':'body must not be loaded'}],draft=[]))
            db.add(store.Publication(id=identifier+':1',document_id=identifier,version=1,index_document_id='cad-'+str(i),chunks=[],operator='editor',status='published'))
        db.commit()
    statements=[];requests=[]
    def observe(connection,cursor,statement,*args):statements.append(statement)
    event.listen(store.engine(),'before_cursor_execute',observe)
    monkeypatch.setattr(chunks.cloud,'request',lambda path,payload,method:requests.append(payload) or {'results':[]})
    try:assert chunks.search('privacy')==[]
    finally:event.remove(store.engine(),'before_cursor_execute',observe)
    assert len(requests)==1
    assert all('"cad-'+str(i)+'"' in requests[0]['filter'] for i in range(60))
    assert sum('FROM workspace_accounts' in s for s in statements)==1
    assert not any('documents.blocks' in s or 'publications.chunks' in s for s in statements)


def test_full_evidence_budget_still_considers_legacy_search(monkeypatch):
    managed=[dict(snippets=[{'snippet':str(i)+'證據'*1800}]) for i in range(4)]
    monkeypatch.setattr(chunks,'search',lambda *args:managed)
    calls=[]
    monkeypatch.setattr(vertex_search,'search_vertex_data_store',lambda *a,**k: calls.append(True) or [])
    assert vertex_search.retrieve('question')==managed
    assert calls==[True]


def test_sparse_managed_results_still_search_legacy(monkeypatch):
    called=[]
    monkeypatch.setattr(chunks,'search',lambda *a:[])
    monkeypatch.setattr(vertex_search,'search_vertex_data_store',lambda *a,**k:called.append(True) or [])
    monkeypatch.setattr(vertex_search,'search_gcs_documents_fallback',lambda *a,**k: (_ for _ in ()).throw(AssertionError('fallback must not run')))
    assert vertex_search.retrieve('question')==[] and called==[True]


def test_diversification_considers_both_stores_and_distinct_documents():
    managed=[{'id':'a','chunk_id':'1'},{'id':'a','chunk_id':'2'},{'id':'b'}]
    legacy=[{'id':'c'},{'id':'d'}]
    result=vertex_search.diversify_results(managed,legacy)
    assert [(x['id'],x.get('chunk_id')) for x in result]==[('a','1'),('c',None),('d',None),('b',None),('a','2')]


def test_document_catalogue_never_loads_drafts_or_unauthorized_source_bodies(source,monkeypatch):
    from app.services import documents
    with store.session() as db:
        db.get(store.Document,source['id']).shared=True
        db.commit()
    hidden=documents.create(b'Private original source.', 'hidden.txt', 'text/plain', {'language':'en'})
    statements=[]
    def observe(connection,cursor,statement,parameters,*args):statements.append((statement,parameters))
    event.listen(store.engine(),'before_cursor_execute',observe)
    token=auth.current_user.set(auth.User('reader','reader@example.test'))
    try:
        result=documents.list_documents()
    finally:
        auth.current_user.reset(token)
        event.remove(store.engine(),'before_cursor_execute',observe)
    assert [d['id'] for d in result]==[source['id']]
    assert not any('documents.draft,' in sql or 'documents.draft ' in sql for sql,_ in statements)
    body_queries=[(sql,params) for sql,params in statements if 'documents.blocks' in sql]
    assert len(body_queries)==1 and hidden['id'] not in str(body_queries[0][1])


def test_unknown_legacy_source_does_not_download_or_extract_during_query(monkeypatch):
    from app.services import documents
    from app.core.config import settings
    result=dict(id='unknown',title='New source',link=f'gs://{settings.GCS_BUCKET_NAME}/documents/new.txt',snippets=[{'snippet':'unprepared'}])
    monkeypatch.setattr(chunks,'search',lambda *args:[])
    monkeypatch.setattr(vertex_search,'search_vertex_data_store',lambda *a,**k:[result])
    def forbidden(*args,**kwargs):raise AssertionError('Query must not prepare sources')
    monkeypatch.setattr(store,'get_bytes',forbidden)
    monkeypatch.setattr(documents,'extract',forbidden)
    found=vertex_search.retrieve('policy')
    assert found==[] and found.pending_source_count==1
    import pytest
    with pytest.raises(vertex_search.SourcePreparationPending):
        vertex_search.prepare_rag('What policy is supported?')


def test_legacy_lookup_excludes_private_and_published_source_bodies(monkeypatch):
    from app.services import documents
    from app.core.config import settings
    results=[dict(link=f'gs://{settings.GCS_BUCKET_NAME}/documents/{name}.txt') for name in ['allowed','private','published']]
    with store.session() as db:
        for name,result in zip(['allowed','private','published'],results):
            db.add(store.Document(id=documents.legacy_identifier(result),owner='other',shared=name!='private',
                title=name,language='en',original_key=result['link'],original_hash='a'*64,mime='text/plain',
                published_version=int(name=='published'),blocks=[{'text':name}],draft=[{'content':'not needed'}]))
        db.commit()
    statements=[]
    def observe(conn,cursor,sql,params,*args):statements.append((sql,params))
    event.listen(store.engine(),'before_cursor_execute',observe)
    try:records,pending=documents.legacy_catalog_records(results)
    finally:event.remove(store.engine(),'before_cursor_execute',observe)
    allowed_id=documents.legacy_identifier(results[0])
    assert list(records)==[allowed_id] and pending==0
    bodies=[(sql,params) for sql,params in statements if 'documents.blocks' in sql]
    assert len(bodies)==1 and bodies[0][1]==(allowed_id,)
    assert not any('documents.draft' in sql for sql,_ in statements)


def test_background_legacy_preparation_is_idempotent_and_preserves_reviewed_draft(monkeypatch):
    from app.services import documents,legacy_catalog
    from app.core.config import settings
    from types import SimpleNamespace
    monkeypatch.setattr(store,'get_bytes',lambda *args:b'Public governance source with human review.')
    blob=SimpleNamespace(name='documents/fixed.txt',metadata={'language':'en'})
    assert legacy_catalog.prepare_collection([blob])['prepared']==1
    identifier=documents.legacy_identifier({'link':f'gs://{settings.GCS_BUCKET_NAME}/documents/fixed.txt'})
    with store.session() as db:
        db.get(store.Document,identifier).draft=[{'content':'Reviewed text must survive'}];db.commit()
    monkeypatch.setattr(store,'get_bytes',lambda *args:(_ for _ in ()).throw(AssertionError('Must not redownload')))
    assert legacy_catalog.prepare_collection([blob])['existing']==1
    with store.session() as db:
        assert db.get(store.Document,identifier).draft==[{'content':'Reviewed text must survive'}]


def test_large_background_source_keeps_interactive_upload_limit():
    import pytest
    from fastapi import HTTPException
    from app.services import documents
    data=b'A'*500001
    with pytest.raises(HTTPException) as exc:documents.extract(data,'large.txt')
    assert exc.value.status_code==413
    blocks,_=documents.extract(data,'large.txt',max_text_chars=2000000)
    assert len(blocks[0]['text'])==500001
