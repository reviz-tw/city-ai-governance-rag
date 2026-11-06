"""Durable records; SQLite for local use, PostgreSQL for deployed workers."""
import os
import time
from functools import lru_cache
from pathlib import Path
from sqlalchemy import JSON, Boolean, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from app.core.config import settings

class Base(DeclarativeBase):
    pass

class Document(Base):
    __tablename__ = 'documents'
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    owner: Mapped[str] = mapped_column(String(200))
    shared: Mapped[bool] = mapped_column(Boolean, default=False)
    readers: Mapped[list] = mapped_column(JSON, default=list)
    title: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(20))
    original_key: Mapped[str] = mapped_column(Text)
    original_hash: Mapped[str] = mapped_column(String(64))
    mime: Mapped[str] = mapped_column(String(100))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    blocks: Mapped[list] = mapped_column(JSON, default=list)
    extraction_warnings: Mapped[list] = mapped_column(JSON, default=list)
    draft: Mapped[list] = mapped_column(JSON, default=list)
    draft_revision: Mapped[int] = mapped_column(Integer, default=1)
    published_version: Mapped[int] = mapped_column(Integer, default=0)
    index_status: Mapped[str] = mapped_column(String(30), default='unpublished')
    created_at: Mapped[float] = mapped_column(Float, default=time.time)

class Publication(Base):
    __tablename__ = 'publications'
    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(100), index=True)
    version: Mapped[int] = mapped_column(Integer)
    previous_version: Mapped[int] = mapped_column(Integer, default=0)
    chunks: Mapped[list] = mapped_column(JSON)
    operator: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[float] = mapped_column(Float, default=time.time)
    operation: Mapped[str | None] = mapped_column(Text, nullable=True)
    index_document_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default='pending')
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

class DocumentReview(Base):
    """An explicit person's review of one immutable published version."""
    __tablename__ = 'document_reviews'
    id: Mapped[str] = mapped_column(String(300), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(100), index=True)
    version: Mapped[int] = mapped_column(Integer)
    reviewer_id: Mapped[str] = mapped_column(String(200), index=True)
    reviewer_email: Mapped[str] = mapped_column(String(320))
    reviewed_at: Mapped[float] = mapped_column(Float, default=time.time)

class ChunkTranslation(Base):
    """One durable translation per immutable chunk/version/language/engine contract."""
    __tablename__ = 'chunk_translations'
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(100), index=True)
    version: Mapped[int] = mapped_column(Integer)
    chunk_id: Mapped[str] = mapped_column(String(100))
    source_hash: Mapped[str] = mapped_column(String(64), index=True)
    source_language: Mapped[str] = mapped_column(String(20))
    language: Mapped[str] = mapped_column(String(20), index=True)
    model: Mapped[str] = mapped_column(String(200))
    model_revision: Mapped[str] = mapped_column(String(100))
    rules_version: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30), default='queued', index=True)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(String(100), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    lease_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lease_until: Mapped[float] = mapped_column(Float, default=0)
    retry_at: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)
    updated_at: Mapped[float] = mapped_column(Float, default=time.time)

class TranslationDiagnostic(Base):
    """Operator-only failed segment samples; never served by translation APIs."""
    __tablename__ = 'translation_diagnostics'
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    language: Mapped[str] = mapped_column(String(20), index=True)
    document_id: Mapped[str] = mapped_column(String(100))
    chunk_id: Mapped[str] = mapped_column(String(100))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)


class TranslationBatch(Base):
    """A model outage stops subsequent tasks in the same finite execution."""
    __tablename__ = 'translation_batches'
    id: Mapped[str] = mapped_column(String(200), primary_key=True)
    halted: Mapped[bool] = mapped_column(Boolean, default=False)
    reason: Mapped[str | None] = mapped_column(String(100), nullable=True)


class Job(Base):
    __tablename__ = 'jobs'
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    owner: Mapped[str] = mapped_column(String(200), index=True)
    email: Mapped[str] = mapped_column(String(320))
    kind: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30), default='queued', index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    draft: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    cache_key: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)
    updated_at: Mapped[float] = mapped_column(Float, default=time.time)
    expires_at: Mapped[float] = mapped_column(Float)
    lease_until: Mapped[float] = mapped_column(Float, default=0)

@lru_cache(maxsize=1)
def engine():
    if settings.DATABASE_URL.startswith('sqlite:///'):
        path = settings.DATABASE_URL.removeprefix('sqlite:///')
        if path != ':memory:':
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        return create_engine(settings.DATABASE_URL, connect_args={'check_same_thread': False},hide_parameters=True)
    return create_engine(settings.DATABASE_URL, pool_pre_ping=True, pool_size=2, max_overflow=2,hide_parameters=True)


def session():
    return sessionmaker(engine(), expire_on_commit=False)()


def initialize():
    Base.metadata.create_all(engine())
    _ensure_account_columns()
    from app.services.accounts import bootstrap
    bootstrap()
    Path(settings.ARTIFACT_STORAGE_DIR).mkdir(parents=True, exist_ok=True)


def _ensure_account_columns():
    from sqlalchemy import inspect, text
    eng = engine()
    inspector = inspect(eng)
    if not inspector.has_table('workspace_accounts'):
        return
    existing = {c['name'] for c in inspector.get_columns('workspace_accounts')}
    alterations = [
        ('last_active_at', 'FLOAT'),
        ('updated_at', 'FLOAT'),
        ('updated_by', 'VARCHAR(320)'),
    ]
    missing = [(col, col_type) for col, col_type in alterations if col not in existing]
    if not missing:
        return
    with eng.begin() as conn:
        for col, col_type in missing:
            conn.execute(text(f'ALTER TABLE workspace_accounts ADD COLUMN {col} {col_type}'))


def put_bytes(key: str, data: bytes, mime: str):
    if settings.ARTIFACT_GCS_BUCKET:
        from google.cloud import storage
        storage.Client(project=settings.GCP_PROJECT_ID).bucket(settings.ARTIFACT_GCS_BUCKET).blob(key).upload_from_string(data, content_type=mime)
    else:
        path = local_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def local_path(key: str):
    root = Path(settings.ARTIFACT_STORAGE_DIR).resolve()
    path = (root / key).resolve()
    if not path.is_relative_to(root) or path == root:
        raise ValueError('Invalid storage key')
    return path


def get_bytes(key: str):
    if key.startswith('gs://'):
        from google.cloud import storage
        bucket, name = key[5:].split('/', 1)
        if bucket != settings.GCS_BUCKET_NAME or not name.startswith('documents/'):
            raise ValueError('Untrusted source storage path')
        return storage.Client(project=settings.GCP_PROJECT_ID).bucket(bucket).blob(name).download_as_bytes()
    if settings.ARTIFACT_GCS_BUCKET:
        from google.cloud import storage
        return storage.Client(project=settings.GCP_PROJECT_ID).bucket(settings.ARTIFACT_GCS_BUCKET).blob(key).download_as_bytes()
    return local_path(key).read_bytes()


def delete_bytes(key: str):
    if settings.ARTIFACT_GCS_BUCKET:
        from google.cloud import storage
        storage.Client(project=settings.GCP_PROJECT_ID).bucket(settings.ARTIFACT_GCS_BUCKET).blob(key).delete()
    else:
        local_path(key).unlink(missing_ok=True)

class RateLimit(Base):
    __tablename__ = 'rate_limits'
    key: Mapped[str] = mapped_column(String(300), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[float] = mapped_column(Float)

class MCPToken(Base):
    __tablename__ = 'mcp_tokens'
    digest: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner: Mapped[str] = mapped_column(String(200), index=True)
    email: Mapped[str] = mapped_column(String(320))
    expires_at: Mapped[float] = mapped_column(Float)


def delete_prefix(prefix: str):
    if not prefix.startswith('jobs/') or len(prefix.split('/')) != 3 or not prefix.endswith('/'):
        raise ValueError('Invalid task prefix')
    if settings.ARTIFACT_GCS_BUCKET:
        from google.cloud import storage
        bucket = storage.Client(project=settings.GCP_PROJECT_ID).bucket(settings.ARTIFACT_GCS_BUCKET)
        for blob in bucket.list_blobs(prefix=prefix):
            blob.delete()
    else:
        import shutil
        shutil.rmtree(local_path(prefix), ignore_errors=True)

class DraftRevision(Base):
    __tablename__ = 'draft_revisions'
    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(100), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    chunks: Mapped[list] = mapped_column(JSON)
    operator: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[float] = mapped_column(Float, default=time.time)


class WorkspaceAccount(Base):
    __tablename__ = 'workspace_accounts'
    email: Mapped[str] = mapped_column(String(320), primary_key=True)
    role: Mapped[str] = mapped_column(String(20))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)
    last_active_at: Mapped[float | None] = mapped_column(Float, nullable=True, default=time.time)
    updated_at: Mapped[float | None] = mapped_column(Float, nullable=True, default=time.time)
    updated_by: Mapped[str | None] = mapped_column(String(320), nullable=True)

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    actor: Mapped[str] = mapped_column(String(320), index=True)
    target: Mapped[str] = mapped_column(String(320), default='')
    status: Mapped[str] = mapped_column(String(30), default='succeeded')
    source_ip: Mapped[str] = mapped_column(String(100), default='')
    path: Mapped[str] = mapped_column(String(300), default='')
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    entry_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[float] = mapped_column(Float, default=time.time, index=True)

class AccountInitialization(Base):
    __tablename__ = 'account_initialization'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

class ChatSession(Base):
    __tablename__ = 'chat_sessions'
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    owner: Mapped[str] = mapped_column(String(200), index=True)
    title: Mapped[str] = mapped_column(String(160), default='新對話')
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    updated_at: Mapped[float] = mapped_column(Float, default=time.time)
    busy_until: Mapped[float] = mapped_column(Float, default=0)

class ChatTurn(Base):
    __tablename__ = 'chat_turns'
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(100), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text, default='')
    sources: Mapped[list] = mapped_column(JSON, default=list)
    response_language: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default='running')
    created_at: Mapped[float] = mapped_column(Float, default=time.time)

class ChatSummary(Base):
    __tablename__ = 'chat_summaries'
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(100), index=True)
    through_sequence: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    source_turn_ids: Mapped[list] = mapped_column(JSON)
    method: Mapped[str] = mapped_column(String(40), default='extractive-v1')
    created_at: Mapped[float] = mapped_column(Float, default=time.time)

class DoclingProposal(Base):
    __tablename__ = 'docling_proposals'
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(100), index=True)
    original_hash: Mapped[str] = mapped_column(String(64))
    base_revision: Mapped[int] = mapped_column(Integer)
    blocks: Mapped[list] = mapped_column(JSON)
    chunks: Mapped[list] = mapped_column(JSON)
    details: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(30), default='ready')
    operator: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[float] = mapped_column(Float, default=time.time)
