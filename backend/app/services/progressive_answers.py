"""One evidence snapshot, a quick preview, then an independently reasoned answer."""
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from queue import Queue, Empty, Full
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


class FullAnswerStream:
    def __init__(self):
        self.fragments = Queue(maxsize=64)
        self.stopped = threading.Event()
        self.future = None

    def cancel(self):
        self.stopped.set()
        if self.future is not None:
            self.future.cancel()

    def put(self, fragment):
        while not self.stopped.is_set():
            try:
                self.fragments.put(fragment, timeout=0.1)
                return
            except Full:
                continue


def _full_answer(contents, system, config, stream):
    with rag_timing.phase('detailed'):
        emitted = False
        iterator = iter(gemini.stream(contents, system, **config))
        try:
            while not stream.stopped.is_set():
                try:
                    fragment = next(iterator)
                except StopIteration:
                    break
                if not fragment:
                    continue
                emitted = emitted or bool(fragment.strip())
                stream.put(fragment)
            if not emitted and not stream.stopped.is_set():
                raise ValueError('No full answer generated')
        finally:
            try:
                if hasattr(iterator, 'close'):
                    iterator.close()
            finally:
                stream.put(None)  # Wake the consumer on completion or failure.


def _submit(contents, system, config):
    slots = _full_slots
    if not slots.acquire(blocking=False):
        return None
    stream = FullAnswerStream()
    try:
        future = _full_pool.submit(copy_context().run, _full_answer, contents, system, config, stream)
    except BaseException:
        slots.release()
        raise
    future.add_done_callback(lambda _: slots.release())
    stream.future = future
    return stream


def events(contents, base_system, language, brief_style, detailed_style, brief_config, detailed_config):
    """Start both generations together; stream full-answer fragments after the preview.

    Neither generation consumes the other's text as evidence. Headers and both
    bodies use ordinary chunk events, so persistence/export keep one answer.
    """
    short_title, full_title, preview_warning = COPY[language]
    deadline = time.monotonic() + settings.GEMINI_TIMEOUT_MS / 1000
    full = _submit(contents, base_system + detailed_style, detailed_config)
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
        if full is None:
            raise RuntimeError('Full-answer generation capacity unavailable')
        detailed_started = False
        with rag_timing.span('detailed_wait_after_preview'):
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError('Full answer exceeded the request deadline')
                try:
                    fragment = full.fragments.get_nowait()
                except Empty:
                    if full.future.done():
                        # Recheck after completion: the worker may have queued its
                        # final fragment between the empty check and done().
                        if not full.fragments.empty():
                            continue
                        full.future.result()  # Propagate failure after preserving queued text.
                        break
                    try:
                        fragment = full.fragments.get(timeout=min(2, remaining))
                    except Empty:
                        yield dict(type='heartbeat')
                        continue
                if fragment is None:
                    full.future.result()
                    break
                if not detailed_started:
                    rag_timing.record_since('detailed_first_text', started)
                text = fragment if detailed_started else f'\n\n## {full_title}\n\n' + fragment
                detailed_started = True
                yield dict(type='chunk', text=text, phase='detailed')
    finally:
        if full is not None:
            # An already running HTTP call finishes under its provider timeout;
            # the shared pool and admission bound cap orphaned work.
            full.cancel()
