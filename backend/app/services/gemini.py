"""One SDK and an explicit provider; never silently change credentials or region."""
from contextlib import contextmanager
from google import genai
from google.genai import types
from app.core.config import settings


@contextmanager
def client():
    options = {"http_options": types.HttpOptions(timeout=settings.GEMINI_TIMEOUT_MS)}
    if settings.GEMINI_PROVIDER == "vertex":
        options.update(vertexai=True, project=settings.GCP_PROJECT_ID, location=settings.GEMINI_LOCATION)
    else:
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is required for the developer provider")
        options.update(vertexai=False, api_key=settings.GEMINI_API_KEY)
    with genai.Client(**options) as instance:
        yield instance


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


def generate(contents: str, system: str, schema=None, *, cleaner=False):
    with client() as api:
        response = api.models.generate_content(
            model=settings.GEMINI_CLEANER_MODEL if cleaner else settings.GEMINI_CHAT_MODEL,
            contents=contents, config=generation_config(system, schema))
        if not response.text:
            raise ValueError("The model returned no text")
        return response.text


def stream(contents: str, system: str):
    with client() as api:
        for part in api.models.generate_content_stream(
            model=settings.GEMINI_CHAT_MODEL, contents=contents,
            config=generation_config(system)):
            if part.text:
                yield part.text
