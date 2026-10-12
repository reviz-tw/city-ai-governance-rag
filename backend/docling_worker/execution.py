"""Bounded parsing subprocess: request timeouts cannot leave orphan model threads."""
import asyncio
import json
import os
import sys
import time
import uuid
from pathlib import Path
from fastapi import HTTPException
from . import leases

async def run_conversion(path, max_tokens, *, timeout=None, caller_lease=None, python_executable=None):
    request_id=uuid.uuid4().hex
    started=time.monotonic()
    timeout=timeout or int(os.environ.get('DOCLING_PARSE_TIMEOUT_SECONDS','3600'))
    output=Path(path).with_suffix('.result.json')
    print(json.dumps({'event':'docling_request_started','request_id':request_id,'timeout_seconds':timeout}),flush=True)
    if caller_lease and not await leases.alive(caller_lease):
        await leases.stopped(caller_lease,None)
        raise HTTPException(409,'Caller lease expired; parsing not started')
    process=await asyncio.create_subprocess_exec(python_executable or sys.executable,'-m','docling_worker.converter',str(path),str(output),str(max_tokens),env={**os.environ,'DOCLING_REQUEST_ID':request_id},start_new_session=True)
    failure=None
    try:
        waiter=asyncio.create_task(process.wait())
        while not waiter.done():
            remaining=timeout-(time.monotonic()-started)
            if remaining<=0:raise asyncio.TimeoutError()
            try:await asyncio.wait_for(asyncio.shield(waiter),timeout=min(15,remaining))
            except asyncio.TimeoutError:
                if time.monotonic()-started>=timeout:raise
                if caller_lease and not await leases.alive(caller_lease):
                    failure='caller_lease_expired'
                    raise HTTPException(504,'Caller lease expired; parsing process stopped')
                print(json.dumps({'event':'docling_request_running','request_id':request_id,'elapsed_seconds':round(time.monotonic()-started,2)}),flush=True)
        if process.returncode!=0:
            raise HTTPException(422,'Docling conversion failed; original retained')
        result=json.loads(output.read_text())
        print(json.dumps({'event':'docling_request_completed','request_id':request_id,'elapsed_seconds':round(time.monotonic()-started,2),'chunks':len(result['chunks'])}),flush=True)
        return result
    except asyncio.TimeoutError as exc:
        failure='parse_timeout'
        raise HTTPException(504,'Docling parsing timed out; parsing process stopped') from exc
    except BaseException as exc:
        failure=failure or ('caller_disconnected' if isinstance(exc,asyncio.CancelledError) else type(exc).__name__)
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
            # Kill surviving descendants even if the parent exited on SIGTERM.
            try:os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:pass
        if caller_lease:await leases.stopped(caller_lease,process.returncode)
        if failure:
            print(json.dumps({'event':'docling_process_stopped','request_id':request_id,'returncode':process.returncode}),flush=True)
            print(json.dumps({'event':'docling_request_failed','request_id':request_id,'reason':failure,'elapsed_seconds':round(time.monotonic()-started,2)}),flush=True)
