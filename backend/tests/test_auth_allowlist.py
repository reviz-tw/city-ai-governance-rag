import time
import jwt
import pytest
from fastapi import HTTPException
from starlette.requests import Request
from app.core.config import settings
from app.services import auth


def test_google_and_existing_sessions_honor_current_allowlist(monkeypatch):
    monkeypatch.setattr(settings, 'LOGIN_ALLOWED_EMAILS', ['allowed@example.test'])
    monkeypatch.setattr(auth.id_token, 'verify_oauth2_token', lambda *args: {
        'sub': 'google-sub', 'email': 'other@example.test', 'email_verified': True})
    with pytest.raises(HTTPException) as error:
        auth.verify_google('synthetic-token')
    assert error.value.status_code == 403
    now = int(time.time())
    token = jwt.encode(dict(sub='google-sub', email='other@example.test', iat=now,
        exp=now+60, aud='city-governance', iss='city-governance'), settings.AUTH_SESSION_SECRET, algorithm='HS256')
    request = Request({'type':'http', 'headers':[(b'cookie', f'governance_session={token}'.encode())]})
    with pytest.raises(HTTPException) as error:
        auth.authenticate(request)
    assert error.value.status_code == 403
    assert auth.allowed_user(auth.User('sub', 'ALLOWED@example.test')).id == 'sub'


def test_model_schema_keeps_title_and_local_constraints():
    from app.models.artifacts import ReportDraft
    from app.services.gemini import wire_schema
    from pydantic import ValidationError
    schema = wire_schema(ReportDraft)
    assert 'title' in schema['properties']
    assert 'maxLength' not in schema['properties']['title']
    assert 'Maximum characters: 160' in schema['properties']['title']['description']
    assert 'Maximum items: 12' in schema['$defs']['Section']['properties']['citations']['description']
    with pytest.raises(ValidationError):
        ReportDraft(title='x'*161, summary='', sections=[], limitations='')

def test_personal_mcp_credential_scope_rotation_revocation(monkeypatch):
    from fastapi import Response
    from app.services import store
    from sqlalchemy import select
    created = auth.create_mcp_token(Response())
    def request(path='/mcp'):
        return Request({'type':'http','scheme':'https','server':('testserver',443),'path':path,
                        'headers':[(b'authorization',('Bearer '+created['token']).encode())]})
    assert auth.authenticate(request()).id == 'editor'
    with store.session() as db:
        saved = db.scalar(select(store.MCPToken))
        assert saved.digest != created['token']
    with pytest.raises(HTTPException):
        auth.authenticate(request('/api/library'))
    monkeypatch.setattr(settings,'LOGIN_ALLOWED_EMAILS',['other@example.test'])
    with pytest.raises(HTTPException) as blocked:
        auth.authenticate(request())
    assert blocked.value.status_code == 403
    monkeypatch.setattr(settings,'LOGIN_ALLOWED_EMAILS',[])
    auth.create_mcp_token(Response())
    with pytest.raises(HTTPException):
        auth.authenticate(request())
    created = auth.create_mcp_token(Response())
    auth.revoke_mcp_token()
    with pytest.raises(HTTPException):
        auth.authenticate(request())

def test_worker_endpoint_requires_exact_identity(monkeypatch):
    from app.main import verify_worker
    monkeypatch.setattr(settings,'WORKER_SERVICE_ACCOUNT','worker@example.test')
    request=Request({'type':'http','headers':[(b'authorization',b'Bearer synthetic')]})
    monkeypatch.setattr(auth.id_token,'verify_oauth2_token',lambda *args: {'email':'other@example.test','email_verified':True,'aud':settings.APP_ORIGIN})
    with pytest.raises(HTTPException):
        verify_worker(request)
    monkeypatch.setattr(auth.id_token,'verify_oauth2_token',lambda *args: {'email':'worker@example.test','email_verified':True,'aud':settings.APP_ORIGIN})
    verify_worker(request)

def test_mcp_security_accepts_configured_hosts_and_rejects_other_run_apps():
    from mcp.server.transport_security import TransportSecurityMiddleware
    from app.mcp.server import transport_security
    origins=['https://candidate---city-rag-backend-dev-wvswpuk2tq-de.a.run.app']
    guard=TransportSecurityMiddleware(transport_security(origins))
    assert guard._validate_host('candidate---city-rag-backend-dev-wvswpuk2tq-de.a.run.app')
    assert not guard._validate_host('unrelated.run.app')
