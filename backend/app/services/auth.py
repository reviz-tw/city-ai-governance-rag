import time
import hashlib
import secrets
from contextvars import ContextVar
from dataclasses import dataclass, replace
import jwt
from fastapi import APIRouter, HTTPException, Request, Response
from google.oauth2 import id_token
from google.auth.transport.requests import Request as GoogleRequest
from pydantic import BaseModel, Field
from app.core.config import settings

@dataclass(frozen=True)
class User:
    id: str
    email: str
    role: str | None = None

    @property
    def admin(self):
        from app.services.accounts import role_for
        return (self.role if self.role is not None else role_for(self.email)) == 'admin'

    @property
    def editor(self):
        from app.services.accounts import role_for
        return (self.role if self.role is not None else role_for(self.email)) in {'admin', 'editor'}

current_user: ContextVar[User | None] = ContextVar('current_user', default=None)


def require_user() -> User:
    user = current_user.get()
    if user is None:
        raise HTTPException(401, 'Sign in with Google to continue')
    return user


def require_editor() -> User:
    user = require_user()
    if not user.editor:
        from app.services import audit
        audit.record('auth.editor.denied', actor=user.email, status='denied')
        raise HTTPException(403, 'Document editor role required')
    return user


def allowed_user(user: User) -> User:
    from app.services.accounts import role_for
    role = role_for(user.email)
    if role is None:
        from app.services import audit
        audit.record('auth.access.denied', actor=user.email, target=user.email, status='denied')
        raise HTTPException(403, 'This account is not enabled for this workspace')
    # A request-local snapshot, never a login-lifetime permission cache.
    return replace(user, role=role)


def verify_google(credential: str) -> User:
    if not settings.GOOGLE_OAUTH_CLIENT_ID:
        raise HTTPException(503, 'Google Sign-In is not configured')
    try:
        info = id_token.verify_oauth2_token(credential, GoogleRequest(), settings.GOOGLE_OAUTH_CLIENT_ID)
        if not info.get('email_verified') or not info.get('sub'):
            raise ValueError('Unverified identity')
        user = User(info['sub'], info['email'].lower())
    except Exception:
        from app.services import audit
        audit.record('auth.login.failed', actor='anonymous', status='failed', details={'reason': 'invalid_google_credential'})
        raise HTTPException(401, 'Invalid or expired Google credential') from None
    return allowed_user(user)


def authenticate(request: Request) -> User | None:
    from app.services import audit
    authorization = request.headers.get('authorization', '')
    if authorization.startswith('Bearer cgm_'):
        if not (request.url.path == '/mcp' or request.url.path.startswith('/mcp/')):
            audit.record('auth.token.rejected', status='denied', details={'reason': 'mcp_token_outside_mcp_scope'}, request=request)
            raise HTTPException(401, 'This credential is scoped to MCP')
        from app.services import store
        with store.session() as db:
            saved = db.get(store.MCPToken, hashlib.sha256(authorization[7:].encode()).hexdigest())
            if not saved or saved.expires_at <= time.time():
                audit.record('auth.token.rejected', status='denied', details={'reason': 'mcp_token_expired_or_revoked'}, request=request)
                raise HTTPException(401, 'MCP credential expired or revoked')
            return allowed_user(User(saved.owner, saved.email))
    if authorization.startswith('Bearer '):
        return verify_google(authorization[7:])
    cookie = request.cookies.get('governance_session')
    if not cookie:
        return None
    try:
        data = jwt.decode(cookie, settings.AUTH_SESSION_SECRET, algorithms=['HS256'],
                          audience='city-governance', issuer='city-governance',
                          options={'require': ['exp', 'iat', 'sub', 'email']})
        return allowed_user(User(data['sub'], data['email']))
    except jwt.PyJWTError:
        audit.record('auth.token.rejected', status='denied', details={'reason': 'session_expired_or_invalid'}, request=request)
        raise HTTPException(401, 'Session expired') from None


def check_origin(request: Request):
    if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'} and not request.headers.get('authorization','').startswith('Bearer '):
        origin = request.headers.get('origin')
        if origin not in settings.ALLOWED_ORIGINS:
            from app.services import audit
            audit.record('auth.origin.rejected', status='denied', details={'origin': origin or ''}, request=request)
            raise HTTPException(403, 'Untrusted request origin')

router = APIRouter(prefix='/api/auth')

class LoginRequest(BaseModel):
    credential: str = Field(min_length=1, max_length=10000)

@router.get('/config')
def config():
    return {'client_id': settings.GOOGLE_OAUTH_CLIENT_ID}

@router.post('/login')
def login(body: LoginRequest, request: Request, response: Response):
    from app.services import accounts, audit
    check_origin(request)
    if len(settings.AUTH_SESSION_SECRET) < 32:
        raise HTTPException(503, 'Session signing secret is not configured')
    user = verify_google(body.credential)
    accounts.touch_login(user.email)
    now = int(time.time())
    token = jwt.encode(dict(sub=user.id, email=user.email, iss='city-governance', aud='city-governance',
                            iat=now, exp=now + settings.AUTH_SESSION_SECONDS),
                       settings.AUTH_SESSION_SECRET, algorithm='HS256')
    response.set_cookie('governance_session', token, httponly=True, secure=settings.ENVIRONMENT != 'development' or request.url.scheme == 'https',
                        samesite='strict', max_age=settings.AUTH_SESSION_SECONDS, path='/')
    audit.record(
        'auth.login.succeeded',
        actor=user.email,
        target=user.email,
        details={'role': user.role or ('admin' if user.admin else 'editor' if user.editor else 'reader'), 'session_seconds': settings.AUTH_SESSION_SECONDS},
        request=request,
    )
    return dict(email=user.email, editor=user.editor, admin=user.admin)

@router.get('/me')
def me():
    user = require_user()
    return dict(email=user.email, editor=user.editor, admin=user.admin)

@router.post('/logout')
def logout(request: Request, response: Response):
    from app.services import audit
    check_origin(request)
    response.delete_cookie('governance_session', path='/')
    audit.record('auth.logout', request=request)
    return {'success': True}

@router.post('/mcp-token')
def create_mcp_token(response: Response):
    """Explicit personal credential, one hour, current roles, never stored in plaintext."""
    from app.services import audit, store
    from sqlalchemy import delete
    user = require_user()
    value = 'cgm_' + secrets.token_urlsafe(40)
    digest = hashlib.sha256(value.encode()).hexdigest()
    expiry = time.time() + min(settings.AUTH_SESSION_SECONDS, 3600)
    with store.session() as db:
        db.execute(delete(store.MCPToken).where(store.MCPToken.owner == user.id))
        db.add(store.MCPToken(digest=digest, owner=user.id,
                             email=user.email, expires_at=expiry))
        db.commit()
    response.headers['Cache-Control'] = 'no-store'
    audit.record(
        'auth.mcp_token.created',
        actor=user.email,
        target=user.email,
        details={'digest_prefix': digest[:12], 'expires_at': round(expiry, 3)},
    )
    return {'token': value, 'expires_at': expiry}

@router.delete('/mcp-token')
def revoke_mcp_token():
    from app.services import audit, store
    from sqlalchemy import delete
    user = require_user()
    with store.session() as db:
        db.execute(delete(store.MCPToken).where(store.MCPToken.owner == user.id))
        db.commit()
    audit.record('auth.mcp_token.revoked', actor=user.email, target=user.email)
    return {'revoked': True}
