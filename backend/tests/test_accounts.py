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
