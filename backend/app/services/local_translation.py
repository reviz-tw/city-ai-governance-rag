"""Optional local TranslateGemma runtime; deliberately absent from the web image."""
import re
from app.core.config import settings
from app.services.translations import TranslationError, validate_translation


def split_to_budget(text, count_tokens, budget):
    """Split at sentence/word boundaries, measured with the actual chat template tokenizer."""
    remaining = text
    while remaining:
        if count_tokens(remaining) <= budget:
            yield remaining
            return
        lo, hi = 1, len(remaining)
        while lo < hi:
            mid = (lo+hi+1)//2
            if count_tokens(remaining[:mid]) <= budget:
                lo = mid
            else:
                hi = mid-1
        if count_tokens(remaining[:lo]) > budget:
            raise TranslationError('input_too_large')
        boundary = max(remaining.rfind(mark, max(1,lo//2), lo) for mark in ('。','！','？','. ','; ',' '))
        end = boundary+1 if boundary >= 0 else lo
        yield remaining[:end]
        remaining = remaining[end:]


class LocalTranslator:
    def __init__(self, device='auto', local_files_only=False):
        import torch
        from transformers import AutoModelForImageTextToText, AutoProcessor
        self.torch = torch
        if device == 'auto':
            device = 'cuda' if torch.cuda.is_available() else ('mps' if torch.backends.mps.is_available() else 'cpu')
        dtype = torch.float32 if device=='cpu' else (torch.float16 if device=='mps' else torch.bfloat16)
        options = dict(revision=settings.TRANSLATION_MODEL_REVISION, local_files_only=local_files_only)
        self.processor = AutoProcessor.from_pretrained(settings.TRANSLATION_MODEL, **options)
        self.model = AutoModelForImageTextToText.from_pretrained(settings.TRANSLATION_MODEL, torch_dtype=dtype, **options).to(device)
        self.model.eval()

    def inputs(self, text, source, target):
        messages = [{'role':'user', 'content':[{'type':'text', 'source_lang_code':source,
                    'target_lang_code':target, 'text':text}]}]
        return self.processor.apply_chat_template(messages, tokenize=True, add_generation_prompt=True,
                                                  return_dict=True, return_tensors='pt')

    def generate(self, text, source, target):
        inputs = self.inputs(text, source, target).to(self.model.device)
        length = inputs['input_ids'].shape[-1]
        if length > settings.TRANSLATION_INPUT_TOKENS:
            raise TranslationError('input_too_large')
        with self.torch.inference_mode():
            output = self.model.generate(**inputs, do_sample=False, max_new_tokens=settings.TRANSLATION_OUTPUT_TOKENS)
        generated = output[0][length:]
        if len(generated) >= settings.TRANSLATION_OUTPUT_TOKENS:
            eos = self.model.generation_config.eos_token_id
            eos = eos if isinstance(eos,list) else [eos]
            if int(generated[-1]) not in eos:
                raise TranslationError('output_truncated')
        return self.processor.decode(generated, skip_special_tokens=True).strip()

    def count_tokens(self, text, source, target):
        return self.inputs(text, source, target)['input_ids'].shape[-1]

    def translate(self, text, source, target, *, attempt=1):
        # Preserve layout, URLs and TOC dot leaders in application code. Asking
        # the model to regenerate long leaders can trigger Ollama's repeat limit.
        parts = re.split(r'(\n+|\t+|https?://[^\s<>()]+|[.．·]{4,}|[…⋯]{2,})', text)
        result = []
        budget = max(512, self.count_tokens('',source,target)+128,
                     settings.TRANSLATION_INPUT_TOKENS // min(attempt,3))
        for part in parts:
            if not part:
                continue
            if part.isspace() or part.startswith(('http://','https://')) or not any(c.isalpha() for c in part):
                result.append(part)
                continue
            prefix, suffix = part[:len(part)-len(part.lstrip())], part[len(part.rstrip()):]
            count = lambda value: self.count_tokens(value, source, target)
            translated = [validate_translation(segment, self.generate(segment,source,target),source,target)
                          for segment in split_to_budget(part.strip(), count, budget)]
            result.append(prefix + ' '.join(translated) + suffix)
        return validate_translation(text, ''.join(result),source,target)
