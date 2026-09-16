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
    Path(settings.ARTIFACT_STORAGE_DIR).mkdir(parents=True, exist_ok=True)


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
