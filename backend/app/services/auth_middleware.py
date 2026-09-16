import re
from fastapi import HTTPException, Request
from starlette.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from app.services.auth import authenticate, check_origin, current_user

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
        public = path in {'/api/auth/config','/api/auth/login','/api/auth/logout','/api/health'}
        try:
            user = None if public else await run_in_threadpool(authenticate, request)
            if not public and user is None:
                raise HTTPException(401, 'Sign in with Google to continue')
            check_origin(request)
            if '/mcp/messages' in path:
                session_id = request.query_params.get('session_id', '')
                if not user or self.sse_owners.get(session_id) != user.id:
                    raise HTTPException(403, 'MCP session does not belong to this user')
        except HTTPException as exc:
            return await JSONResponse({'detail':exc.detail}, status_code=exc.status_code)(scope, receive, send)
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
