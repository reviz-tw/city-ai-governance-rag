import json
import threading
from concurrent.futures import Future
from queue import Empty
from unittest.mock import Mock
import pytest
from app.pipelines import vertex_search as rag
from app.services import conversations, gemini, progressive_answers, rag_timing
from app.models.schema import RAGQueryRequest


def payload(frame):
    return json.loads(frame.removeprefix('data: '))


@pytest.fixture
def evidence(monkeypatch):
    retrieve = Mock(return_value=[dict(id='policy',title='Synthetic policy',link='source',
        snippets=[{'snippet':'AI recommendations require human approval. Budget is not stated.'}],
        metadata={'language':'en','document_id':'policy','version':1})])
    monkeypatch.setattr(rag,'retrieve',retrieve)
    return retrieve


def test_default_stream_delivers_preview_before_full_completion_and_retrieves_once(evidence,monkeypatch):
    started=threading.Event(); release=threading.Event(); calls=[]
    def full(contents,system,**config):
        calls.append(('full',contents,system,config));started.set()
        yield 'Human approval is mandatory [1]. '
        assert release.wait(5)
        yield 'Budget is not specified [1].'
    def brief(contents,system,**config):
        assert started.wait(5)
        calls.append(('brief',contents,system,config))
        yield 'Human approval is required [1].'
    monkeypatch.setattr(gemini,'generate',Mock(side_effect=AssertionError('Full answer must stream')))
    monkeypatch.setattr(gemini,'stream',lambda *a,**k:brief(*a,**k) if k.get('thinking_level')=='LOW' else full(*a,**k))
    stream=rag.stream_city_governance_rag_vertex('What is the AI governance rule?')
    try:
        assert payload(next(stream))['type']=='status'
        source=payload(next(stream))
        assert source['answer_detail']=='progressive'
        assert payload(next(stream))['stage']=='generating'
        opening=payload(next(stream))
        assert opening['phase']=='brief' and 'Quick take' in opening['text']
        assert not release.is_set()
        assert payload(next(stream))['stage']=='expanding'
        first=payload(next(stream))
        assert first['phase']=='detailed' and 'Human approval' in first['text']
        assert not release.is_set()  # Full text reaches the caller before generation completes.
        release.set()
        rest=[payload(f) for f in stream]
    finally:
        release.set();stream.close()
    assert [e['type'] for e in rest]==['chunk','done']
    assert rest[0]['phase']=='detailed' and 'Budget' in rest[0]['text']
    assert 'Full answer' in first['text'] and 'Full answer' not in rest[0]['text']
    assert rest[-1]['status']=='completed'
    assert evidence.call_count==1 and calls[0][1]==calls[1][1]
    assert calls[0][3]==dict(max_output_tokens=12000,thinking_level='MEDIUM')
    assert calls[1][3]['thinking_level']=='LOW'
    assert calls[1][3]['timeout_ms']==8000
    assert '180 words' not in calls[0][2] and 'Human approval is required' not in calls[0][1]
    assert RAGQueryRequest(query='question').answer_detail=='progressive'


def test_full_failure_keeps_preview_and_sources_but_never_claims_completion(evidence,monkeypatch):
    def stream(*a,**k):
        if k.get('thinking_level')=='LOW':
            yield 'Quick evidence [1].'
        else:
            yield 'Partial full answer [1].'
            raise RuntimeError('SECRET provider detail')
    monkeypatch.setattr(gemini,'stream',stream)
    events=[payload(f) for f in rag.stream_city_governance_rag_vertex('What is the AI policy?')]
    assert events[-1]==dict(type='done',status='failed')
    assert events[-2]['type']=='error' and events[-2]['partial']
    assert 'Quick evidence' in ''.join(e.get('text','') for e in events)
    assert 'Partial full answer' in ''.join(e.get('text','') for e in events)
    assert next(e for e in events if e['type']=='sources')['sources'][0]['document_id']=='policy'
    assert 'SECRET' not in str(events)


@pytest.mark.parametrize('partial',[False,True])
def test_preview_failure_still_delivers_normal_full_answer(evidence,monkeypatch,partial):
    def broken(*a,**k):
        if partial:yield 'Partial preview '
        raise TimeoutError('SECRET timeout')
    monkeypatch.setattr(gemini,'stream',lambda *a,**k:broken() if k.get('thinking_level')=='LOW'
        else iter(['The full independently reasoned answer [1].']))
    events=[payload(f) for f in rag.stream_city_governance_rag_vertex('What is the AI policy?')]
    text=''.join(e.get('text','') for e in events)
    assert 'quick take could not be completed' in text
    assert 'Full answer' in text and 'independently reasoned' in text
    assert events[-1]['status']=='completed' and not any(e['type']=='error' for e in events)
    assert 'SECRET' not in text


def test_combined_answer_restores_as_one_turn_with_the_same_citations(evidence,monkeypatch):
    monkeypatch.setattr(gemini,'stream',lambda *a,**k:iter(['Summary [1].']) if k.get('thinking_level')=='LOW'
        else iter(['Normal detailed answer, ', 'preserving the missing budget [1].']))
    sid=conversations.create_session()['id']
    tid,context=conversations.begin(sid,'What is the AI policy?')
    frames=list(conversations.stream(sid,tid,rag.stream_city_governance_rag_vertex(
        'What is the AI policy?',research_context=context)))
    answer=conversations.read_session(sid)['messages']
    assert len(answer)==2 and answer[0]['role']=='user'
    assert answer[1]['status']=='completed'
    assert answer[1]['content']==''.join(payload(f).get('text','') for f in frames)
    assert answer[1]['content'].index('Quick take')<answer[1]['content'].index('Full answer')
    assert answer[1]['citations'][0]['citation_id']==1


def test_disconnect_keeps_partial_preview_and_cancels_queued_full_generation(evidence,monkeypatch):
    future=Future()
    full=progressive_answers.FullAnswerStream();full.future=future
    monkeypatch.setattr(progressive_answers,'_submit',lambda *a:full)
    monkeypatch.setattr(gemini,'stream',lambda *a,**k:iter(['Preview [1].']))
    sid=conversations.create_session()['id'];tid,context=conversations.begin(sid,'What is the AI policy?')
    stream=conversations.stream(sid,tid,rag.stream_city_governance_rag_vertex('What is the AI policy?',research_context=context))
    while payload(next(stream))['type']!='chunk':pass
    stream.close()
    saved=conversations.read_session(sid)['messages'][1]
    assert future.cancelled() and saved['status']=='interrupted'
    assert 'Preview' in saved['content'] and 'Full answer' not in saved['content']


def test_full_ready_first_is_still_appended_once_after_preview(evidence,monkeypatch):
    ready=threading.Event()
    def full(*a,**k):yield 'Complete answer [1].';ready.set()
    def preview(*a,**k):assert ready.wait(5);yield 'Quick answer [1].'
    monkeypatch.setattr(gemini,'stream',lambda *a,**k:preview() if k.get('thinking_level')=='LOW' else full())
    result=rag.query_city_governance_rag_vertex('What is the AI policy?')
    assert result['status']=='completed' and result['answer_detail']=='progressive'
    assert result['answer'].count('Complete answer')==1
    assert result['answer'].index('Quick answer')<result['answer'].index('Complete answer')


def test_full_capacity_is_bounded_and_released_after_worker_finishes(monkeypatch):
    started=threading.Event();release=threading.Event()
    monkeypatch.setattr(progressive_answers,'_full_slots',threading.BoundedSemaphore(1))
    def full(*a,**k):started.set();assert release.wait(5);yield 'Full answer'
    monkeypatch.setattr(gemini,'stream',full)
    first=progressive_answers._submit('evidence','system',{})
    try:
        assert started.wait(5)
        assert progressive_answers._submit('evidence','system',{}) is None
    finally:release.set()
    first.future.result(timeout=5)
    assert first.fragments.get_nowait()=='Full answer'
    # done callbacks release the admission slot before a later request starts.
    assert progressive_answers._full_slots.acquire(timeout=5)
    progressive_answers._full_slots.release()


def test_keepalive_while_waiting_is_accepted_by_durable_conversation(evidence,monkeypatch):
    full=progressive_answers.FullAnswerStream();full.future=Future()
    class Waiting:
        calls=0
        def get_nowait(self):raise Empty()
        def get(self,timeout):
            self.calls+=1
            if self.calls==1:raise Empty()
            if self.calls==2:return 'Normal full answer [1].'
            full.future.set_result(None)
            return None
    full.fragments=Waiting()
    monkeypatch.setattr(progressive_answers,'_submit',lambda *a:full)
    monkeypatch.setattr(gemini,'stream',lambda *a,**k:iter(['Preview [1].']))
    sid=conversations.create_session()['id'];tid,context=conversations.begin(sid,'What is the AI policy?')
    frames=list(conversations.stream(sid,tid,rag.stream_city_governance_rag_vertex('What is the AI policy?',research_context=context)))
    assert any(payload(f)['type']=='heartbeat' for f in frames)
    assert conversations.read_session(sid)['messages'][1]['status']=='completed'


def test_cancellation_unblocks_full_buffer_and_closes_provider_stream(monkeypatch):
    filled=threading.Event();closed=threading.Event()
    def fragments(*a,**k):
        try:
            for i in range(1000):
                if i==64:filled.set()
                yield str(i)
        finally:closed.set()
    monkeypatch.setattr(gemini,'stream',fragments)
    full=progressive_answers._submit('evidence','system',{})
    try:
        assert filled.wait(5)
        assert full.fragments.qsize()==64
    finally:full.cancel()
    full.future.result(timeout=5)
    assert closed.is_set()


def test_disconnect_during_full_stream_persists_partial_answer(evidence,monkeypatch):
    release=threading.Event();closed=threading.Event()
    def fragments(*a,**k):
        if k.get('thinking_level')=='LOW':
            yield 'Preview [1].'
            return
        try:
            yield 'First detailed finding [1].'
            assert release.wait(5)
            yield 'Later finding.'
        finally:closed.set()
    monkeypatch.setattr(gemini,'stream',fragments)
    sid=conversations.create_session()['id'];tid,context=conversations.begin(sid,'What is the AI policy?')
    stream=conversations.stream(sid,tid,rag.stream_city_governance_rag_vertex('What is the AI policy?',research_context=context))
    try:
        while payload(next(stream)).get('phase')!='detailed':pass
        stream.close()
        saved=conversations.read_session(sid)['messages'][1]
        assert saved['status']=='interrupted'
        assert 'First detailed finding' in saved['content'] and 'Later finding' not in saved['content']
    finally:
        release.set();stream.close()
    assert closed.wait(5)


@pytest.mark.parametrize('failure',[RuntimeError('provider failure'),gemini.OutputTruncated('limit')])
def test_full_stream_error_is_persisted_with_received_text(evidence,monkeypatch,failure):
    def fragments(*a,**k):
        if k.get('thinking_level')=='LOW':
            yield 'Preview [1].'
        else:
            yield 'Partial detail [1].'
            raise failure
    monkeypatch.setattr(gemini,'stream',fragments)
    sid=conversations.create_session()['id'];tid,context=conversations.begin(sid,'What is the AI policy?')
    frames=list(conversations.stream(sid,tid,rag.stream_city_governance_rag_vertex('What is the AI policy?',research_context=context)))
    saved=conversations.read_session(sid)['messages'][1]
    assert saved['status']=='failed' and 'Partial detail' in saved['content']
    assert payload(frames[-1])['status']=='failed'
