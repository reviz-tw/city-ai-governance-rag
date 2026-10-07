"""Bridge to an isolated Docling worker; fail visibly, never relabel legacy chunks."""
import hashlib
import json
import subprocess
import tempfile
import os
import threading
import selectors
import atexit
from pathlib import Path
from fastapi import HTTPException
from app.core.config import settings

class DoclingBusy(HTTPException):
    """Retryable processor capacity or transport failure; source is unchanged."""
    def __init__(self,message='Document processor temporarily unavailable'):
        super().__init__(503,message,headers={'Retry-After':'60'})


_local=threading.local()
_workers=[]

def close_local_workers():
    for process,log in _workers:
        if process.poll() is None:
            process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        log.close()
atexit.register(close_local_workers)


def persistent_convert(worker,path,output):
    process=getattr(_local,'process',None)
    if process is None or process.poll() is not None:
        log=tempfile.TemporaryFile()
        process=subprocess.Popen([settings.DOCLING_PYTHON,str(worker),'--serve'],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,text=True)
        _local.process=process;_workers.append((process,log))
    process.stdin.write(json.dumps(dict(input=str(path),output=str(output),max_tokens=settings.DOCLING_CHUNK_TOKENS))+'\n')
    process.stdin.flush()
    with selectors.DefaultSelector() as selector:
        selector.register(process.stdout,selectors.EVENT_READ)
        if not selector.select(timeout=1200):
            process.kill();process.wait()
            raise HTTPException(422,'Docling conversion timed out; original retained')
    line=process.stdout.readline()
    if not line or not json.loads(line).get('ok'):
        raise HTTPException(422,'Docling parsing failed; original retained')


def enabled():return bool(settings.DOCLING_SERVICE_URL or settings.DOCLING_PYTHON)


def parse(data,filename,*,source_uri=None):
    if not enabled():raise HTTPException(503,'Docling worker is not configured')
    limit=256 if source_uri or not settings.DOCLING_SERVICE_URL else 20
    if len(data)>limit*1024*1024:raise HTTPException(413,f'Docling input limit: {limit} MiB')
    if settings.DOCLING_SERVICE_URL:
        import requests
        from google.oauth2.id_token import fetch_id_token
        from google.auth.transport.requests import Request
        url=settings.DOCLING_SERVICE_URL.rstrip('/')
        if not url.startswith('https://'):raise HTTPException(503,'Docling service must use HTTPS')
        token=fetch_id_token(Request(),url)
        if source_uri and len(data)>20*1024*1024:
            allowed=[f'gs://{bucket}/{prefix}' for bucket,prefix in (
                (settings.GCS_BUCKET_NAME,'documents/'),(settings.ARTIFACT_GCS_BUCKET,'managed-originals/')) if bucket]
            if not any(source_uri.startswith(prefix) for prefix in allowed):
                raise HTTPException(422,'Untrusted Docling source path')
            response=requests.post(url+'/parse-source',headers={'Authorization':'Bearer '+token},
                json={'source_uri':source_uri,'max_tokens':settings.DOCLING_CHUNK_TOKENS},timeout=1200)
        else:
            response=requests.post(url+'/parse',headers={'Authorization':'Bearer '+token},
                files={'file':(Path(filename).name,data)},data={'max_tokens':settings.DOCLING_CHUNK_TOKENS},timeout=1200)
        if response.status_code in {429,500,502,503,504}:raise DoclingBusy('Document processor temporarily unavailable')
        if response.status_code!=200:raise HTTPException(422,'Docling parsing failed; original retained')
        result=response.json()
    else:
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/('source'+Path(filename).suffix.lower())
            output=Path(directory)/'result.json';path.write_bytes(data)
            worker=Path(__file__).resolve().parents[2]/'docling_worker'/'converter.py'
            # Source checkout path differs from the application container path.
            if not worker.exists():worker=Path(__file__).resolve().parents[3]/'docling_worker'/'converter.py'
            if os.environ.get('DOCLING_PERSISTENT')=='1':
                persistent_convert(worker,path,output)
            else:
                completed=subprocess.run([settings.DOCLING_PYTHON,str(worker),str(path),str(output),str(settings.DOCLING_CHUNK_TOKENS)],
                    capture_output=True,timeout=1200)
                if completed.returncode or not output.exists():raise HTTPException(422,'Docling parsing failed; original retained')
            result=json.loads(output.read_text())
    if result.get('original_hash')!=hashlib.sha256(data).hexdigest() or result.get('schema_version')!=1:
        raise HTTPException(422,'Docling result does not match the original document')
    from app.services.chunks import validate
    validate(result['chunks'],result['blocks'])
    return result
