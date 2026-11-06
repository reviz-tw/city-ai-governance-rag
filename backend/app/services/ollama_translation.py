"""TranslateGemma through a co-located Ollama process, pinned to a manifest digest."""
import re
import hashlib
import requests
from app.core.config import settings
from app.services.languages import LANG_NAMES
from app.services.local_translation import LocalTranslator
from app.services.translations import TranslationError


class OllamaTranslator(LocalTranslator):
    def __init__(self):
        if not settings.TRANSLATION_MODEL.startswith('translategemma:'):
            raise ValueError('Only TranslateGemma is enabled for the Ollama worker')
        if not re.fullmatch(r'sha256:[a-f0-9]{64}', settings.TRANSLATION_MODEL_REVISION):
            raise ValueError('TRANSLATION_MODEL_REVISION must pin the Ollama manifest digest')
        self.http = requests.Session()
        self.http.trust_env = False
        self.url = 'http://127.0.0.1:11434'
        response = self.http.get(self.url+'/api/tags',timeout=10)
        response.raise_for_status()
        model = next((m for m in response.json()['models'] if m['name']==settings.TRANSLATION_MODEL),None)
        if not model or model['digest'].removeprefix('sha256:') != settings.TRANSLATION_MODEL_REVISION.removeprefix('sha256:'):
            raise ValueError('Installed TranslateGemma weights do not match the pinned digest')

    @staticmethod
    def prompt(text, source, target):
        codes={'zh-TW':'zh-Hant','zh-CN':'zh-Hans'}
        return (f'You are a professional {LANG_NAMES[source]} ({codes.get(source,source)}) to '
                f'{LANG_NAMES[target]} ({codes.get(target,target)}) translator. Your goal is to accurately '
                f'convey the meaning and nuances of the original {LANG_NAMES[source]} text while adhering to '
                f'{LANG_NAMES[target]} grammar, vocabulary, and cultural sensitivities.\n'
                'Preserve every number, quantity, date, list number, and identifier. '
                'Hotline numbers such as 1999 are service identifiers, not years; never omit them.\n'
                f'Produce only the {LANG_NAMES[target]} translation, without any additional explanations or '
                f'commentary. Please translate the following {LANG_NAMES[source]} text into {LANG_NAMES[target]}:\n\n\n{text}')

    def count_tokens(self, text, source, target):
        # Conservative UTF-8 byte bound, including prompt and chat framing. Ollama
        # does not expose a tokenizer API. Check actual prompt_eval_count as well.
        return len(self.prompt(text,source,target).encode('utf-8'))+64

    def generate(self, text, source, target):
        response = self.http.post(self.url+'/api/chat', json={
            'model':settings.TRANSLATION_MODEL, 'stream':False, 'keep_alive':'30m',
            'messages':[{'role':'user','content':self.prompt(text,source,target)}],
            'options':{'temperature':0, 'seed':0, 'num_ctx':4096,
                       'num_predict':settings.TRANSLATION_OUTPUT_TOKENS}},timeout=(10,240))
        try:
            response.raise_for_status()
        except requests.HTTPError:
            # Ollama's JSON error can contain model output. Keep a bounded copy
            # only in the private diagnostic table, never the public logs.
            body = response.text
            try:
                error = response.json().get('error')
            except (ValueError, AttributeError):
                error = None
            code = ('model_repetition' if response.status_code == 500 and
                    error == 'prediction aborted, token repeat limit reached'
                    else 'model_unavailable')
            raise TranslationError(code, diagnostic={
                'kind': 'ollama_http_error', 'http_status': response.status_code,
                'response_excerpt': body[:2000],
                'response_sha256': hashlib.sha256(body.encode()).hexdigest(),
                'source_segment': text, 'source_language': source, 'target_language': target,
            }) from None
        value=response.json()
        if value.get('done_reason')=='length':
            raise TranslationError('output_truncated')
        if value.get('prompt_eval_count',0)>settings.TRANSLATION_INPUT_TOKENS:
            raise TranslationError('input_too_large')
        return value.get('message',{}).get('content','').strip()
