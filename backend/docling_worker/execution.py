"""Bounded parsing subprocess: request timeouts cannot leave orphan model threads."""
import asyncio
import json
import os
import sys
import time
import uuid
from pathlib import Path
from fastapi import HTTPException

async def run_conversion(path, max_tokens, *, timeout=None):
    request_id=uuid.uuid4().hex
    started=time.monotonic()
    timeout=timeout or int(os.environ.get('DOCLING_PARSE_TIMEOUT_SECONDS','3600'))
    output=Path(path).with_suffix('.result.json')
    print(json.dumps({'event':'docling_request_started','request_id':request_id,'timeout_seconds':timeout}),flush=True)
    process=await asyncio.create_subprocess_exec(sys.executable,'-m','docling_worker.converter',str(path),str(output),str(max_tokens),env={**os.environ,'DOCLING_REQUEST_ID':request_id},start_new_session=True)
    try:
        waiter=asyncio.create_task(process.wait())
        while not waiter.done():
            remaining=timeout-(time.monotonic()-started)
            if remaining<=0:raise asyncio.TimeoutError()
            try:await asyncio.wait_for(asyncio.shield(waiter),timeout=min(30,remaining))
            except asyncio.TimeoutError:
                if time.monotonic()-started>=timeout:raise
                print(json.dumps({'event':'docling_request_running','request_id':request_id,'elapsed_seconds':round(time.monotonic()-started,2)}),flush=True)
        if process.returncode!=0:
            raise HTTPException(422,'Docling conversion failed; original retained')
        result=json.loads(output.read_text())
        print(json.dumps({'event':'docling_request_completed','request_id':request_id,'elapsed_seconds':round(time.monotonic()-started,2),'chunks':len(result['chunks'])}),flush=True)
        return result
    except asyncio.TimeoutError as exc:
        print(json.dumps({'event':'docling_request_failed','request_id':request_id,'reason':'parse_timeout','elapsed_seconds':round(time.monotonic()-started,2)}),flush=True)
        raise HTTPException(504,'Docling parsing timed out; parsing process stopped') from exc
    except BaseException as exc:
        print(json.dumps({'event':'docling_request_failed','request_id':request_id,'reason':type(exc).__name__,'elapsed_seconds':round(time.monotonic()-started,2)}),flush=True)
        raise
    finally:
        if process.returncode is None:
            import signal
            try:os.killpg(process.pid,signal.SIGTERM)
            except ProcessLookupError:pass
            try:await asyncio.wait_for(process.wait(),timeout=5)
            except asyncio.TimeoutError:
                try:os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                await process.wait()
