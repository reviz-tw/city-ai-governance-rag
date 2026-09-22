import time
import pytest
from fastapi.testclient import TestClient
from app.core.config import settings
from app.services import auth, documents, store
from app.services.auth import User


@pytest.fixture
def client(monkeypatch):
    import app.main as main
    monkeypatch.setattr(main, 'session_manager', None)
    monkeypatch.setattr(auth, 'verify_google', lambda token: User(token, token + '@example.test'))
    with TestClient(main.app) as client:
        yield client


def login(client, role):
    response = client.post('/api/auth/login', json={'credential': role}, headers={'origin': 'http://localhost:5173'})
    assert response.status_code == 200


HEADERS = {'origin': 'http://localhost:5173'}


def test_admin_serves_login_application_and_library_requires_auth(client):
    response = client.get('/admin/')
    assert response.status_code == 200 and '/assets/' in response.text
    assert 'docs.forEach' not in response.text
    assert client.get('/api/library').status_code == 401
    assert client.get('/api/library/legacy').status_code == 401
    assert client.get('/admin/tools/').status_code == 200


def test_editor_can_rechunk_save_review_and_submit_index(client, source, monkeypatch):
    monkeypatch.setattr(settings, 'CHUNK_INDEX_ENABLED', True)
    monkeypatch.setattr(settings, 'CHUNK_DATA_STORE_ID', 'test-store')
    from app.services import jobs
    submitted = []
    monkeypatch.setattr(jobs, 'dispatch_job', lambda job: submitted.append(job.id))
    login(client, 'editor')
    path = '/api/library/' + source['id']
    original = client.get(path).json()
    response = client.post(path + '/draft', json={'revision': original['draft_revision'], 'reset': True, 'chunk_size': 100}, headers=HEADERS)
    assert response.status_code == 200
    draft = response.json()
    assert len(draft['draft']) > len(original['draft'])
    assert all(len(c['content']) <= 100 for c in draft['draft'])
    assert draft['original_hash'] == original['original_hash'] and draft['published_version'] == 0
    assert client.get(path).json()['draft'] == draft['draft']
    assert client.post(path + '/draft', json={'revision': original['draft_revision'], 'chunks': original['draft']}, headers=HEADERS).status_code == 409
    assert client.post(path + '/publish', json={'revision': draft['draft_revision'], 'reviewed_diff': 'stale'}, headers=HEADERS).status_code == 409
    review = client.get(path + '/diff').json()
    result = client.post(path + '/publish', json={'revision': draft['draft_revision'], 'reviewed_diff': review['hash']}, headers=HEADERS)
    assert result.status_code == 200 and result.json()['kind'] == 'index'
    assert submitted == [result.json()['id']]
    assert client.get(path).json()['index_status'] == 'pending'
    assert client.get(path).json()['published_version'] == 0
    assert client.post(path + '/publish', json={'revision': draft['draft_revision'], 'reviewed_diff': review['hash']}, headers=HEADERS).status_code == 409


@pytest.mark.parametrize('size', [0, 99, 5001])
def test_rechunk_rejects_invalid_size(client, source, size):
    login(client, 'editor')
    assert client.post('/api/library/' + source['id'] + '/draft', json={'revision': source['draft_revision'], 'reset': True, 'chunk_size': size}, headers=HEADERS).status_code == 422


def test_large_draft_survives_session_expiry_and_requires_rechunk_before_indexing(client, source, monkeypatch):
    monkeypatch.setattr(settings, 'CHUNK_INDEX_ENABLED', True)
    monkeypatch.setattr(settings, 'CHUNK_DATA_STORE_ID', 'test-store')
    login(client, 'editor')
    path = '/api/library/' + source['id']
    original = client.get(path).json()
    chunks = [{**original['draft'][0], 'id':f'c{i+1}', 'order':i,
               'content':f'Human-reviewed passage {i+1}'} for i in range(3781)]
    saved = client.post(path + '/draft', json={'revision':original['draft_revision'], 'chunks':chunks}, headers=HEADERS)
    assert saved.status_code == 200
    assert saved.json()['draft_revision'] == 2 and len(saved.json()['draft']) == 3781
    with store.session() as db:
        revision = db.get(store.DraftRevision, source['id']+':2')
        assert revision and revision.chunks[700]['content'] == 'Human-reviewed passage 701'
    client.cookies.clear()
    assert client.get(path).status_code == 401
    login(client, 'editor')
    reopened = client.get(path).json()
    assert reopened['draft_revision'] == 2 and reopened['draft'][700] == chunks[700]
    review = client.get(path + '/diff').json()
    blocked = client.post(path + '/publish', json={'revision':2,'reviewed_diff':review['hash']}, headers=HEADERS)
    assert blocked.status_code == 422 and '3000' in blocked.json()['detail']
    assert client.get(path).json()['index_status'] == 'unpublished'


@pytest.mark.parametrize('count, expected_status', [(3000, 200), (3001, 422)])
def test_publication_limit_preserves_drafts_and_only_dispatches_allowed_size(client, source, monkeypatch, count, expected_status):
    from app.services import jobs
    monkeypatch.setattr(settings, 'CHUNK_INDEX_ENABLED', True)
    monkeypatch.setattr(settings, 'CHUNK_DATA_STORE_ID', 'test-store')
    submitted = []
    monkeypatch.setattr(jobs, 'dispatch_job', lambda job: submitted.append(job.id))
    login(client, 'editor')
    path = '/api/library/' + source['id']
    original = client.get(path).json()
    passages = [{**original['draft'][0], 'id': f'c{i+1}', 'order': i,
                 'content': f'Reviewed passage {i+1}'} for i in range(count)]
    saved = client.post(path + '/draft', json={'revision': original['draft_revision'], 'chunks': passages}, headers=HEADERS)
    assert saved.status_code == 200
    revision = saved.json()['draft_revision']
    review = client.get(path + '/diff').json()
    result = client.post(path + '/publish', json={'revision': revision, 'reviewed_diff': review['hash']}, headers=HEADERS)
    assert result.status_code == expected_status
    current = client.get(path).json()
    assert current['draft'] == passages and current['published_version'] == 0
    with store.session() as db:
        publication = db.get(store.Publication, source['id'] + ':1')
        if expected_status == 200:
            assert submitted == [result.json()['id']]
            assert publication.chunks == passages and publication.status == 'pending'
            assert current['index_status'] == 'pending'
        else:
            assert not submitted and publication is None
            assert '3000' in result.json()['detail']
            assert current['index_status'] == 'unpublished'


def test_library_shows_durable_draft_save_and_latest_index_submission(client, source, monkeypatch):
    from app.services import jobs
    monkeypatch.setattr(settings, 'CHUNK_INDEX_ENABLED', True)
    monkeypatch.setattr(settings, 'CHUNK_DATA_STORE_ID', 'test-store')
    monkeypatch.setattr(jobs, 'dispatch_job', lambda job: None)
    login(client, 'editor')
    path = '/api/library/' + source['id']
    initial = next(d for d in client.get('/api/library').json() if d['id'] == source['id'])
    assert initial['last_draft_saved_at'] is None
    assert initial['last_index_submission'] is None

    before = time.time()
    saved = client.post(path + '/draft', json={'revision':initial['draft_revision'],
                         'chunks':client.get(path).json()['draft']}, headers=HEADERS).json()
    assert before <= saved['last_draft_saved_at'] <= time.time()
    assert saved['last_index_submission'] is None
    listed = next(d for d in client.get('/api/library').json() if d['id'] == source['id'])
    assert listed['last_draft_saved_at'] == saved['last_draft_saved_at']

    review = client.get(path + '/diff').json()
    submitted = client.post(path + '/publish', json={'revision':saved['draft_revision'],
                            'reviewed_diff':review['hash']}, headers=HEADERS)
    assert submitted.status_code == 200
    latest = client.get(path).json()['last_index_submission']
    assert latest['version'] == 1 and latest['status'] == 'pending'
    assert before <= latest['submitted_at'] <= time.time()
    assert next(d for d in client.get('/api/library').json() if d['id'] == source['id'])['last_index_submission'] == latest

    with store.session() as db:
        db.get(store.Publication, source['id'] + ':1').status = 'published'
        doc = db.get(store.Document, source['id'])
        doc.index_status, doc.published_version = 'indexed', 1
        db.commit()
    assert client.get(path).json()['last_index_submission'] == {**latest, 'status':'published'}

    newer = client.post(path + '/draft', json={'revision':saved['draft_revision'],
                        'chunks':saved['draft']}, headers=HEADERS).json()
    assert newer['last_draft_saved_at'] > latest['submitted_at']
    assert newer['last_index_submission']['version'] == 1
    review = client.get(path + '/diff').json()
    second = client.post(path + '/publish', json={'revision':newer['draft_revision'],
                         'reviewed_diff':review['hash']}, headers=HEADERS)
    assert second.status_code == 200
    assert client.get(path).json()['last_index_submission']['version'] == 2


def test_reader_cannot_edit_or_publish_shared_document(client, source):
    with store.session() as db:
        db.get(store.Document, source['id']).shared = True
        db.commit()
    login(client, 'reader')
    path = '/api/library/' + source['id']
    value = client.get(path).json()
    assert not value['editable'] and 'draft' not in value
    assert client.post(path + '/draft', json={'revision': value['draft_revision'], 'reset': True}, headers=HEADERS).status_code == 403
    assert client.post(path + '/publish', json={'revision': value['draft_revision'], 'reviewed_diff': 'x'}, headers=HEADERS).status_code == 403
    assert client.post(path + '/preview-reflow', json={'revision': value['draft_revision'], 'chunks': []}, headers=HEADERS).status_code == 403


def test_editor_can_preview_reflow_but_stale_or_invalid_ranges_are_rejected(client, source):
    login(client, 'editor')
    path = '/api/library/' + source['id']
    doc = client.get(path).json()
    doc['draft'][0]['content'] = '機關導入人工智慧時，\n應保留人工覆核。'
    body = {'revision':doc['draft_revision'], 'chunks':doc['draft']}
    result = client.post(path + '/preview-reflow', json=body, headers=HEADERS)
    assert result.status_code == 200 and result.json()['changed'] == 1
    assert client.get(path).json()['draft_revision'] == doc['draft_revision']
    assert client.post(path + '/preview-reflow', json={**body, 'revision':-1}, headers=HEADERS).status_code == 409
    body['chunks'][0]['refs'][0]['page'] = 999
    assert client.post(path + '/preview-reflow', json=body, headers=HEADERS).status_code == 422


def test_admin_opens_historical_draft_without_overwriting_existing_edits(client, monkeypatch):
    from app.pipelines import vertex_search
    monkeypatch.setattr(vertex_search, 'list_governance_documents', lambda: [{'filename': 'historical.txt', 'gcs_uri': f'gs://{settings.GCS_BUCKET_NAME}/documents/historical.txt', 'language': 'en'}])
    monkeypatch.setattr(store, 'get_bytes', lambda key: b'Original historical governance document.')
    login(client, 'admin')
    response = client.post('/api/library/legacy-draft', json={'filename': 'historical.txt'}, headers=HEADERS)
    assert response.status_code == 200
    value = response.json()
    assert value['editable'] and value['legacy_filename'] == 'historical.txt'
    value['draft'][0]['content'] = 'Human-reviewed draft.'
    saved = client.post('/api/library/' + value['id'] + '/draft', json={'revision': value['draft_revision'], 'chunks': value['draft']}, headers=HEADERS).json()
    reopened = client.post('/api/library/legacy-draft', json={'filename': 'historical.txt'}, headers=HEADERS).json()
    assert reopened['draft'] == saved['draft'] and reopened['draft_revision'] == saved['draft_revision']
    assert client.post('/api/library/legacy-draft', json={'filename': '../secrets.txt'}, headers=HEADERS).status_code == 404
    login(client, 'editor')
    assert client.post('/api/library/legacy-draft', json={'filename': 'historical.txt'}, headers=HEADERS).status_code == 403


def test_worker_migration_accepts_only_configured_audiences_and_worker_identity(monkeypatch):
    from google.oauth2 import id_token
    from fastapi import HTTPException, Request
    from app.main import verify_worker
    monkeypatch.setattr(settings, 'APP_ORIGIN', 'https://stable.example.test')
    monkeypatch.setattr(settings, 'WORKER_LEGACY_ORIGINS', ['https://candidate.example.test'])
    monkeypatch.setattr(settings, 'WORKER_SERVICE_ACCOUNT', 'worker@example.test')
    claims = {'aud': settings.APP_ORIGIN, 'email': settings.WORKER_SERVICE_ACCOUNT, 'email_verified': True}
    monkeypatch.setattr(id_token, 'verify_oauth2_token', lambda *args: claims)
    request = Request({'type': 'http', 'headers': [(b'authorization', b'Bearer test')]})
    verify_worker(request)
    claims['aud'] = settings.WORKER_LEGACY_ORIGINS[0]
    verify_worker(request)
    claims['aud'] = 'https://untrusted.example.test'
    with pytest.raises(HTTPException):
        verify_worker(request)
    claims.update(aud=settings.APP_ORIGIN, email='different@example.test')
    with pytest.raises(HTTPException):
        verify_worker(request)
