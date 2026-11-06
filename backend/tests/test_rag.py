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
    result=rag.query_city_governance_rag_vertex('如何管理城市人工智慧的政策風險？',interface_language='en',answer_detail='brief')
    assert retrieved.call_args.args[2] is None
    assert result['response_language']=='zh-TW'
    assert result['sources'][0]['language']=='en'
    assert 'Evidence in English.' in generate.call_args.args[0]


def test_inferred_city_is_a_search_term_not_a_document_filter(retrieved,monkeypatch):
    monkeypatch.setattr(rag, 'prepare', lambda *args: dict(
        retrieval_query='AI participation',city='Bogotá',preferred_language=None,
        recent_languages=[],history=[],summary=''))
    rag.prepare_rag('Any cases about Bogotá?')
    assert 'Bogotá' in retrieved.call_args.args[0]
    assert retrieved.call_args.args[1] is None
    rag.prepare_rag('AI participation',city_filter='Taipei')
    assert retrieved.call_args.args[1] == 'Taipei'


@pytest.mark.parametrize('city,languages,expected',[
    (None,None,['bogota','taipei']),('Bogotá',None,['bogota']),
    (None,['en'],['bogota']),('Bogotá',['ja'],[]),
])
def test_legacy_scope_uses_catalogue_without_unsupported_remote_filters(monkeypatch,city,languages,expected):
    from app.services import chunks,documents
    monkeypatch.setattr(chunks,'search',lambda *args:[])
    results=[dict(id=name,title=name,snippets=[],metadata={}) for name in ['bogota','taipei']]
    remote=Mock(return_value=results)
    monkeypatch.setattr(rag,'search_vertex_data_store',remote)
    monkeypatch.setattr(documents,'legacy_identifier',lambda result:result['id'])
    docs={'bogota':SimpleNamespace(title='Bogotá',published_version=0,metadata_json={'city':'Bogotá'},language='en',original_hash='a',blocks=[]),
          'taipei':SimpleNamespace(title='Taipei',published_version=0,metadata_json={'city':'Taipei'},language='zh-TW',original_hash='b',blocks=[])}
    monkeypatch.setattr(documents,'legacy_catalog_records',lambda results:(docs,0))
    assert [r['id'] for r in rag.retrieve('AI governance',city,languages)]==expected
    assert not remote.call_args.kwargs.get('filter_expr')


def test_fallback_respects_scope(monkeypatch):
    blobs=[SimpleNamespace(name='documents/private.txt',metadata={'city':'London','language':'ja'},download_as_bytes=Mock(return_value=b'wrong')),
           SimpleNamespace(name='documents/allowed.txt',metadata={'city':'Taipei','language':'en'},download_as_bytes=Mock(return_value=b'allowed policy text'))]
    client=Mock();client.bucket.return_value.list_blobs.return_value=blobs
    monkeypatch.setattr(rag.storage,'Client',Mock(return_value=client))
    result=rag.search_gcs_documents_fallback('policy',city_filter='Taipei',source_language_filters=['en'])
    assert [r['id'] for r in result]==['allowed.txt']
    blobs[0].download_as_bytes.assert_not_called()


def test_stream_failure_does_not_retry_or_report_success(retrieved,monkeypatch):
    def failing(*args,**kwargs):
        yield 'Partial '
        raise RuntimeError('private provider details')
    mocked=Mock(side_effect=failing)
    monkeypatch.setattr(gemini,'stream',mocked)
    events=[json.loads(e.removeprefix('data: ')) for e in rag.stream_city_governance_rag_vertex('What is the governance policy?',answer_detail='brief')]
    assert [e['type'] for e in events]==['status','sources','status','chunk','error','done']
    assert events[-1]['status']=='failed' and events[-2]['partial']
    assert mocked.call_count==1
    assert 'private provider' not in str(events)


@pytest.mark.parametrize('detail',['brief','detailed','progressive'])
@pytest.mark.parametrize('language',list(rag.NO_RESULTS_MESSAGES))
def test_empty_results_return_localized_message_without_generation(monkeypatch,detail,language):
    from app.services import chunks
    monkeypatch.setattr(chunks,'search',lambda *a:[])
    monkeypatch.setattr(rag,'search_vertex_data_store',lambda *a,**kw:[])
    generate=Mock(side_effect=AssertionError('No answer generation without evidence'))
    stream=Mock(side_effect=AssertionError('No answer generation without evidence'))
    monkeypatch.setattr(gemini,'generate',generate)
    monkeypatch.setattr(gemini,'stream',stream)
    kwargs=dict(response_language=language,answer_detail=detail)
    result=rag.query_city_governance_rag_vertex('What policy is supported?',**kwargs)
    assert result['sources']==[]
    assert result['answer']==rag.NO_RESULTS_MESSAGES[language]
    assert result['status']=='completed' and 'error' not in result
    assert result['search_results_count']==0 and result['model_used']==''
    events=[json.loads(e.removeprefix('data: ')) for e in rag.stream_city_governance_rag_vertex('What policy is supported?',**kwargs)]
    assert [e['type'] for e in events]==['status','sources','chunk','done']
    assert events[2]['text']==result['answer']
    assert events[-1]['status']=='completed'
    generate.assert_not_called()
    stream.assert_not_called()


@pytest.mark.parametrize('pending',[0,1])
def test_results_without_usable_passages_distinguish_pending_sources(monkeypatch,pending):
    monkeypatch.setattr(gemini,'generate',Mock(side_effect=AssertionError('Must not generate')))
    monkeypatch.setattr(gemini,'stream',Mock(side_effect=AssertionError('Must not generate')))
    monkeypatch.setattr(rag,'retrieve',lambda *a:rag.RetrievalResults([
        {'id':'empty','title':'Empty passage','snippets':[{'snippet':'<b> </b>'}]}],pending))
    events=[json.loads(e.removeprefix('data: ')) for e in rag.stream_city_governance_rag_vertex(
        'What policy is supported?',response_language='zh-TW')]
    if pending:
        assert events[-1]['status']=='failed'
        assert events[-2]['message']==rag.PREPARATION_ERRORS['zh-TW']
    else:
        assert events[-1]['status']=='completed'
        assert events[-2]['text']==rag.NO_RESULTS_MESSAGES['zh-TW']


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


def test_standalone_question_skips_rewrite_but_followup_does_not(monkeypatch):
    call=Mock(return_value=json.dumps({'retrieval_query':'Taipei AI policy','summary':'','city':'Taipei'}))
    monkeypatch.setattr(gemini,'generate',call)
    context=ResearchContext(history=[HistoryMessage(id='u',role='user',content='Previous topic')],persisted=True)
    question='What are the requirements for artificial intelligence transparency?'
    assert prepare(question,context)['retrieval_query']==question
    call.assert_not_called()
    prepare('What are the AI requirements for that city?',context)
    call.assert_called_once()


@pytest.mark.parametrize('failed_store',['managed','legacy'])
def test_search_failure_is_not_reported_as_empty_results(monkeypatch,failed_store):
    from app.services import chunks
    failure=Mock(side_effect=RuntimeError('private'))
    monkeypatch.setattr(chunks,'search',failure if failed_store=='managed' else Mock(return_value=[]))
    monkeypatch.setattr(rag,'search_vertex_data_store',failure if failed_store=='legacy' else Mock(return_value=[]))
    events=[json.loads(e.removeprefix('data: ')) for e in rag.stream_city_governance_rag_vertex('What is the AI policy?')]
    assert [e['type'] for e in events]==['status','error','done']
    assert 'search service' in events[1]['message'].lower()
    assert events[-1]['status']=='failed' and 'private' not in str(events)


def test_managed_citations_keep_original_passage_ids(retrieved):
    retrieved.return_value[0]['refs']=[{'block_id':'p4','page':3},{'block_id':'p4','page':3},{'block_id':'p5','page':4}]
    retrieved.return_value[0]['chunk_id']='chunk-a'
    _,_,sources,_=rag.prepare_rag('What is the policy?')
    assert sources[0]['block_ids']==['p4','p5']


def test_expanded_evidence_includes_more_documents_within_byte_budgets(monkeypatch):
    monkeypatch.setattr(rag,'retrieve',lambda *a:[dict(id=str(i),title=f'Policy {i}',
        snippets=[{'snippet':f'{i}: '+('治理證據'*1000)}],metadata={}) for i in range(12)])
    system,contents,sources,_=rag.prepare_rag('What is the AI governance policy?')
    assert len(sources)==7  # Previously only three long passages fit in 9,000 bytes.
    assert sum(len(s['snippet'].encode('utf-8')) for s in sources)<=24000
    assert all(len(s['snippet'].encode('utf-8'))<=3500 for s in sources)
    assert len((system+contents).encode('utf-8'))<=36000
    assert [s['citation_id'] for s in sources]==list(range(1,len(sources)+1))


def test_search_markup_is_removed_from_citations_and_model_evidence(retrieved):
    retrieved.return_value[0]['snippets']=[{'snippet':'Review <b>AI</b> use &amp; human oversight.'}]
    _,content,sources,_=rag.prepare_rag('What is the policy?')
    assert sources[0]['snippet']=='Review AI use & human oversight.'
    assert '<b>' not in content and '&amp;' not in content


def test_empty_passages_return_no_results(monkeypatch):
    monkeypatch.setattr(rag, "retrieve", lambda *a: [{"id":"empty", "title":"Empty", "snippets":[{"snippet":"<b> </b>"}]}])
    monkeypatch.setattr(gemini, "stream", Mock(side_effect=AssertionError("Must not generate")))
    events=[json.loads(e.removeprefix("data: ")) for e in rag.stream_city_governance_rag_vertex("What is the AI policy?", response_language="en")]
    assert events[-1]["status"]=="completed"
    assert events[-2]["text"]==rag.NO_RESULTS_MESSAGES["en"]


def test_persisted_followup_uses_retrieval_only_schema_without_dropping_context(monkeypatch):
    from app.services.context import RetrievalPlan,ContextPlan
    generate=Mock(return_value=json.dumps({'retrieval_query':'新北市人工智慧風險管理規範','city':'新北'}))
    monkeypatch.setattr(gemini,'generate',generate)
    context=ResearchContext(persisted=True,city='台北',summary='已追溯摘要',history=[
        HistoryMessage(id='u',role='user',content='台北市人工智慧風險管理規範')])
    result=prepare('那新北呢？',context)
    assert result['city']=='新北' and '新北' in result['retrieval_query']
    assert result['summary']=='已追溯摘要' and result['history'][0]['id']=='u'
    assert generate.call_args.args[2] is RetrievalPlan
    assert 'summary' not in RetrievalPlan.model_json_schema()['properties']
    assert generate.call_args.kwargs['max_output_tokens']==512
    assert generate.call_args.kwargs['cleaner'] is True
    generate.return_value=json.dumps({'retrieval_query':'New Taipei policy','city':'新北','summary':'explicit external summary'})
    external=prepare('那新北呢？',ResearchContext(history=context.history))
    assert generate.call_args.args[2] is ContextPlan
    assert generate.call_args.kwargs['max_output_tokens']==1024
    assert external['summary']=='explicit external summary'
