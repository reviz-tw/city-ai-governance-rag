"""Request-scoped timings without questions, answers, source text or credentials."""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
import json
import logging
import time
import uuid
from functools import wraps

logger = logging.getLogger(__name__)
_current = ContextVar('rag_timing', default=None)
_phase = ContextVar('rag_generation_phase', default=None)


@dataclass
class Trace:
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    started: float = field(default_factory=time.monotonic)
    stages: dict = field(default_factory=dict)
    status: str = "completed"
    model_metrics: dict = field(default_factory=dict)

    def record(self, stage, milliseconds, **fields):
        if generation_phase := _phase.get():
            stage = generation_phase + '_' + stage
        self.stages[stage] = round(milliseconds, 2)
        logger.info(json.dumps(dict(event='rag_stage', request_id=self.request_id,
            stage=stage, duration_ms=round(milliseconds, 2), **fields), separators=(',', ':')))

    def event(self, name, **fields):
        if generation_phase := _phase.get():
            fields = dict(generation_phase=generation_phase, **fields)
        if name in {'rag_model_usage', 'rag_model_finish'}:
            if generation_phase:
                self.model_metrics.setdefault(generation_phase, {}).update(fields)
            else:
                self.model_metrics.update(fields)
        logger.info(json.dumps(dict(event=name, request_id=self.request_id, **fields), separators=(',', ':')))


def current():
    return _current.get()


@contextmanager
def request_scope():
    if current() is not None:
        yield current()
        return
    trace = Trace()
    token = _current.set(trace)
    try:
        yield trace
    except BaseException:
        trace.status = 'failed'
        raise
    finally:
        trace.event('rag_request', status=trace.status, total_ms=round((time.monotonic()-trace.started)*1000, 2), stages=trace.stages)
        _current.reset(token)


@contextmanager
def span(stage, **fields):
    started = time.monotonic()
    try:
        yield
    finally:
        if trace := current():
            trace.record(stage, (time.monotonic()-started)*1000, **fields)


def record_since(stage, started, **fields):
    if trace := current():
        trace.record(stage, (time.monotonic()-started)*1000, **fields)


class RagTimingMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope.get('path') not in {'/api/chat/stream', '/api/rag/query'}:
            return await self.app(scope, receive, send)
        with request_scope() as trace:
            async def traced_send(message):
                if message['type'] == 'http.response.start':
                    if message['status'] >= 400:
                        trace.status = 'failed'
                    message = {**message, 'headers': [*message.get('headers', []),
                        (b'x-request-id', trace.request_id.encode())]}
                await send(message)
            await self.app(scope, receive, traced_send)


def traced(*, streaming=False):
    def decorate(function):
        if streaming:
            @wraps(function)
            def wrapped(*args, **kwargs):
                with request_scope():
                    yield from function(*args, **kwargs)
        else:
            @wraps(function)
            def wrapped(*args, **kwargs):
                with request_scope():
                    return function(*args, **kwargs)
        return wrapped
    return decorate


def failed():
    if trace := current():
        trace.status = 'failed'


@contextmanager
def phase(name):
    token = _phase.set(name)
    try:
        yield
    finally:
        _phase.reset(token)
