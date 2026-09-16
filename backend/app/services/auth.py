import time
import hashlib
import secrets
from contextvars import ContextVar
from dataclasses import dataclass
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

    @property
    def admin(self):
        return self.email.lower() in {s.lower() for s in settings.ADMIN_EMAILS}

    @property
    def editor(self):
        return self.admin or self.email.lower() in {s.lower() for s in settings.EDITOR_EMAILS}

current_user: ContextVar[User | None] = ContextVar('current_user', default=None)


def require_user() -> User:
    user = current_user.get()
    if user is None:
        raise HTTPException(401, 'Sign in with Google to continue')
    return user


def require_editor() -> User:
    user = require_user()
    if not user.editor:
        raise HTTPException(403, 'Document editor role required')
    return user


def allowed_user(user: User) -> User:
    if settings.LOGIN_ALLOWED_EMAILS and user.email.lower() not in {email.lower() for email in settings.LOGIN_ALLOWED_EMAILS}:
        raise HTTPException(403, 'This account is not enabled for this workspace')
    return user


def verify_google(credential: str) -> User:
    if not settings.GOOGLE_OAUTH_CLIENT_ID:
        raise HTTPException(503, 'Google Sign-In is not configured')
    try:
        info = id_token.verify_oauth2_token(credential, GoogleRequest(), settings.GOOGLE_OAUTH_CLIENT_ID)
        if not info.get('email_verified') or not info.get('sub'):
            raise ValueError('Unverified identity')
        user = User(info['sub'], info['email'].lower())
    except Exception:
        raise HTTPException(401, 'Invalid or expired Google credential') from None
    return allowed_user(user)


def authenticate(request: Request) -> User | None:
    authorization = request.headers.get('authorization', '')
    if authorization.startswith('Bearer cgm_'):
        if not (request.url.path == '/mcp' or request.url.path.startswith('/mcp/')):
            raise HTTPException(401, 'This credential is scoped to MCP')
        from app.services import store
        with store.session() as db:
            saved = db.get(store.MCPToken, hashlib.sha256(authorization[7:].encode()).hexdigest())
            if not saved or saved.expires_at <= time.time():
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
        raise HTTPException(401, 'Session expired') from None


def check_origin(request: Request):
    if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'} and not request.headers.get('authorization','').startswith('Bearer '):
        if request.headers.get('origin') not in settings.ALLOWED_ORIGINS:
            raise HTTPException(403, 'Untrusted request origin')

router = APIRouter(prefix='/api/auth')

class LoginRequest(BaseModel):
    credential: str = Field(min_length=1, max_length=10000)

@router.get('/config')
def config():
    return {'client_id': settings.GOOGLE_OAUTH_CLIENT_ID}

@router.post('/login')
def login(body: LoginRequest, request: Request, response: Response):
    check_origin(request)
    if len(settings.AUTH_SESSION_SECRET) < 32:
        raise HTTPException(503, 'Session signing secret is not configured')
    user = verify_google(body.credential)
    now = int(time.time())
    token = jwt.encode(dict(sub=user.id, email=user.email, iss='city-governance', aud='city-governance',
                            iat=now, exp=now + settings.AUTH_SESSION_SECONDS),
                       settings.AUTH_SESSION_SECRET, algorithm='HS256')
    response.set_cookie('governance_session', token, httponly=True, secure=settings.ENVIRONMENT != 'development' or request.url.scheme == 'https',
                        samesite='strict', max_age=settings.AUTH_SESSION_SECONDS, path='/')
    return dict(email=user.email, editor=user.editor, admin=user.admin)

@router.get('/me')
def me():
    user = require_user()
    return dict(email=user.email, editor=user.editor, admin=user.admin)

@router.post('/logout')
def logout(request: Request, response: Response):
    check_origin(request)
    response.delete_cookie('governance_session', path='/')
    return {'success': True}

@router.post('/mcp-token')
def create_mcp_token(response: Response):
    """Explicit personal credential, one hour, current roles, never stored in plaintext."""
    from app.services import store
    from sqlalchemy import delete
    user = require_user()
    value = 'cgm_' + secrets.token_urlsafe(40)
    expiry = time.time() + min(settings.AUTH_SESSION_SECONDS, 3600)
    with store.session() as db:
        db.execute(delete(store.MCPToken).where(store.MCPToken.owner == user.id))
        db.add(store.MCPToken(digest=hashlib.sha256(value.encode()).hexdigest(), owner=user.id,
                             email=user.email, expires_at=expiry))
        db.commit()
    response.headers['Cache-Control'] = 'no-store'
    return {'token': value, 'expires_at': expiry}

@router.delete('/mcp-token')
def revoke_mcp_token():
    from app.services import store
    from sqlalchemy import delete
    user = require_user()
    with store.session() as db:
        db.execute(delete(store.MCPToken).where(store.MCPToken.owner == user.id))
        db.commit()
    return {'revoked': True}
