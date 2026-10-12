import asyncio
import sys
import pytest
from fastapi import HTTPException
from docling_worker import execution


def test_timeout_terminates_actual_parser_process(tmp_path,monkeypatch,capsys):
    real_spawn=asyncio.create_subprocess_exec
    processes=[]
    async def spawn(*args,**kwargs):
        process=await real_spawn(sys.executable,'-c','import time; time.sleep(60)',start_new_session=True)
        processes.append(process)
        return process
    monkeypatch.setattr(execution.asyncio,'create_subprocess_exec',spawn)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(execution.run_conversion(tmp_path/'source.pdf',768,timeout=.1))
    assert exc.value.status_code==504
    assert processes[0].returncode is not None
    assert 'parse_timeout' in capsys.readouterr().out


def test_success_logs_completed_chunks(tmp_path,monkeypatch,capsys):
    real_spawn=asyncio.create_subprocess_exec
    async def spawn(*args,**kwargs):
        return await real_spawn(sys.executable,'-c',"import sys; from pathlib import Path; Path(sys.argv[1]).write_text('{\"chunks\":[{\"id\":\"c1\"}]}')",str(args[4]),start_new_session=True)
    monkeypatch.setattr(execution.asyncio,'create_subprocess_exec',spawn)
    result=asyncio.run(execution.run_conversion(tmp_path/'source.pdf',768,timeout=5))
    assert len(result['chunks'])==1
    assert 'docling_request_completed' in capsys.readouterr().out


def test_missing_caller_lease_stops_process_without_disconnect(tmp_path,monkeypatch,capsys):
    real_spawn=asyncio.create_subprocess_exec;processes=[];checks=[];ack=[]
    async def spawn(*args,**kwargs):
        p=await real_spawn(sys.executable,'-c','import time; time.sleep(60)',start_new_session=True)
        processes.append(p);return p
    async def alive(identifier):
        checks.append(identifier);return len(checks)==1
    async def stopped(identifier,code):ack.append((identifier,code))
    real_wait=asyncio.wait_for
    async def fast_wait(awaitable,timeout):return await real_wait(awaitable,min(timeout,.05))
    monkeypatch.setattr(execution.asyncio,'create_subprocess_exec',spawn)
    monkeypatch.setattr(execution.asyncio,'wait_for',fast_wait)
    monkeypatch.setattr(execution.leases,'alive',alive)
    monkeypatch.setattr(execution.leases,'stopped',stopped)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(execution.run_conversion(tmp_path/'source.pdf',768,timeout=60,caller_lease='a'*32))
    assert exc.value.status_code==504
    assert processes[0].returncode is not None
    assert ack==[('a'*32,processes[0].returncode)]
    assert 'caller_lease_expired' in capsys.readouterr().out
