import json
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from app.pipelines import vertex_search as rag, cleaner
from app.services import gemini
from app.services.context import ResearchContext, HistoryMessage, prepare
from app.core.config import settings

@pytest.fixture
def retrieved(monkeypatch):
    result=[{'id':'a','title':'English policy','link':'source','snippets':[{'snippet':'Evidence in English.'}], 'metadata':{'language':'en','document_id':'a'}}]
    call=Mock(return_value=result)
    monkeypatch.setattr(rag,'retrieve',call)
    return call


def test_chinese_answer_does_not_filter_english_sources(retrieved,monkeypatch):
    generate=Mock(return_value='有依據的回答 [1]')
    monkeypatch.setattr(gemini,'generate',generate)
    result=rag.query_city_governance_rag_vertex('如何管理城市人工智慧的政策風險？',interface_language='en')
    assert retrieved.call_args.args[2] is None
    assert result['response_language']=='zh-TW'
    assert result['sources'][0]['language']=='en'
    assert 'Evidence in English.' in generate.call_args.args[0]


def test_filters_escape_city_and_expand_legacy_language():
    assert rag.build_filter(languages=['en'])=='language: ANY("en")'
    assert '"zh"' in rag.build_filter(languages=['zh-TW'])
    assert '\\"' in rag.build_filter(city='a" OR b')


def test_fallback_respects_scope(monkeypatch):
    blobs=[SimpleNamespace(name='documents/private.txt',metadata={'city':'London','language':'ja'},download_as_bytes=Mock(return_value=b'wrong')),
           SimpleNamespace(name='documents/allowed.txt',metadata={'city':'Taipei','language':'en'},download_as_bytes=Mock(return_value=b'allowed policy text'))]
    client=Mock();client.bucket.return_value.list_blobs.return_value=blobs
    monkeypatch.setattr(rag.storage,'Client',Mock(return_value=client))
    result=rag.search_gcs_documents_fallback('policy',city_filter='Taipei',source_language_filters=['en'])
    assert [r['id'] for r in result]==['allowed.txt']
    blobs[0].download_as_bytes.assert_not_called()


def test_stream_failure_does_not_retry_or_report_success(retrieved,monkeypatch):
    def failing(*args):
        yield 'Partial '
        raise RuntimeError('private provider details')
    mocked=Mock(side_effect=failing)
    monkeypatch.setattr(gemini,'stream',mocked)
    events=[json.loads(e.removeprefix('data: ')) for e in rag.stream_city_governance_rag_vertex('What is the governance policy?')]
    assert [e['type'] for e in events]==['sources','chunk','error','done']
    assert events[-1]['status']=='failed' and events[-2]['partial']
    assert mocked.call_count==1
    assert 'private provider' not in str(events)


def test_no_evidence_prompt_forbids_invented_facts(monkeypatch):
    monkeypatch.setattr(rag,'retrieve',lambda *a:[])
    generate=Mock(return_value='No evidence available.')
    monkeypatch.setattr(gemini,'generate',generate)
    result=rag.query_city_governance_rag_vertex('What policy is supported?')
    assert result['sources']==[]
    assert 'never invent' in generate.call_args.args[1]
    assert '22' not in result['answer']


def test_cleaner_uses_shared_sdk_and_validated_json(monkeypatch):
    data={'cleaned_text':'text','suggested_metadata':{'title':'Policy','city':'Taipei','country':'Taiwan','policy_domain':'Governance','language':'en'},'summary':'Summary','key_takeaways':['A']}
    call=Mock(return_value=json.dumps(data));monkeypatch.setattr(gemini,'generate',call)
    result=cleaner.clean_and_annotate_document('text')
    assert result.suggested_metadata.language=='en'
    assert call.call_args.kwargs['cleaner'] is True


def test_context_rewrite_and_bounded_history(monkeypatch):
    call=Mock(return_value=json.dumps({'retrieval_query':'新北市的人工智慧風險管理指引','summary':'研究城市政策，保留來源 a','city':'新北'}))
    monkeypatch.setattr(gemini,'generate',call)
    context=ResearchContext(history=[HistoryMessage(id='u1',role='user',content='比較城市人工智慧風險管理指引'*500),HistoryMessage(id='a1',role='assistant',content='draft',response_language='zh-TW')],city='台北')
    result=prepare('那新北市呢？',context)
    assert result['city']=='新北'
    assert '風險管理' in result['retrieval_query']
    assert len(call.call_args.args[0].encode()) < 10000
    assert prepare('New question',None)['history']==[]
