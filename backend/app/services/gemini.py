"""One SDK and an explicit provider; never silently change credentials or region."""
from contextlib import contextmanager
import atexit
import threading
import time
from app.services import rag_timing
from google import genai
from google.genai import types
from app.core.config import settings


_clients = threading.local()
_all_clients = []
_clients_lock = threading.Lock()


@atexit.register
def close_clients():
    for instance in _all_clients:
        instance.close()


@contextmanager
def client():
    # Worker threads reuse their HTTP connection pool and authenticated client.
    key = (settings.GEMINI_PROVIDER, settings.GCP_PROJECT_ID, settings.GEMINI_LOCATION,
           settings.GEMINI_API_KEY, settings.GEMINI_TIMEOUT_MS)
    if getattr(_clients, 'key', None) != key:
        options = {"http_options": types.HttpOptions(timeout=settings.GEMINI_TIMEOUT_MS)}
        if settings.GEMINI_PROVIDER == "vertex":
            options.update(vertexai=True, project=settings.GCP_PROJECT_ID, location=settings.GEMINI_LOCATION)
        else:
            if not settings.GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY is required for the developer provider")
            options.update(vertexai=False, api_key=settings.GEMINI_API_KEY)
        with rag_timing.span('model_client_setup'):
            instance = genai.Client(**options)
        _clients.key, _clients.instance = key, instance
        with _clients_lock:
            _all_clients.append(instance)
    yield _clients.instance


def wire_schema(schema):
    # Vertex's constrained decoder rejects some deeply combined length/item bounds.
    # Keep the type/citation structure on the wire; Pydantic enforces all bounds after generation.
    value = schema.model_json_schema() if hasattr(schema, 'model_json_schema') else schema
    def strip(node):
        if isinstance(node, dict):
            value = {k:strip(v) for k,v in node.items() if k not in {'minLength','maxLength','minItems','maxItems','minimum','maximum'}}
            hints = []
            for key, text in [('minLength','Minimum characters'),('maxLength','Maximum characters'),
                              ('minItems','Minimum items'),('maxItems','Maximum items'),
                              ('minimum','Minimum value'),('maximum','Maximum value')]:
                if key in node:
                    hints.append(f'{text}: {node[key]}.')
            if hints:
                value['description'] = ' '.join([node.get('description',''),*hints]).strip()
            return value
        if isinstance(node, list):
            return [strip(v) for v in node]
        return node
    return strip(value)


def generation_config(system_instruction: str, schema=None):
    config = dict(system_instruction=system_instruction,
                  temperature=settings.GEMINI_TEMPERATURE,
                  max_output_tokens=settings.GEMINI_MAX_OUTPUT_TOKENS)
    if settings.GEMINI_THINKING_LEVEL is not None:
        config["thinking_config"] = types.ThinkingConfig(thinking_level=settings.GEMINI_THINKING_LEVEL)
    elif settings.GEMINI_THINKING_BUDGET is not None:
        config["thinking_config"] = types.ThinkingConfig(thinking_budget=settings.GEMINI_THINKING_BUDGET)
    if schema is not None:
        config.update(response_mime_type="application/json", response_schema=wire_schema(schema))
    return types.GenerateContentConfig(**config)


def generate(contents: str, system: str, schema=None, *, cleaner=False, max_output_tokens=None, thinking_level=None):
    config=generation_config(system, schema)
    if max_output_tokens is not None:config.max_output_tokens=max_output_tokens
    if thinking_level is not None:
        config.thinking_config = types.ThinkingConfig(thinking_level=thinking_level)
    with client() as api:
        response = api.models.generate_content(
            model=settings.GEMINI_CLEANER_MODEL if cleaner else settings.GEMINI_CHAT_MODEL,
            contents=contents, config=config)
        observe_response(response)
        if not response.text:
            raise ValueError("The model returned no text")
        return response.text


class OutputTruncated(RuntimeError):
    pass


def observe_response(response):
    usage = getattr(response, 'usage_metadata', None)
    if usage and any(getattr(usage, field, None) is not None for field in
                     ('prompt_token_count', 'candidates_token_count', 'thoughts_token_count')) and (trace := rag_timing.current()):
        trace.event('rag_model_usage', input_tokens=usage.prompt_token_count,
                    output_tokens=usage.candidates_token_count, thought_tokens=usage.thoughts_token_count)
    for candidate in getattr(response, 'candidates', None) or []:
        reason = getattr(candidate, 'finish_reason', None)
        if trace := rag_timing.current():
            if reason:
                trace.event('rag_model_finish', reason=str(reason))
        if reason == types.FinishReason.MAX_TOKENS:
            raise OutputTruncated('Model output limit reached')


def stream(contents: str, system: str, *, max_output_tokens=None, thinking_level=None, timeout_ms=None):
    config = generation_config(system)
    if max_output_tokens is not None:
        config.max_output_tokens = max_output_tokens
    if thinking_level is not None:
        config.thinking_config = types.ThinkingConfig(thinking_level=thinking_level)
    if timeout_ms is not None:
        config.http_options = types.HttpOptions(timeout=timeout_ms)
    started = time.monotonic()
    first = True
    with client() as api:
        with rag_timing.span('model_generation'):
            for part in api.models.generate_content_stream(
                model=settings.GEMINI_CHAT_MODEL, contents=contents, config=config):
                if part.text:
                    if first:
                        rag_timing.record_since('model_first_text', started)
                        first = False
                    yield part.text
                observe_response(part)
