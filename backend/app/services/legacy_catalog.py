"""Prepare the historical catalogue in a bounded Cloud Run Job, never in a query.

Run: python -m app.services.legacy_catalog
Only the configured public documents/ collection is eligible. Existing sources,
reviewed drafts, publication versions and original bytes are never overwritten.
"""
import json
import logging
from pathlib import Path
from google.cloud import storage
from sqlalchemy import text
from sqlalchemy.orm import load_only
from app.core.config import settings
from app.services import documents, store

logger = logging.getLogger(__name__)


def prepare_collection(blobs):
    counts = dict(prepared=0, existing=0, unsupported=0, failed=0)
    for blob in blobs:
        if blob.name.endswith('/'):
            continue
        if Path(blob.name).suffix.lower() not in {'.pdf', '.docx', '.txt', '.md'}:
            counts['unsupported'] += 1
            continue
        result = dict(link=f'gs://{settings.GCS_BUCKET_NAME}/{blob.name}',
                      title=blob.name.removeprefix('documents/'), metadata=blob.metadata or {})
        identifier = documents.legacy_identifier(result)
        if not identifier:
            continue
        with store.session() as db:
            if db.get(store.Document, identifier, options=[load_only(store.Document.id)]):
                counts['existing'] += 1
                continue
        try:
            documents.prepare_legacy(result)
            counts['prepared'] += 1
        except Exception as exc:
            counts['failed'] += 1
            logger.warning('legacy_prepare_failed id=%s kind=%s', identifier, type(exc).__name__)
    return counts


def main():
    logging.basicConfig(level=logging.INFO)
    store.initialize()
    # A connection-scoped lock prevents overlapping scheduled executions. Process
    # failure releases it automatically; individual files commit independently.
    with store.engine().connect() as lock:
        postgres = lock.dialect.name == 'postgresql'
        if postgres and not lock.scalar(text('SELECT pg_try_advisory_lock(1749932106)')):
            print(json.dumps(dict(event='legacy_catalog', status='already_running')))
            return
        try:
            client = storage.Client(project=settings.GCP_PROJECT_ID)
            counts = prepare_collection(client.list_blobs(settings.GCS_BUCKET_NAME, prefix='documents/'))
            print(json.dumps(dict(event='legacy_catalog', **counts)), flush=True)
            if counts['failed']:
                raise RuntimeError('Some historical sources could not be prepared; inspect job logs')
        finally:
            if postgres:
                lock.execute(text('SELECT pg_advisory_unlock(1749932106)'))


if __name__ == '__main__':
    main()
