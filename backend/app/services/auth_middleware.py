import re
from app.services.rag_timing import span
from fastapi import HTTPException, Request
from starlette.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from app.services import audit
from app.services.auth import authenticate, check_origin, current_user, User

class AuthenticationMiddleware:
    def __init__(self, app):
        self.app = app
        self.sse_owners = {}

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        request = Request(scope)
        path = request.url.path
        if request.method == 'OPTIONS' or not (path.startswith('/api/') or path.startswith('/mcp')):
            return await self.app(scope, receive, send)
        ctx_token = audit.request_context.set({
            'source_ip': audit.client_ip(request),
            'path': audit.request_path(request),
        })
        public = path in {'/api/auth/config','/api/auth/login','/api/auth/logout','/api/health'}
        try:
            with span('authentication'):
                user = None if public else await run_in_threadpool(authenticate, request)
            if not public and user is None:
                await run_in_threadpool(
                    audit.record,
                    'auth.unauthenticated.rejected',
                    actor='anonymous',
                    target=path,
                    status='denied',
                    request=request,
                )
                raise HTTPException(401, 'Sign in with Google to continue')
            check_origin(request)
            if '/mcp/messages' in path:
                session_id = request.query_params.get('session_id', '')
                if not user or self.sse_owners.get(session_id) != user.id:
                    await run_in_threadpool(
                        audit.record,
                        'auth.mcp_session.rejected',
                        actor=user.email if user else 'anonymous',
                        target=session_id,
                        status='denied',
                        request=request,
                    )
                    raise HTTPException(403, 'MCP session does not belong to this user')
        except HTTPException as exc:
            audit.request_context.reset(ctx_token)
            return await JSONResponse({'detail':exc.detail}, status_code=exc.status_code)(scope, receive, send)
        except Exception:
            audit.request_context.reset(ctx_token)
            raise
        # MCP transports can retain execution context beyond this HTTP request.
        # Keep their live role lookup; Web roles are cached only for one request.
        if user and path.startswith('/mcp'):user=User(user.id,user.email)
        token = current_user.set(user)
        owned_sessions = []
        async def authenticated_send(message):
            if path.rstrip('/') == '/mcp/sse' and request.method == 'GET' and message['type'] == 'http.response.body':
                match = re.search(rb'session_id=([a-zA-Z0-9_-]+)', message.get('body',b''))
                if match and user:
                    session_id = match[1].decode()
                    self.sse_owners[session_id] = user.id
                    owned_sessions.append(session_id)
            await send(message)
        try:
            await self.app(scope, receive, authenticated_send)
        finally:
            for session_id in owned_sessions:
                self.sse_owners.pop(session_id, None)
            current_user.reset(token)
            audit.request_context.reset(ctx_token)
