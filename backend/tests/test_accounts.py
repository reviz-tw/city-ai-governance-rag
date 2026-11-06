import pytest
from fastapi import HTTPException, Response
from starlette.requests import Request
from app.services import accounts, auth, store


def as_admin():
    return auth.current_user.set(auth.User('admin', 'admin@example.test'))


def test_management_and_live_authorization():
    with pytest.raises(HTTPException) as e:
        accounts.list_accounts()
    assert e.value.status_code == 403
    token=as_admin()
    try:
        accounts.create_account(accounts.AccountInput(email=' NEW@example.test ', role='reader'))
        assert auth.allowed_user(auth.User('new','new@example.test')).editor is False
        accounts.update_account('new@example.test', accounts.AccountUpdate(role='editor',active=True))
        assert auth.User('new','new@example.test').editor
        accounts.update_account('new@example.test', accounts.AccountUpdate(role='editor',active=False))
        with pytest.raises(HTTPException):
            auth.allowed_user(auth.User('new','new@example.test'))
        accounts.delete_account('new@example.test')
        store.initialize()
        with pytest.raises(HTTPException):
            auth.allowed_user(auth.User('new','new@example.test'))
        with pytest.raises(HTTPException) as e:
            accounts.delete_account('admin@example.test')
        assert e.value.status_code == 409
    finally:
        auth.current_user.reset(token)


def test_deleted_seed_not_recreated_and_unknown_denied():
    token=as_admin()
    try:
        accounts.delete_account('editor@example.test')
        store.initialize()
        assert accounts.role_for('editor@example.test') is None
        with pytest.raises(HTTPException):
            auth.allowed_user(auth.User('unknown','unknown@example.test'))
    finally:
        auth.current_user.reset(token)


def test_duplicate_and_role_validation():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        accounts.AccountInput(email='invalid',role='reader')
    token=as_admin()
    try:
        with pytest.raises(HTTPException) as e:
            accounts.create_account(accounts.AccountInput(email='ADMIN@example.test'))
        assert e.value.status_code == 409
    finally:
        auth.current_user.reset(token)


def test_api_cookie_revocation_and_role_change(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    import app.main as main
    monkeypatch.setattr(main, 'session_manager', None)
    monkeypatch.setattr(auth.id_token,'verify_oauth2_token',lambda credential,*args:{
        'sub':credential,'email':credential+'@example.test','email_verified':True})
    headers={'origin':'http://localhost:5173'}
    with TestClient(app) as admin, TestClient(app) as editor:
        assert admin.post('/api/auth/login',json={'credential':'admin'},headers=headers).status_code==200
        assert editor.post('/api/auth/login',json={'credential':'editor'},headers=headers).status_code==200
        assert editor.get('/api/accounts').status_code==403
        assert admin.post('/api/accounts',json={'email':'new@example.test'},headers=headers).status_code==201
        assert admin.patch('/api/accounts/editor@example.test',json={'role':'reader','active':True},headers=headers).status_code==200
        assert editor.get('/api/auth/me').json()['editor'] is False
        assert admin.patch('/api/accounts/editor@example.test',json={'role':'reader','active':False},headers=headers).status_code==200
        assert editor.get('/api/auth/me').status_code==403
        assert admin.delete('/api/accounts/editor@example.test',headers=headers).status_code==200
        assert editor.post('/api/auth/login',json={'credential':'editor'},headers=headers).status_code==403
        logs_res = admin.get('/api/accounts/audit-logs')
        assert logs_res.status_code == 200
        logs = logs_res.json()
        actions = [entry['action'] for entry in logs]
        assert 'auth.login.succeeded' in actions
        assert 'account.created' in actions
        assert 'account.updated' in actions
        assert 'account.deactivated' in actions
        assert 'account.deleted' in actions
        assert 'auth.access.denied' in actions
        assert all(len(entry['entry_hash']) == 64 and entry['timestamp_utc'].endswith('Z') for entry in logs)


def test_idle_account_auto_disabled_and_last_admin_protected(monkeypatch):
    import time
    from app.core.config import settings
    monkeypatch.setattr(settings, 'ACCOUNT_MAX_IDLE_DAYS', 30)
    token = as_admin()
    try:
        # Make reader@example.test idle for 31 days
        with store.session() as db:
            reader = db.get(store.WorkspaceAccount, 'reader@example.test')
            reader.last_active_at = time.time() - 31 * 86400
            admin_acc = db.get(store.WorkspaceAccount, 'admin@example.test')
            admin_acc.last_active_at = time.time() - 31 * 86400
            db.commit()
        # Reader should be auto-disabled on access check
        assert accounts.role_for('reader@example.test') is None
        with store.session() as db:
            assert db.get(store.WorkspaceAccount, 'reader@example.test').active is False
        # Last active admin must be protected from auto-disable lockout
        assert accounts.role_for('admin@example.test') == 'admin'
        # Re-enabling the account resets last_active_at and restores access
        accounts.update_account('reader@example.test', accounts.AccountUpdate(role='reader', active=True))
        assert accounts.role_for('reader@example.test') == 'reader'
        # Make editor@example.test idle and test batch disable_idle_accounts()
        with store.session() as db:
            editor = db.get(store.WorkspaceAccount, 'editor@example.test')
            editor.last_active_at = time.time() - 45 * 86400
            db.commit()
        disabled = accounts.disable_idle_accounts()
        assert disabled == ['editor@example.test']
        assert accounts.role_for('editor@example.test') is None
    finally:
        auth.current_user.reset(token)


def test_error_masking_and_mcp_cors_origin_restriction(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    import app.main as main
    from app.pipelines import vertex_search
    monkeypatch.setattr(main, 'session_manager', None)
    monkeypatch.setattr(auth.id_token, 'verify_oauth2_token', lambda credential, *args: {
        'sub': credential, 'email': credential + '@example.test', 'email_verified': True})

    def boom():
        raise RuntimeError('SENSITIVE_INTERNAL_DB_PATH=/cloudsql/secret-instance')

    monkeypatch.setattr(vertex_search, 'list_governance_documents', boom)
    headers = {'origin': 'http://localhost:5173'}
    with TestClient(app) as client:
        assert client.post('/api/auth/login', json={'credential': 'editor'}, headers=headers).status_code == 200
        res = client.get('/api/documents/list')
        assert res.status_code == 500
        assert 'SENSITIVE_INTERNAL_DB_PATH' not in res.text
        # Allowed origin on MCP OPTIONS gets echoed back
        opt_ok = client.options('/mcp', headers={'origin': 'http://localhost:5173'})
        assert opt_ok.headers.get('access-control-allow-origin') == 'http://localhost:5173'
        # Untrusted origin on MCP OPTIONS does not get wildcard or untrusted origin echoed
        opt_bad = client.options('/mcp', headers={'origin': 'https://evil.example.com'})
        assert opt_bad.headers.get('access-control-allow-origin') is None
