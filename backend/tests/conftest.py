import pytest
from app.core.config import settings
from app.services import store
from app.services.auth import User, current_user

@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(settings,'DATABASE_URL',f'sqlite:///{tmp_path}/test.db')
    monkeypatch.setattr(settings,'ARTIFACT_STORAGE_DIR',str(tmp_path/'files'))
    monkeypatch.setattr(settings,'ARTIFACT_GCS_BUCKET','')
    monkeypatch.setattr(settings,'WORKER_ENABLED',False)
    monkeypatch.setattr(settings,'ADMIN_EMAILS',['admin@example.test'])
    monkeypatch.setattr(settings,'EDITOR_EMAILS',['editor@example.test'])
    monkeypatch.setattr(settings,'AUTH_SESSION_SECRET','test-only-signing-key-not-for-deployment-123456')
    monkeypatch.setattr(settings,'GOOGLE_OAUTH_CLIENT_ID','test-client')
    monkeypatch.setattr(settings,'LOGIN_ALLOWED_EMAILS',[])
    monkeypatch.setattr(settings,'CHUNK_INDEX_ENABLED',False)
    store.engine.cache_clear()
    store.initialize()
    token=current_user.set(User('editor','editor@example.test'))
    yield
    current_user.reset(token)
    store.engine().dispose()
    store.engine.cache_clear()

@pytest.fixture
def source():
    from app.services import documents
    return documents.create(b'# Synthetic governance\n\nIn 2026, 20 cases required review. No automatic approval is allowed.\n\nCity staff must check privacy risks.', 'synthetic.txt','text/plain',{'language':'en'})
