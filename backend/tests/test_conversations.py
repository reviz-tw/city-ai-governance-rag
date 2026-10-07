import json
import pytest
from fastapi import HTTPException
from app.services import conversations as c, auth, store
from app.pipelines.vertex_search import event

@pytest.fixture(autouse=True)
def summary_model(monkeypatch):
    monkeypatch.setattr(c.gemini,'generate',lambda payload,*args:json.dumps({'text':'摘要：'+json.loads(payload)['turns'][0]['question']}))


def complete(sid,question='保留來源與研究限制'):
    tid,context=c.begin(sid,question)
    frames=iter([event({'type':'sources','sources':[{'document_id':'source','version':2}],'response_language':'zh-TW','context_city':'台北'}),
                 event({'type':'chunk','text':'有引用的回答 [1]'}),event({'type':'done','status':'completed'})])
    list(c.stream(sid,tid,frames))
    return tid,context


def test_roundtrip_restore_and_private_ownership():
    sid=c.create_session()['id']
    tid,_=complete(sid)
    saved=c.read_session(sid)
    assert saved['messages'][0]['content']=='保留來源與研究限制'
    assert saved['messages'][1]['content']=='有引用的回答 [1]'
    assert saved['messages'][1]['citations'][0]['version']==2
    token=auth.current_user.set(auth.User('admin','admin@example.test'))
    try:
        assert c.list_sessions()==[]
        for action in (lambda:c.read_session(sid),lambda:c.begin(sid,'偷看'),lambda:c.delete_session(sid),lambda:c.rename_session(sid,c.Rename(title='偷改'))):
            with pytest.raises(HTTPException) as e:action()
            assert e.value.status_code==404
    finally:auth.current_user.reset(token)


def test_summary_provenance_and_resume_context():
    sid=c.create_session()['id']
    ids=[complete(sid,f'問題{i}')[0] for i in range(5)]
    saved=c.read_session(sid)
    assert len(saved['summaries'])==2
    assert saved['summaries'][0]['through_sequence']==1
    assert saved['summaries'][1]['source_turn_ids']==ids[:2]
    assert saved['summaries'][1]['method'].startswith('model-v1:')
    tid,context=c.begin(sid,'續問')
    assert context.persisted and context.summary==saved['summaries'][-1]['text']
    assert len(context.history)==6
    assert context.history[0].id==ids[2]+'-user'
    assert context.city=='台北'
    c.finish(sid,tid,'',[],None,None,'failed')


def test_interruption_and_overlap():
    sid=c.create_session()['id']
    tid,_=c.begin(sid,'提問')
    with pytest.raises(HTTPException) as e:c.begin(sid,'同時提問')
    assert e.value.status_code==409
    with pytest.raises(HTTPException):c.delete_session(sid)
    gen=c.stream(sid,tid,iter([event({'type':'chunk','text':'部分回答'}),event({'type':'done','status':'completed'})]))
    next(gen);gen.close()
    saved=c.read_session(sid)
    assert saved['messages'][1]['content']=='部分回答'
    assert saved['messages'][1]['status']=='interrupted'
    tid,context=c.begin(sid,'重問')
    assert context.history==[]
    c.finish(sid,tid,'',[],None,None,'failed')


def test_summary_failure_fallback_keeps_history(monkeypatch):
    monkeypatch.setattr(c.gemini,'generate',lambda *args: (_ for _ in ()).throw(ValueError('failed')))
    sid=c.create_session()['id']
    ids=[complete(sid,f'需求{i}')[0] for i in range(5)]
    saved=c.read_session(sid)
    assert saved['summaries'][-1]['method']=='extractive-v1'
    assert '需求0' in saved['summaries'][-1]['text'] and '需求1' in saved['summaries'][-1]['text']
    assert saved['summaries'][-1]['source_turn_ids']==ids[:2]
    assert len(saved['messages'])==10
    c.rename_session(sid,c.Rename(title='研究'))
    assert c.list_sessions()[0]['title']=='研究'
    c.delete_session(sid)
    assert c.list_sessions()==[]
    with store.session() as db:
        from sqlalchemy import select
        assert db.scalar(select(store.ChatTurn)) is None
        assert db.scalar(select(store.ChatSummary)) is None


def test_stream_api_uses_server_context(monkeypatch):
    import app.main as main
    from app.api import routes
    from fastapi.testclient import TestClient
    monkeypatch.setattr(main,'session_manager',None)
    monkeypatch.setattr(auth.id_token,'verify_oauth2_token',lambda *args:{'sub':'editor','email':'editor@example.test','email_verified':True})
    seen=[]
    def upstream(**kwargs):
        seen.append(kwargs['research_context'])
        yield event({'type':'sources','sources':[],'response_language':'zh-TW','context_city':None})
        yield event({'type':'chunk','text':'持久回答'})
        yield event({'type':'done','status':'completed'})
    monkeypatch.setattr(routes,'stream_city_governance_rag_vertex',upstream)
    headers={'origin':'http://localhost:5173'}
    with TestClient(main.app) as client:
        client.post('/api/auth/login',json={'credential':'synthetic'},headers=headers)
        sid=client.post('/api/sessions',headers=headers).json()['id']
        for i in range(2):
            response=client.post('/api/chat/stream',json={'session_id':sid,'query':f'問題{i}','research_context':{'summary':'偽造摘要'}},headers=headers)
            assert response.status_code==200 and 'completed' in response.text
        assert seen[0].summary=='' and seen[1].history[0].content=='問題0'
        assert len(client.get('/api/sessions/'+sid).json()['messages'])==4


def test_expired_lease_recovery_and_stale_writer():
    sid=c.create_session()['id']
    old,_=c.begin(sid,'意外中斷')
    with store.session() as db:
        db.get(store.ChatSession,sid).busy_until=0
        db.commit()
    new,_=c.begin(sid,'新的追問')
    c.finish(sid,old,'過期回答',[],None,None,'completed')
    with store.session() as db:
        assert db.get(store.ChatTurn,old).status=='interrupted'
        assert db.get(store.ChatSession,sid).busy_until>0
    c.finish(sid,new,'新的回答',[],None,None,'completed')
    store.engine().dispose();store.engine.cache_clear();store.initialize()
    saved=c.read_session(sid)
    assert saved['messages'][-1]['content']=='新的回答'
    assert saved['messages'][1]['status']=='interrupted'


def test_persisted_summary_is_not_silently_rewritten(monkeypatch):
    from app.services import context
    monkeypatch.setattr(context.gemini,'generate',lambda *args:json.dumps({
        'retrieval_query':'獨立查詢','summary':'未追溯的新摘要','city':None}))
    supplied=context.ResearchContext(persisted=True,summary='已追溯的摘要',history=[
        context.HistoryMessage(id=str(i),role='user',content='近期提問') for i in range(6)])
    value=context.prepare('續問',supplied)
    assert value['summary']=='已追溯的摘要'
    assert len(value['history'])==6
    assert value['retrieval_query']=='獨立查詢'
