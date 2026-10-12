"""Storage-backed caller lease survives Cloud Run's HTTP proxy disconnect behavior."""
import asyncio
import datetime
import json
import os
import re
from urllib.parse import quote


def key(identifier, stopped=False):
    if not re.fullmatch(r'[a-f0-9]{32}',identifier):raise ValueError('Invalid caller lease')
    return f'docling-leases/{identifier}'+('.stopped.json' if stopped else '.json')


def access(identifier, stopped=False, payload=None):
    from google.auth import default
    from google.auth.transport.requests import AuthorizedSession
    bucket=os.environ['DOCLING_ARTIFACT_BUCKET'];name=key(identifier,stopped)
    credentials,_=default(scopes=['https://www.googleapis.com/auth/devstorage.read_write'])
    with AuthorizedSession(credentials) as client:
        if payload is not None:
            result=client.post(f'https://storage.googleapis.com/upload/storage/v1/b/{quote(bucket,safe="")}/o',params={'uploadType':'media','name':name},data=json.dumps(payload),headers={'Content-Type':'application/json'},timeout=(5,10))
            result.raise_for_status();return True
        result=client.get(f'https://storage.googleapis.com/storage/v1/b/{quote(bucket,safe="")}/o/{quote(name,safe="")}',params={'fields':'updated'},timeout=(5,10))
        if result.status_code==404:return False
        result.raise_for_status()
        updated=datetime.datetime.fromisoformat(result.json()['updated'].replace('Z','+00:00'))
        return (datetime.datetime.now(datetime.timezone.utc)-updated).total_seconds()<45


async def alive(identifier):
    try:return await asyncio.to_thread(access,identifier)
    except Exception:return False


async def stopped(identifier,returncode):
    try:await asyncio.to_thread(access,identifier,True,{'returncode':returncode})
    except Exception:
        import logging
        logging.getLogger(__name__).exception('docling_stop_ack_failed')
