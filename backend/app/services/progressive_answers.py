"""One evidence snapshot, a quick preview, then an independently reasoned answer."""
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from contextvars import copy_context
from app.core.config import settings
from app.services import gemini, rag_timing

logger = logging.getLogger(__name__)
# Bound abandoned provider calls too; disconnects must not create unlimited workers.
_full_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix='rag-full')
_full_slots = threading.BoundedSemaphore(8)

COPY = {
 'zh-TW': ('快速重點', '完整回答', '快速重點未能完整產生，請以後續完整回答為準。'),
 'zh-CN': ('快速要点', '完整回答', '快速要点未能完整生成，请以后续完整回答为准。'),
 'en': ('Quick take', 'Full answer', 'The quick take could not be completed. Please refer to the full answer below.'),
 'ja': ('要点', '詳しい回答', '要点の生成が完了しませんでした。以下の詳しい回答を確認してください。'),
 'fr': ('En bref', 'Réponse complète', 'Le résumé rapide est incomplet. Consultez la réponse complète ci-dessous.'),
 'es': ('Puntos clave', 'Respuesta completa', 'El resumen rápido está incompleto. Consulte la respuesta completa a continuación.'),
 'ru': ('Кратко', 'Полный ответ', 'Краткий ответ не завершён. См. полный ответ ниже.'),
 'ko': ('핵심 요약', '전체 답변', '핵심 요약을 완료하지 못했습니다. 아래 전체 답변을 확인해 주세요.'),
 'de': ('Kurzüberblick', 'Vollständige Antwort', 'Der Kurzüberblick ist unvollständig. Beachten Sie die vollständige Antwort unten.'),
}


def _full_answer(contents, system, config):
    with rag_timing.phase('detailed'), rag_timing.span('model_generation'):
        answer = gemini.generate(contents, system, **config)
        if not answer or not answer.strip():
            raise ValueError('No full answer generated')
        return answer


def _submit(contents, system, config):
    slots = _full_slots
    if not slots.acquire(blocking=False):
        return None
    try:
        future = _full_pool.submit(copy_context().run, _full_answer, contents, system, config)
    except BaseException:
        slots.release()
        raise
    future.add_done_callback(lambda _: slots.release())
    return future


def events(contents, base_system, language, brief_style, detailed_style, brief_config, detailed_config):
    """Start the full answer immediately; publish it only after it is complete.

    Neither generation consumes the other's text as evidence. Headers and both
    bodies use ordinary chunk events, so persistence/export keep one answer.
    """
    short_title, full_title, preview_warning = COPY[language]
    deadline = time.monotonic() + settings.GEMINI_TIMEOUT_MS / 1000
    future = _submit(contents, base_system + detailed_style, detailed_config)
    try:
        started = time.monotonic()
        emitted = False
        preview = iter(gemini.stream(contents, base_system + brief_style +
            ' This is only the quick opening preview. Use at most two short sentences '
            '(about 80 words or 180 Chinese/Japanese characters). '
            'Keep necessary qualifications and citations; a full independent answer will follow.',
            **brief_config, timeout_ms=settings.RAG_PREVIEW_TIMEOUT_MS))
        try:
            while True:
                try:
                    # StreamingResponse can resume each next() in a different
                    # copied Context. Never keep a ContextVar token across yield.
                    with rag_timing.phase('brief'):
                        fragment = next(preview)
                except StopIteration:
                    break
                if not fragment:
                    continue
                text = fragment if emitted else f'## {short_title}\n\n' + fragment
                emitted = True
                yield dict(type='chunk', text=text, phase='brief')
            if not emitted:
                raise ValueError('No preview generated')
        except Exception as exc:
            logger.warning('preview_failed kind=%s', type(exc).__name__)
            yield dict(type='chunk', text=('\n\n' if emitted else '') + preview_warning,
                       phase='brief', preview_incomplete=True)
        finally:
            with rag_timing.phase('brief'):
                if hasattr(preview, 'close'):
                    preview.close()
            rag_timing.record_since('brief_complete', started)
        yield dict(type='status', stage='expanding')
        if future is None:
            raise RuntimeError('Full-answer generation capacity unavailable')
        with rag_timing.span('detailed_wait_after_preview'):
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError('Full answer exceeded the request deadline')
                try:
                    answer = future.result(timeout=min(2, remaining))
                    break
                except FutureTimeout:
                    if future.done():
                        raise
                    # Keeps the SSE connection and durable conversation lease alive.
                    yield dict(type='heartbeat')
        yield dict(type='chunk', text=f'\n\n## {full_title}\n\n' + answer, phase='detailed')
    finally:
        if future is not None:
            # An already running HTTP call finishes under its provider timeout;
            # the shared pool and admission bound cap orphaned work.
            future.cancel()
