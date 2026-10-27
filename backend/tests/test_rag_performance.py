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
