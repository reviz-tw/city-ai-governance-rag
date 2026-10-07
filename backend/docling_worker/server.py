"""Private Cloud Run service. Cloud Run IAM validates callers; local bind is localhost."""
import asyncio
import tempfile
import os
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from .converter import convert
from pydantic import BaseModel, Field
app=FastAPI(docs_url=None,redoc_url=None)
lock=asyncio.Lock()

class StoredSource(BaseModel):
    source_uri:str=Field(max_length=2048)
    max_tokens:int=Field(default=768,ge=128,le=2048)

def read_source(uri):
    bucket=os.environ.get('DOCLING_SOURCE_BUCKET','')
    prefix=f'gs://{bucket}/documents/'
    if not bucket or not uri.startswith(prefix):
        raise HTTPException(422,'Untrusted source storage path')
    from google.auth import default
    from google.auth.transport.requests import AuthorizedSession
    from urllib.parse import quote
    key=uri[len(f'gs://{bucket}/'):]
    credentials,_=default(scopes=['https://www.googleapis.com/auth/devstorage.read_only'])
    with AuthorizedSession(credentials) as client:
        response=client.get(f'https://storage.googleapis.com/storage/v1/b/{quote(bucket,safe="")}/o/{quote(key,safe="")}?alt=media',stream=True,timeout=120)
        response.raise_for_status()
        data=bytearray()
        for part in response.iter_content(1024*1024):
            data.extend(part)
            if len(data)>256*1024*1024:raise HTTPException(413,'Source limit: 256 MiB')
    return bytes(data)

@app.post('/parse-source')
async def parse_source(source:StoredSource):
    async with lock:
        data=await asyncio.to_thread(read_source,source.source_uri)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/('source'+Path(source.source_uri).suffix.lower());path.write_bytes(data)
            try:return await asyncio.to_thread(convert,path,source.max_tokens)
            except Exception as exc:
                raise HTTPException(422,'Docling conversion failed; original document retained') from exc

@app.get('/health')
def health():return {'status':'ok','processor':'docling'}

@app.post('/parse')
async def parse(file:UploadFile=File(...),max_tokens:int=Form(768)):
    suffix=Path(file.filename or '').suffix.lower()
    if suffix not in {'.pdf','.doc','.docx','.txt','.md','.html','.xlsx','.pptx'}:
        raise HTTPException(415,'Unsupported Docling input format')
    if not 128<=max_tokens<=2048:raise HTTPException(422,'Invalid token limit')
    data=await file.read(20*1024*1024+1)
    if len(data)>20*1024*1024:raise HTTPException(413,'Upload limit: 20 MiB')
    async with lock:
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/('source'+suffix);path.write_bytes(data)
            try:return await asyncio.to_thread(convert,path,max_tokens)
            except Exception as exc:
                raise HTTPException(422,'Docling conversion failed; original document retained') from exc
