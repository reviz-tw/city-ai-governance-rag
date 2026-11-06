import time
from unittest.mock import Mock
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.core.config import settings
from app.services import documents, store, translations as tr
from app.services.auth import User, current_user
from app.services.local_translation import split_to_budget, LocalTranslator
from app.translation_worker import process_one, ModelUnavailable


def publish(source, version=1, contents=None):
    with store.session() as db:
        doc=db.get(store.Document,source['id'])
        chunks=[dict(c) for c in doc.draft]
        if contents is not None:
            chunks[0]={**chunks[0], 'content':contents}
        pub=store.Publication(id=f'{doc.id}:{version}',document_id=doc.id,version=version,
            previous_version=doc.published_version,chunks=chunks,operator='editor@example.test',status='published')
        doc.published_version=version
        db.add(pub);db.commit()
        return pub


def test_backfill_six_languages_is_idempotent_and_same_language_is_original(source):
    pub=publish(source)
    first=tr.backfill()
    assert first=={'documents':1,'created':len(pub.chunks)*6}
    assert tr.backfill()['created']==0
    with store.session() as db:
        rows=list(db.scalars(select(store.ChunkTranslation)))
    assert len(rows)==len(pub.chunks)*6
    assert all(r.status=='completed' for r in rows if r.language=='en')
    assert all(r.status=='queued' for r in rows if r.language!='en')
    result=tr.read(source['id'],'en')
    assert result['complete'] and result['chunks'][0]['text']==pub.chunks[0]['content']
    assert tr.statistics()['completed']==len(pub.chunks)


def test_backfill_skips_unpublished_and_only_queues_current_version(source):
    assert tr.backfill()['created']==0
    publish(source,1)
    pub=publish(source,2)
    tr.backfill()
    with store.session() as db:
        rows=list(db.scalars(select(store.ChunkTranslation)))
    assert len(rows)==len(pub.chunks)*6 and {r.version for r in rows}=={2}


def test_access_is_document_scoped_shared_cache_does_not_grant_access(source):
    publish(source);tr.backfill()
    token=current_user.set(User('other','other@example.test'))
    try:
        with pytest.raises(HTTPException) as exc:tr.read(source['id'],'ja',enqueue=True)
        assert exc.value.status_code==404
        with store.session() as db:
            db.get(store.Document,source['id']).shared=True;db.commit()
        assert tr.read(source['id'],'en')['complete']
        with store.session() as db:
            db.get(store.Document,source['id']).shared=False;db.commit()
        with pytest.raises(HTTPException):tr.read(source['id'],'en')
    finally:
        current_user.reset(token)


def test_immutable_chunk_text_is_used_not_original_block_or_later_draft(source):
    pub=publish(source,contents='Reviewed policy text with 20 cases.')
    with store.session() as db:
        db.get(store.Document,source['id']).draft=[{'id':'new-draft','content':'not published'}];db.commit()
    result=tr.read(source['id'],'en',chunk_ids=[pub.chunks[0]['id']],version=1,enqueue=True)
    assert result['chunks'][0]['original']=='Reviewed policy text with 20 cases.'
    assert result['chunks'][0]['text']==result['chunks'][0]['original']
    with pytest.raises(HTTPException) as exc:tr.read(source['id'],'en',version=2)
    assert exc.value.status_code==409
    with pytest.raises(HTTPException):tr.read(source['id'],'en',chunk_ids=['new-draft'])
    with pytest.raises(HTTPException):tr.read(source['id'],'en',original_hash='changed')


def test_legacy_block_citations_map_to_published_chunks(source):
    pub=publish(source)
    result=tr.read(source['id'],'ja',block_ids=['p2'],enqueue=True)
    expected=[c['id'] for c in pub.chunks if any(r['block_id']=='p2' for r in c['refs'])]
    assert [c['chunk_id'] for c in result['chunks']]==expected
    assert len(result['chunks'])<len(pub.chunks) or len(pub.chunks)==1


def test_republication_reuses_unchanged_translation_and_model_change_invalidates(source,monkeypatch):
    pub=publish(source);tr.read(source['id'],'ja',enqueue=True)
    row,chunk=tr.claim()
    assert tr.finish(row,text='保存済みの訳文')
    pub2=publish(source,2)
    tr.read(source['id'],'ja',enqueue=True)
    result=tr.read(source['id'],'ja')
    assert next(c for c in result['chunks'] if c['chunk_id']==row.chunk_id)['text']=='保存済みの訳文'
    publish(source,3,contents='Changed policy content.')
    result=tr.read(source['id'],'ja',enqueue=True)
    assert result['chunks'][0]['status']=='queued'
    monkeypatch.setattr(settings,'TRANSLATION_MODEL_REVISION','new-immutable-revision')
    assert all(c['status']=='missing' for c in tr.read(source['id'],'ja')['chunks'])
    assert all(c['status']=='queued' for c in tr.read(source['id'],'ja',enqueue=True)['chunks'])


def test_failed_chunks_do_not_stop_other_work_and_retry_is_bounded(source,monkeypatch):
    publish(source)
    tr.read(source['id'],'ja',enqueue=True)
    monkeypatch.setattr(settings,'TRANSLATION_MAX_ATTEMPTS',2)
    row,chunk=tr.claim()
    tr.finish(row,error='numbers_mismatch')
    with store.session() as db:
        r=db.get(store.ChunkTranslation,row.id);r.retry_at=0;r.priority=100;db.commit()
    retry,_=tr.claim()
    assert retry.id==row.id and retry.attempts==2
    tr.finish(retry,error='numbers_mismatch')
    tr.read(source['id'],'ja',enqueue=True)  # Poll/reopen must not reset exhausted retries.
    with store.session() as db:
        assert db.get(store.ChunkTranslation,row.id).status=='failed'
    assert tr.retry_failed(source['id'])==1
    with store.session() as db:
        assert db.get(store.ChunkTranslation,row.id).attempts==0


def test_expired_worker_lease_is_reclaimed_stale_result_cannot_overwrite(source):
    publish(source);tr.read(source['id'],'ja',enqueue=True)
    first,_=tr.claim()
    with store.session() as db:
        r=db.get(store.ChunkTranslation,first.id);r.lease_until=0;r.priority=100;db.commit()
    second,_=tr.claim()
    assert second.id==first.id and second.lease_token!=first.lease_token
    assert not tr.finish(first,text='late result')
    assert tr.finish(second,text='current result')
    assert not tr.heartbeat(first)


def test_read_does_not_enqueue_and_requested_language_gets_priority(source):
    pub=publish(source)
    assert all(c['status']=='missing' for c in tr.read(source['id'],'de')['chunks'])
    assert tr.statistics()=={}
    tr.backfill()
    selected=pub.chunks[0]['id']
    tr.read(source['id'],'de',chunk_ids=[selected],enqueue=True)
    row,_=tr.claim()
    assert row.language=='de' and row.chunk_id==selected


def test_worker_uses_local_provider_and_keeps_results_after_artifact_cleanup(source,monkeypatch):
    from app.services import gemini,jobs
    monkeypatch.setattr(gemini,'generate',Mock(side_effect=AssertionError('No Gemini for translations')))
    pub=publish(source);tr.read(source['id'],'ja',enqueue=True)
    translator=Mock()
    translator.translate.side_effect=lambda text,*args,**kwargs:text
    assert process_one(translator)
    assert translator.translate.call_count==1
    # Translation records are not Job records and do not expire after 24 hours.
    with store.session() as db:
        for r in db.scalars(select(store.ChunkTranslation)):r.created_at=time.time()-86400*7
        db.commit()
    jobs.purge_expired()
    assert tr.statistics().get('completed')==1


def test_production_single_attempt_failure_is_not_retried_by_read_or_backfill(source,monkeypatch):
    monkeypatch.setattr(settings,'TRANSLATION_MAX_ATTEMPTS',1)
    pub=publish(source)
    chunk_id=pub.chunks[0]['id']
    tr.read(source['id'],'ja',chunk_ids=[chunk_id],enqueue=True)
    translator=Mock()
    translator.translate.side_effect=RuntimeError('inference unavailable')
    with pytest.raises(ModelUnavailable):
        process_one(translator)
    assert tr.statistics()=={'failed':1}
    tr.read(source['id'],'ja',chunk_ids=[chunk_id],enqueue=True)
    assert not process_one(translator)
    assert translator.translate.call_count==1
    tr.backfill()
    with store.session() as db:
        failed=db.scalar(select(store.ChunkTranslation).where(
            store.ChunkTranslation.chunk_id==chunk_id,store.ChunkTranslation.language=='ja'))
        assert failed.status=='failed' and failed.attempts==1


def test_ocr_blocked_only_for_affected_chunks(source):
    with store.session() as db:
        doc=db.get(store.Document,source['id'])
        doc.extraction_warnings=['OCR_REQUIRED: pages 2']
        doc.draft=[{**c,'refs':[{**r,'page':2 if i==0 else 3} for r in c['refs']]} for i,c in enumerate(doc.draft)]
        db.commit()
    publish(source)
    result=tr.read(source['id'],'ja',enqueue=True)
    assert result['chunks'][0]['status']=='blocked'
    assert result['chunks'][0]['error']=='ocr_required'
    assert all(c['status']=='queued' for c in result['chunks'][1:])


@pytest.mark.parametrize('original,translated,source,target',[
    ('1,000 cases','1000 件','en','ja'),
    ('80萬筆','800,000 records','zh-TW','en'),
    ('10.2%','10,2 %','en','fr'),
    ('1.234 cases','1,234 cas','en','fr'),
    ('1,000,000 cases','1 000 000 cas','en','fr'),
    ('2026/09/14 10:00','14/09/2026 10:00','en','fr'),
    ('（三）技術自主與基礎建設','(3) Technological Independence and Foundational Infrastructure','zh-TW','en'),
    ('十二、治理政策','12. Governance policy','zh-TW','en'),
    ('（二十一）治理政策','(21) Governance policy','zh-TW','en'),
    ('一般政策與三重區','General policy and Sanchong District','zh-TW','en'),
    ('民國113年，20件','2024, 20 cases','zh-TW','en'),
    ('政府文件：臺北市政府（113）。《113年度績效報告》。',
     'Government document: Taipei City Government (2024). Performance report for 2024.','zh-TW','en'),
    ('政府文件：臺北市政府研究發展考核委員會（111）。《1999專線》。',
     'Government document: Committee (2022). Hotline 1999.','zh-TW','en'),
    ('專案資訊：臺北市政府資訊局（113）。《113年機關實證主題：提升1999服務品質》。',
     'Project Information: Information Bureau (2024). 2024 Agency Pilot: improve 1999 service.','zh-TW','en'),
    ('會議時間：2026/05/04（一）13:45~15:10','Meeting Time: Monday, May 4, 2026, from 1:45 PM to 3:10 PM.','zh-TW','en'),
    ('我們在 5 月 14 號報告','We will present on May 14th.','zh-TW','en'),
    ('2026/12/31 00:30','31 December 2026, 12:30 AM','zh-TW','en'),
    ('一年兩億。幾百萬到幾千萬的計畫。','An annual budget of 200 million. Projects from a few million to tens of millions.','zh-TW','en'),
    ('過去轉換率只有二三成','The conversion rate was only 20% to 30%.','zh-TW','en'),
    ('支持一兩千萬的預算','Support a budget of 10 to 20 million.','zh-TW','en'),
])
def test_numeric_equivalence(original,translated,source,target):
    assert tr.validate_translation(original,translated,source,target)==translated


@pytest.mark.parametrize('original,translated,reason',[
    ('20 cases','25 件','numbers_mismatch'),
    ('See https://example.test/a','See https://example.test/b','links_mismatch'),
    ('name\tvalue\nA\t20','名前\t値\nA 20','table_structure_mismatch'),
    ('text','','empty_output'),
])
def test_invalid_output_is_not_published(original,translated,reason):
    with pytest.raises(tr.TranslationError,match=reason):tr.validate_translation(original,translated)


def test_split_measures_actual_template_tokens_and_never_drops_text():
    original=('一段很長的政策文字。Second sentence. ')*100
    pieces=list(split_to_budget(original,lambda s:len(s)*2+100,512))
    assert ''.join(pieces)==original
    assert all(len(p)*2+100<=512 for p in pieces)


def test_local_adapter_preserves_table_delimiters_and_urls_without_model_reconstruction():
    model=LocalTranslator.__new__(LocalTranslator)
    class IDs:
        shape=(1,20)
    model.inputs=lambda *args:{'input_ids':IDs()}
    model.generate=Mock(side_effect=lambda text,*args:text.replace('City','都市'))
    original='City\t20\nCity https://example.test/a?q=1\t30'
    output=model.translate(original,'en','ja')
    assert output=='都市\t20\n都市 https://example.test/a?q=1\t30'
    assert all('https://' not in call.args[0] for call in model.generate.call_args_list)


def test_routes_validate_and_do_not_offer_gemini_translation(source):
    from app.api.workspace import router
    app=FastAPI();app.include_router(router)
    client=TestClient(app)
    url=f'/api/library/{source["id"]}/translations'
    assert client.post(url,json={'language':'ja'}).status_code==409
    publish(source)
    assert client.post(url,json={'language':'unsupported'}).status_code==422
    response=client.post(url,json={'language':'en','version':1})
    assert response.status_code==200 and response.json()['complete']
    assert client.get(url,params={'language':'en','version':1}).json()['complete']
    response=client.post('/api/artifacts',json={'kind':'translation','scope':'document','source_ids':[source['id']],'language':'ja'})
    assert response.status_code==410


def test_language_scope_does_not_claim_recover_or_reset_other_languages(source,monkeypatch):
    monkeypatch.setattr(settings,'TRANSLATION_MAX_ATTEMPTS',1)
    with store.session() as db:
        db.get(store.Document,source['id']).language='zh-TW';db.commit()
    publish(source);tr.backfill()
    en,_=tr.claim(language='en')
    ja,_=tr.claim(language='ja')
    assert en.language=='en' and ja.language=='ja'
    tr.finish(en,error='numbers_mismatch')
    tr.finish(ja,error='numbers_mismatch')
    assert tr.retry_failed(language='en')==1
    with store.session() as db:
        assert db.get(store.ChunkTranslation,ja.id).status=='failed'
    assert tr.statistics(language='en').get('failed',0)==0
    while claimed:=tr.claim(language='en'):
        row,_=claimed
        assert row.language=='en'
        tr.finish(row,text='translated')
    assert tr.claim(language='en') is None
    assert tr.statistics(language='fr').get('queued',0)>0


def test_numeric_diagnostics_are_bounded_private_and_do_not_publish_candidates(source,monkeypatch):
    monkeypatch.setattr(settings,'TRANSLATION_MAX_ATTEMPTS',1)
    publish(source);tr.read(source['id'],'ja',enqueue=True)
    translator=Mock()
    def invalid(*args,**kwargs):
        return tr.validate_translation('20 cases','25 cases')
    translator.translate.side_effect=invalid
    budget=[1]
    assert process_one(translator,language='ja',diagnostic_budget=budget)
    assert budget==[0]
    with store.session() as db:
        sample=db.scalar(select(store.TranslationDiagnostic))
        assert sample.payload['original_numbers']=={'20':1}
        assert sample.payload['translated_numbers']=={'25':1}
        assert db.get(store.ChunkTranslation,sample.id).text is None
    result=tr.read(source['id'],'ja')
    assert all(item['text'] is None for item in result['chunks'])


def test_list_number_changes_and_missing_repetitions_still_fail():
    for original,translated in [('（三）政策','(4) Policy'),('三、2026 年','3. Year 2025'),
                                ('（三）政策 20 次 20 人','(3) Policy 20 times')]:
        with pytest.raises(tr.TranslationError,match='numbers_mismatch'):
            tr.validate_translation(original,translated,'zh-TW','en')


@pytest.mark.parametrize('source,target',[
    ('1999專線數位轉型（2026）','Digital transformation (2026)'),
    ('113件案件','2024 cases'),
    ('（113）政策','(2024) Policy'),
    ('民國113年','2025'),
    ('政府文件：臺北市政府（111）。《1999專線》。','Government document (2022). Hotline.'),
    ('2026/05/04 13:45','May 4, 2026, 1:45 AM'),
    ('5 月 14 號','June 14th'),
    ('持續113年','Lasted 2024 years'),
    ('一年兩億','An annual budget of 20 million'),
    ('支持一兩千萬的預算','Support a budget of 1 to 2 million'),
    ('轉換率二三成','Conversion rate 20% to 40%'),
])
def test_roc_normalization_does_not_hide_changed_counts_or_missing_identifiers(source,target):
    with pytest.raises(tr.TranslationError,match='numbers_mismatch'):
        tr.validate_translation(source,target,'zh-TW','en')


def test_model_failure_halts_later_tasks_only_in_the_same_execution():
    from app.translation_worker import batch_halted
    assert not batch_halted('first-run')
    assert batch_halted('first-run',halt=True)
    assert batch_halted('first-run')
    assert not batch_halted('separate-run')
    assert not batch_halted(None,halt=True)


def test_http_diagnostic_is_private_and_never_retried(source, monkeypatch, caplog):
    monkeypatch.setattr(settings,'TRANSLATION_MAX_ATTEMPTS',1)
    publish(source);tr.read(source['id'],'ja',enqueue=True)
    translator=Mock()
    translator.translate.side_effect=tr.TranslationError('model_unavailable',diagnostic={
        'kind':'ollama_http_error','http_status':500,'response_excerpt':'PRIVATE RESPONSE'})
    with pytest.raises(ModelUnavailable):
        process_one(translator,language='ja',diagnostic_budget=[1])
    with store.session() as db:
        sample=db.scalar(select(store.TranslationDiagnostic))
        assert sample.payload['http_status']==500
        row=db.get(store.ChunkTranslation,sample.id)
        assert row.status=='failed' and row.attempts==1 and row.text is None
    assert 'PRIVATE RESPONSE' not in caplog.text
    assert not process_one(translator,language='ja')


def test_model_repetition_rejects_one_row_then_processes_next_without_retry(source, monkeypatch):
    monkeypatch.setattr(settings,'TRANSLATION_MAX_ATTEMPTS',1)
    publish(source)
    tr.read(source['id'],'ja',enqueue=True)
    tr.read(source['id'],'fr',enqueue=True)
    translator=Mock()
    translator.translate.side_effect=tr.TranslationError('model_repetition')
    assert process_one(translator,language='ja')
    assert not process_one(translator,language='ja')
    translator.translate.side_effect=lambda text,*args,**kwargs:text
    assert process_one(translator,language='fr')
    assert tr.statistics(language='ja')=={'failed':1}
    assert tr.statistics(language='fr')=={'completed':1}
    assert translator.translate.call_count==2


def test_halted_batch_reports_failure_without_loading_model(monkeypatch):
    from app.translation_worker import main, batch_halted
    batch_halted('halted-test',halt=True)
    monkeypatch.setenv('CLOUD_RUN_EXECUTION','halted-test')
    monkeypatch.setattr('sys.argv',['worker','--language','en'])
    with pytest.raises(SystemExit) as result:
        main()
    assert result.value.code==2


def test_initialization_failure_halts_batch_without_claiming_queue(source, monkeypatch):
    from app.translation_worker import main, batch_halted
    publish(source);tr.read(source['id'],'ja',enqueue=True)
    monkeypatch.setenv('CLOUD_RUN_EXECUTION','init-failure-test')
    monkeypatch.setattr(settings,'TRANSLATION_RUNTIME','ollama')
    monkeypatch.setattr('sys.argv',['worker','--language','ja'])
    monkeypatch.setattr('app.services.ollama_translation.OllamaTranslator',
                        Mock(side_effect=RuntimeError('private configuration detail')))
    with pytest.raises(SystemExit) as result:
        main()
    assert result.value.code==2
    assert batch_halted('init-failure-test')
    assert tr.statistics(language='ja')=={'queued':1}


@pytest.mark.parametrize('source,target',[
    ('壹、願景及任務','1. Vision and Mission.'),
    ('（拾貳）政策','(12) Policy'),
    ('基金會於113 年成立','The foundation was established in 2024.'),
])
def test_formal_chinese_numbering_and_establishment_year(source,target):
    tr.validate_translation(source,target,'zh-TW','en')


def test_formal_numbering_still_rejects_changed_numbers():
    with pytest.raises(tr.TranslationError,match='numbers_mismatch'):
        tr.validate_translation('壹、政策','2. Policy','zh-TW','en')
