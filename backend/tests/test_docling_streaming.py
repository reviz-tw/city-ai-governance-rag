import asyncio
import json
import sys
from docling_worker import execution,streaming


def test_stream_disconnect_stops_actual_parser(tmp_path,monkeypatch,capsys):
    async def scenario():
        real_spawn=asyncio.create_subprocess_exec
        processes=[]
        started=asyncio.Event()
        async def spawn(*args,**kwargs):
            process=await real_spawn(sys.executable,'-c','import time; time.sleep(60)',start_new_session=True)
            processes.append(process);started.set();return process
        monkeypatch.setattr(execution.asyncio,'create_subprocess_exec',spawn)
        async def operation():return await execution.run_conversion(tmp_path/'source.pdf',768,timeout=60)
        messages=[]
        async def receive():
            await started.wait()
            return {'type':'http.disconnect'}
        async def send(message):messages.append(message)
        response=streaming.response(operation,heartbeat_seconds=.01)
        await response({'type':'http','asgi':{'spec_version':'2.3'}},receive,send)
        assert processes[0].returncode is not None
        assert not any(b'"completed"' in m.get('body',b'') for m in messages)
    asyncio.run(scenario())
    logs=capsys.readouterr().out
    assert 'caller_disconnected' in logs
    assert logs.index('docling_process_stopped')<logs.index('docling_request_failed')


def test_stream_keeps_connection_active_and_returns_result():
    async def scenario():
        async def operation():
            await asyncio.sleep(.04)
            return {'chunks':[{'id':'c'}]}
        response=streaming.response(operation,heartbeat_seconds=.01)
        events=[json.loads(line) async for line in response.body_iterator]
        assert events[0]['event']=='started'
        assert any(e['event']=='running' for e in events)
        assert events[-1]['event']=='completed'
        assert events[-1]['result']['chunks'][0]['id']=='c'
    asyncio.run(scenario())
