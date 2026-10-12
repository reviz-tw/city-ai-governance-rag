"""Keep long HTTP parses active and cancel parsing when the consumer disconnects."""
import asyncio
import json
import time
import anyio
from fastapi import HTTPException
from starlette.responses import StreamingResponse


def response(operation, *, heartbeat_seconds=15):
    async def body():
        task=asyncio.create_task(operation())
        started=time.monotonic()
        try:
            yield json.dumps({'event':'started'})+'\n'
            while not task.done():
                done,_=await asyncio.wait({task},timeout=heartbeat_seconds)
                if not done:
                    yield json.dumps({'event':'running','elapsed_seconds':round(time.monotonic()-started,2)})+'\n'
            try:
                result=task.result()
            except HTTPException as exc:
                yield json.dumps({'event':'failed','status':exc.status_code,'detail':exc.detail})+'\n'
            except Exception:
                yield json.dumps({'event':'failed','status':422,'detail':'Document conversion failed; original retained'})+'\n'
            else:
                yield json.dumps({'event':'completed','result':result},ensure_ascii=False)+'\n'
        finally:
            # StreamingResponse cancels its generator on http.disconnect. Await actual
            # process cleanup under a shield before allowing another parse to start.
            if not task.done():task.cancel()
            with anyio.CancelScope(shield=True):
                try:await task
                except BaseException:pass
    return StreamingResponse(body(),media_type='application/x-ndjson',headers={'Cache-Control':'no-store'})
