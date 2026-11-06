"""Shared, versioned chunk translations. No model work runs in a web request."""
import hashlib
import json
import re
import time
import uuid
from collections import Counter

from fastapi import HTTPException
from sqlalchemy import select, update, and_, func
from app.core.config import settings
from app.services import documents, store
from app.services.languages import normalize_language

T = store.ChunkTranslation


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def source_hash(chunk, language):
    return digest([language, chunk['content']])


def identifier(doc, pub, chunk, language):
    return digest([doc.id, pub.version, chunk['id'], source_hash(chunk, doc.language), language,
                   settings.TRANSLATION_MODEL, settings.TRANSLATION_MODEL_REVISION, settings.TRANSLATION_RULES_VERSION])


def engine_filter():
    return (T.model == settings.TRANSLATION_MODEL,
            T.model_revision == settings.TRANSLATION_MODEL_REVISION,
            T.rules_version == settings.TRANSLATION_RULES_VERSION)


def ocr_required(doc, chunk):
    for warning in doc.extraction_warnings:
        if not warning.startswith('OCR_REQUIRED'):
            continue
        match = re.fullmatch(r'OCR_REQUIRED: pages (\d+(?:,\s*\d+)*)', warning)
        pages = {int(p.strip()) for p in match[1].split(',')} if match else None
        if pages is None or any(r.get('page') is None or r['page'] in pages for r in chunk.get('refs', [])):
            return True
    return False


def ensure(db, doc, pub, languages=None, selected=None, priority=0):
    """Caller holds the document row lock. Enqueue atomically with publication."""
    languages = list(dict.fromkeys(normalize_language(l) for l in
                                  (settings.TRANSLATION_LANGUAGES if languages is None else languages)))
    selected = pub.chunks if selected is None else selected
    existing = {r.id:r for r in db.scalars(select(T).where(T.document_id == doc.id, T.version == pub.version,
                                                        *engine_filter()))}
    reusable = {(r.source_hash, r.language):r for r in db.scalars(select(T).where(
        T.document_id == doc.id, T.status == 'completed', *engine_filter()))}
    created = 0
    for chunk in selected:
        for language in languages:
            key = identifier(doc, pub, chunk, language)
            if key in existing:
                existing[key].priority = max(existing[key].priority, priority)
                continue
            row = T(id=key, document_id=doc.id, version=pub.version, chunk_id=chunk['id'],
                    source_hash=source_hash(chunk, doc.language), source_language=doc.language,
                    language=language, model=settings.TRANSLATION_MODEL,
                    model_revision=settings.TRANSLATION_MODEL_REVISION,
                    rules_version=settings.TRANSLATION_RULES_VERSION, priority=priority)
            cached = reusable.get((row.source_hash, language))
            if language == doc.language:
                row.status, row.text = 'completed', chunk['content']
            elif ocr_required(doc, chunk):
                row.status, row.error = 'blocked', 'ocr_required'
            elif cached:
                row.status, row.text = 'completed', cached.text
            db.add(row)
            existing[key] = row
            created += 1
    return created


def selection(doc, pub, chunk_ids, block_ids, version, original_hash):
    if pub is None or pub.status != 'published':
        raise HTTPException(409, 'Publish this document before requesting chunk translations')
    if (version is not None and version != pub.version) or (original_hash and original_hash != doc.original_hash):
        raise HTTPException(409, 'Source version changed; open the current citation')
    if chunk_ids:
        known = {c['id'] for c in pub.chunks}
        if not set(chunk_ids) <= known:
            raise HTTPException(422, 'Unknown published chunk ID')
        selected = [c for c in pub.chunks if c['id'] in chunk_ids]
    elif block_ids:
        if not set(block_ids) <= {b['id'] for b in doc.blocks}:
            raise HTTPException(422, 'Unknown original block ID')
        selected = [c for c in pub.chunks if any(r['block_id'] in block_ids for r in c['refs'])]
    else:
        selected = pub.chunks
    if not selected:
        raise HTTPException(422, 'No published chunks match these passages')
    return selected


def read(document_id, language, *, version=None, chunk_ids=None, block_ids=None, original_hash=None, enqueue=False):
    language = normalize_language(language)
    authorized = documents.get(document_id)
    with store.session() as db:
        query = select(store.Document).where(store.Document.id == authorized.id)
        doc = db.scalar(query.with_for_update() if enqueue else query)
        # Recheck sharing inside the transaction as permissions may have changed.
        from app.services.auth import require_user
        if not doc or not documents.can_read(doc, require_user()):
            raise HTTPException(404, 'Document not found')
        pub = db.get(store.Publication, f'{doc.id}:{doc.published_version}')
        selected = selection(doc, pub, chunk_ids, block_ids, version, original_hash)
        if enqueue:
            ensure(db, doc, pub, [language], selected, priority=10)
            db.flush()
        rows = {r.id:r for r in db.scalars(select(T).where(T.document_id == doc.id, T.version == pub.version,
                                                       T.language == language, *engine_filter()))}
        items = []
        for chunk in selected:
            row = rows.get(identifier(doc, pub, chunk, language))
            items.append(dict(chunk_id=chunk['id'], original=chunk['content'], refs=chunk['refs'],
                              status=row.status if row else 'missing', text=row.text if row and row.status=='completed' else None,
                              error=row.error if row else None, attempts=row.attempts if row else 0))
        result = dict(document_id=doc.id, version=pub.version, source_language=doc.language, language=language,
                      model=settings.TRANSLATION_MODEL, rules_version=settings.TRANSLATION_RULES_VERSION,
                      chunks=items, complete=all(i['status']=='completed' for i in items))
        if enqueue:
            db.commit()
        return result


def backfill(document_id=None):
    """Idempotently queue only current published versions; unchanged results are reused."""
    created = 0
    with store.session() as db:
        query = select(store.Document.id).where(store.Document.published_version > 0)
        if document_id:
            query = query.where(store.Document.id == document_id)
        identifiers = list(db.scalars(query))
    for identifier_ in identifiers:
        with store.session() as db:
            doc = db.scalar(select(store.Document).where(store.Document.id == identifier_).with_for_update())
            if not doc:
                continue
            pub = db.get(store.Publication, f'{doc.id}:{doc.published_version}')
            if pub and pub.status == 'published':
                created += ensure(db, doc, pub)
                db.commit()
    return dict(documents=len(identifiers), created=created)


def current_filter():
    return and_(store.Document.id == T.document_id, store.Document.published_version == T.version)


def scope_filter(document_id=None, language=None):
    filters = list(engine_filter())
    if document_id:
        filters.append(T.document_id == document_id)
    if language:
        filters.append(T.language == normalize_language(language))
    return filters


def statistics(document_id=None, language=None):
    with store.session() as db:
        query = select(T.status, func.count()).join(store.Document, current_filter()).where(*scope_filter(document_id, language))
        return dict(db.execute(query.group_by(T.status)).all())


def retry_failed(document_id=None, language=None):
    """Explicit operator action; background polling never resets exhausted retries."""
    with store.session() as db:
        ids = select(T.id).join(store.Document, current_filter()).where(T.status == 'failed', *scope_filter(document_id, language))
        result = db.execute(update(T).where(T.id.in_(ids)).values(status='queued', attempts=0, error=None,
                            retry_at=0, lease_token=None, lease_until=0, updated_at=time.time()))
        db.commit()
        return result.rowcount


def claim(document_id=None, language=None):
    now = time.time()
    with store.session() as db:
        # Recover a dead worker. A stale completion cannot overwrite a new lease.
        scope = scope_filter(document_id, language)
        db.execute(update(T).where(T.status=='running', T.lease_until<now, *scope).values(
            status='queued', lease_token=None, error='worker_interrupted', updated_at=now))
        db.execute(update(T).where(T.status=='queued', T.attempts>=settings.TRANSLATION_MAX_ATTEMPTS,
                                   *scope).values(status='failed', updated_at=now))
        query = select(T).join(store.Document, current_filter()).where(
            T.status=='queued', T.retry_at<=now, T.attempts<settings.TRANSLATION_MAX_ATTEMPTS, *scope)
        row = db.scalar(query.order_by(T.priority.desc(), T.created_at, T.id).limit(1).with_for_update(skip_locked=True, of=T))
        if row is None:
            db.commit()
            return None
        token = uuid.uuid4().hex
        changed = db.execute(update(T).where(T.id==row.id, T.status=='queued', T.attempts==row.attempts).values(
            status='running', attempts=row.attempts+1, lease_token=token,
            lease_until=now+settings.TRANSLATION_LEASE_SECONDS, updated_at=now))
        if not changed.rowcount:
            db.rollback()
            return None
        db.flush()
        db.refresh(row)
        pub = db.get(store.Publication, f'{row.document_id}:{row.version}')
        chunk = next((c for c in pub.chunks if c['id']==row.chunk_id), None) if pub else None
        if not chunk or source_hash(chunk, row.source_language)!=row.source_hash:
            row.status, row.error, row.lease_token = 'failed', 'source_changed', None
            db.commit()
            return None
        db.commit()
        return row, chunk


def heartbeat(row):
    with store.session() as db:
        changed = db.execute(update(T).where(T.id==row.id, T.status=='running', T.lease_token==row.lease_token).values(
            lease_until=time.time()+settings.TRANSLATION_LEASE_SECONDS, updated_at=time.time()))
        db.commit()
        return bool(changed.rowcount)


def finish(row, text=None, error=None):
    now = time.time()
    status = 'completed' if error is None else ('failed' if row.attempts>=settings.TRANSLATION_MAX_ATTEMPTS else 'queued')
    with store.session() as db:
        changed = db.execute(update(T).where(T.id==row.id, T.status=='running', T.lease_token==row.lease_token).values(
            status=status, text=text if error is None else None, error=error,
            lease_token=None, lease_until=0, retry_at=now+min(30*2**row.attempts,600) if error else 0, updated_at=now))
        db.commit()
        return bool(changed.rowcount)


class TranslationError(ValueError):
    def __init__(self, code, *, diagnostic=None):
        super().__init__(code)
        self.diagnostic = diagnostic


from app.services.translation_numbers import LINKS, numeric_values


def validate_translation(original, translated, source_language='en', target_language='en'):
    if not translated or not translated.strip():
        raise TranslationError('empty_output')
    links = lambda text: Counter(v.rstrip('.,;。；،') for v in LINKS.findall(text))
    if links(original) != links(translated):
        raise TranslationError('links_mismatch')
    if numeric_values(original, source_language) != numeric_values(translated, target_language):
        raise TranslationError('numbers_mismatch', diagnostic={
            'original':original, 'translated':translated,
            'source_language':source_language, 'target_language':target_language,
            'original_numbers':{str(k):v for k,v in numeric_values(original,source_language).items()},
            'translated_numbers':{str(k):v for k,v in numeric_values(translated,target_language).items()},
        })
    # A tabular chunk must retain its row/cell boundaries; do not ask the model to rebuild it.
    if '\t' in original:
        shape = lambda text: [len(line.split('\t')) for line in text.strip().splitlines() if line.strip()]
        if shape(original) != shape(translated):
            raise TranslationError('table_structure_mismatch')
    return translated.strip()
