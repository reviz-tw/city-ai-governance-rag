import json
import logging
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from app.services import gemini, rag_timing
from app.pipelines import vertex_search as rag


@pytest.fixture
def evidence(monkeypatch):
    monkeypatch.setattr(rag,'retrieve',lambda *a:[dict(id='policy',title='Policy',
        snippets=[{'snippet':'Human review is required.'}],metadata={})])


def test_brief_and_detailed_preserve_citations_and_use_scoped_model_configuration(monkeypatch,evidence):
    generate=Mock(return_value='No evidence.')
    monkeypatch.setattr(gemini,'generate',generate)
    brief=rag.query_city_governance_rag_vertex('What is the AI policy?',answer_detail='brief')
    assert brief['answer_detail']=='brief' and brief['request_id']
    assert generate.call_args.kwargs==dict(max_output_tokens=3072,thinking_level='LOW')
    assert '180 words' in generate.call_args.args[1] and 'exceptions' in generate.call_args.args[1]
    detailed=rag.query_city_governance_rag_vertex('What is the AI policy?',answer_detail='detailed')
    assert detailed['answer_detail']=='detailed'
    assert generate.call_args.kwargs['max_output_tokens']==12000
    assert generate.call_args.kwargs['thinking_level']=='MEDIUM'
    assert 'detailed explanation' in generate.call_args.args[1]


def test_max_tokens_partial_stream_is_not_reported_as_completed(monkeypatch,evidence):
    from contextlib import contextmanager
    from google.genai import types
    @contextmanager
    def api():
        yield SimpleNamespace(models=SimpleNamespace(generate_content_stream=lambda **kw:iter([
            SimpleNamespace(text='Partial [1]',usage_metadata=None,candidates=[]),
            SimpleNamespace(text='',usage_metadata=None,candidates=[SimpleNamespace(finish_reason=types.FinishReason.MAX_TOKENS)])])))
    monkeypatch.setattr(gemini,'client',api)
    events=[json.loads(e.removeprefix('data: ')) for e in rag.stream_city_governance_rag_vertex('What is the AI policy?',answer_detail='brief')]
    assert events[-2]['type']=='error' and events[-2]['partial']
    assert events[-1]['status']=='failed'


def test_request_trace_correlates_stages_and_handled_failures_without_content(monkeypatch,caplog,evidence):
    caplog.set_level(logging.INFO,logger='app.services.rag_timing')
    monkeypatch.setattr(gemini,'stream',Mock(side_effect=RuntimeError('SECRET provider detail')))
    frames=list(rag.stream_city_governance_rag_vertex('Private query about city policy',answer_detail='brief'))
    events=[json.loads(r.message) for r in caplog.records if r.name=='app.services.rag_timing']
    assert len({e['request_id'] for e in events})==1
    assert events[-1]['event']=='rag_request' and events[-1]['status']=='failed'
    assert {'context_rewrite','language_resolution','retrieval','evidence_prompt'} <= set(events[-1]['stages'])
    assert 'Private query' not in str(events) and 'SECRET' not in str(events)


def test_sdk_connections_are_reused_in_worker_thread(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings,'GEMINI_TIMEOUT_MS',43219)
    fake=Mock()
    constructor=Mock(return_value=fake)
    monkeypatch.setattr(gemini.genai,'Client',constructor)
    with gemini.client() as first:
        assert first is fake
    with gemini.client() as second:
        assert second is fake
    assert constructor.call_count==1
    fake.close.assert_not_called()


def test_http_stream_and_request_header_share_one_trace_across_worker_threads(monkeypatch,caplog):
    import app.main as main
    from fastapi.testclient import TestClient
    from app.services import auth
    monkeypatch.setattr(main,'session_manager',None)
    monkeypatch.setattr(auth.id_token,'verify_oauth2_token',lambda *a:{'sub':'editor','email':'editor@example.test','email_verified':True})
    monkeypatch.setattr(rag,'retrieve',lambda *a:[])
    monkeypatch.setattr(gemini,'stream',lambda *a,**kw:iter(['No evidence.']))
    monkeypatch.setattr(gemini,'generate',lambda *a,**kw:'Full answer with no evidence.')
    caplog.set_level(logging.INFO,logger='app.services.rag_timing')
    with TestClient(main.app) as client:
        headers={'origin':'http://localhost:5173'}
        assert client.post('/api/auth/login',headers=headers,json={'credential':'test-token'}).status_code==200
        sid=client.post('/api/sessions',headers=headers).json()['id']
        response=client.post('/api/chat/stream',headers=headers,json={'query':'What is the AI policy?','session_id':sid})
    assert response.status_code==200
    frames=[json.loads(f.removeprefix('data: ')) for f in response.text.split('\n\n') if f.strip()]
    sources=next(f for f in frames if f['type']=='sources')
    assert sources['request_id']==response.headers['x-request-id']
    assert frames[-1]['status']=='completed'
    events=[json.loads(r.message) for r in caplog.records if r.name=='app.services.rag_timing']
    assert len({e['request_id'] for e in events})==1
    assert {'authentication','conversation_begin','conversation_finish'} <= set(events[-1]['stages'])
