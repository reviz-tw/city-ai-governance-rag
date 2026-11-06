from unittest.mock import Mock
import requests
import pytest
from app.core.config import settings
from app.services.ollama_translation import OllamaTranslator
from app.services.translations import TranslationError


@pytest.fixture
def runtime(monkeypatch):
    monkeypatch.setattr(settings, 'TRANSLATION_MODEL', 'translategemma:12b')
    monkeypatch.setattr(settings, 'TRANSLATION_MODEL_REVISION', 'sha256:'+'a'*64)
    http = Mock()
    http.get.return_value.json.return_value = {'models': [
        {'name': settings.TRANSLATION_MODEL, 'digest': settings.TRANSLATION_MODEL_REVISION.removeprefix('sha256:')}]}
    monkeypatch.setattr('app.services.ollama_translation.requests.Session', lambda: http)
    return http


def test_rejects_model_drift_and_non_google_model(runtime, monkeypatch):
    runtime.get.return_value.json.return_value['models'][0]['digest'] = 'sha256:'+'b'*64
    with pytest.raises(ValueError, match='pinned digest'):
        OllamaTranslator()
    monkeypatch.setattr(settings, 'TRANSLATION_MODEL', 'another-model:12b')
    with pytest.raises(ValueError, match='Only TranslateGemma'):
        OllamaTranslator()


def test_local_only_deterministic_request_and_traditional_chinese(runtime):
    translator = OllamaTranslator()
    runtime.post.return_value.json.return_value = {'message': {'content': '臺北'}, 'prompt_eval_count': 120}
    assert translator.generate('Taipei', 'en', 'zh-TW') == '臺北'
    endpoint = runtime.post.call_args.args[0]
    request = runtime.post.call_args.kwargs['json']
    assert endpoint == 'http://127.0.0.1:11434/api/chat'
    assert runtime.trust_env is False
    assert 'zh-Hant' in request['messages'][0]['content']
    assert request['options']['temperature'] == 0 and request['stream'] is False


@pytest.mark.parametrize('response,error', [
    ({'done_reason':'length'}, 'output_truncated'),
    ({'prompt_eval_count':9999}, 'input_too_large'),
])
def test_rejects_truncation_and_context_overflow(runtime, response, error):
    translator = OllamaTranslator()
    runtime.post.return_value.json.return_value = response
    with pytest.raises(TranslationError, match=error):
        translator.generate('Policy', 'en', 'ja')


def test_third_attempt_still_leaves_room_after_translation_prompt(runtime, monkeypatch):
    translator = OllamaTranslator()
    monkeypatch.setattr(translator, 'generate', lambda text, source, target: text)
    original = 'Policy text for city administration. '*50
    translated = translator.translate(original, 'en', 'fr', attempt=3)
    assert translated.replace(' ', '') == original.replace(' ', '')


def test_http_failure_preserves_bounded_private_diagnostic_without_retry(runtime):
    translator = OllamaTranslator()
    response = runtime.post.return_value
    response.raise_for_status.side_effect = requests.HTTPError('sensitive body must not become error code')
    response.status_code = 500
    response.text = '{"error":"' + 'private model output '*200 + '"}'
    with pytest.raises(TranslationError) as failure:
        translator.generate('原始片段', 'zh-TW', 'en')
    assert str(failure.value) == 'model_unavailable'
    diagnostic = failure.value.diagnostic
    assert diagnostic['http_status'] == 500
    assert len(diagnostic['response_excerpt']) == 2000
    assert len(diagnostic['response_sha256']) == 64
    assert diagnostic['source_segment'] == '原始片段'
    assert runtime.post.call_count == 1


@pytest.mark.parametrize('error,status,code', [
    ('prediction aborted, token repeat limit reached',500,'model_repetition'),
    ('prediction aborted, token repeat limit reached',503,'model_unavailable'),
    ('runner process has terminated',500,'model_unavailable'),
    ('unknown server failure',500,'model_unavailable'),
])
def test_only_known_repetition_error_is_content_scoped(runtime,error,status,code):
    translator=OllamaTranslator()
    response=runtime.post.return_value
    response.status_code=status
    response.text='private error response'
    response.json.return_value={'error':error}
    response.raise_for_status.side_effect=requests.HTTPError()
    with pytest.raises(TranslationError,match=code):
        translator.generate('Policy','en','ja')
    assert runtime.post.call_count==1


@pytest.mark.parametrize('leader',['...............','．．．．．．','······','……','⋯⋯'])
def test_toc_leaders_and_page_numbers_are_preserved_outside_model(runtime,monkeypatch,leader):
    translator=OllamaTranslator()
    generate=Mock(return_value='Table 6 Main impacts of AI adoption')
    monkeypatch.setattr(translator,'generate',generate)
    source=f'表 6 AI導入的主要影響{leader} 65'
    assert translator.translate(source,'zh-TW','en') == f'Table 6 Main impacts of AI adoption{leader} 65'
    assert generate.call_args.args[0]=='表 6 AI導入的主要影響'
    assert generate.call_count==1
