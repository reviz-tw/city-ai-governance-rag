import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from starlette.types import Receive, Scope, Send

from app.core.config import settings
from app.api.routes import router as api_router
from app.mcp.server import mcp
from app.services.auth import router as auth_router
from app.services.auth_middleware import AuthenticationMiddleware
from app.api.workspace import router as workspace_router
from app.services import store
import threading
from app.worker import serve

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("city-governance-vertex-rag")

# 初始化 FastMCP 服務 (同時支援傳統 SSE 與現代 Streamable HTTP)
try:
    sse_app = mcp.sse_app()
    streamable_app = mcp.streamable_http_app()
    session_manager = mcp.session_manager
    logger.info("FastMCP SSE 與 Streamable HTTP 初始化完成")
except Exception as e:
    logger.warning(f"FastMCP 初始化提示: {e}")
    sse_app = None
    session_manager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.ENVIRONMENT == 'production':
        if not (settings.GOOGLE_OAUTH_CLIENT_ID and len(settings.AUTH_SESSION_SECRET)>=32
                and settings.DATABASE_URL.startswith('postgresql') and settings.ARTIFACT_GCS_BUCKET
                and settings.CLOUD_TASKS_QUEUE and settings.WORKER_SERVICE_ACCOUNT):
            raise RuntimeError('Production requires Google Sign-In, persistent database/storage and Cloud Tasks configuration')
    store.initialize()
    stop = threading.Event()
    worker = None
    if settings.WORKER_ENABLED and not settings.CLOUD_TASKS_QUEUE:
        worker = threading.Thread(target=serve, args=(stop,), daemon=True)
        worker.start()
    try:
        if session_manager is not None:
            async with session_manager.run():
                yield
        else:
            yield
    finally:
        stop.set()
        if worker:
            worker.join(timeout=2)


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 掛載 REST API
app.include_router(api_router)
app.include_router(auth_router)
app.include_router(workspace_router)

class UnifiedMCPApp:
    """
    整合式 MCP ASGI 路由器：
    - GET /mcp/sse: 傳統 SSE 串流
    - POST /mcp/messages/...: 傳統 SSE 訊息發送
    - POST /mcp, POST /mcp/sse, GET /mcp: 現代 Streamable HTTP (供 Claude Custom Connector, Cursor 等)
    """
    def __init__(self, sse_asgi, streamable_mgr):
        self.sse_asgi = sse_asgi
        self.streamable_mgr = streamable_mgr

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            if self.sse_asgi:
                await self.sse_asgi(scope, receive, send)
            return

        method = scope.get("method", "GET").upper()
        path = scope.get("path", "")

        # 處理 CORS preflight OPTIONS 請求
        if method == "OPTIONS":
            from starlette.responses import Response
            res = Response(
                status_code=200,
                headers={
                    "access-control-allow-origin": "*",
                    "access-control-allow-methods": "GET, POST, OPTIONS, DELETE, HEAD",
                    "access-control-allow-headers": "*",
                }
            )
            await res(scope, receive, send)
            return

        # 1. 傳統 SSE GET 端點: GET /mcp/sse
        # 供傳統 SSE 用戶端建立串流
        if method == "GET" and (path.endswith("/sse") or path.endswith("/sse/")):
            if self.sse_asgi:
                # 確保 scope 中的 path 與 root_path 正確相容於 sse_app (Starlette)
                child_scope = dict(scope)
                child_scope["root_path"] = "/mcp"
                child_scope["path"] = "/sse"
                await self.sse_asgi(child_scope, receive, send)
                return

        # 2. 傳統 SSE 訊息發送端點: POST /mcp/messages/...
        # 發送 JSON-RPC 訊息到現有 SSE 會話
        if "/messages" in path:
            if self.sse_asgi:
                child_scope = dict(scope)
                child_scope["root_path"] = "/mcp"
                idx = path.find("/messages")
                child_scope["path"] = path[idx:]
                await self.sse_asgi(child_scope, receive, send)
                return

        # 3. 現代 Streamable HTTP (Claude Custom Connector, Cursor 等)
        # 正規化 Accept 標頭以符合 MCP SDK 要求
        headers = list(scope.get("headers", []))
        has_accept = False
        new_headers = []
        for k, v in headers:
            if k.lower() == b"accept":
                has_accept = True
                val = v.decode("latin1", errors="ignore")
                if "*/*" in val or "text/event-stream" not in val or "application/json" not in val:
                    new_headers.append((k, b"application/json, text/event-stream"))
                else:
                    new_headers.append((k, v))
            else:
                new_headers.append((k, v))
        if not has_accept:
            new_headers.append((b"accept", b"application/json, text/event-stream"))
        
        req_scope = dict(scope)
        req_scope["headers"] = new_headers

        if self.streamable_mgr:
            await self.streamable_mgr.handle_request(req_scope, receive, send)
        elif self.sse_asgi:
            await self.sse_asgi(req_scope, receive, send)
        else:
            raise HTTPException(status_code=503, detail="MCP service unavailable")

class MCPRoutingMiddleware:
    """
    攔截所有 /mcp 與 /mcp/* 請求，確保無結尾斜線的 /mcp 能正確直達 MCP 路由器，
    避免被 FastAPI 的 SPA 萬用路由捕捉或回傳 405 Method Not Allowed。
    """
    def __init__(self, app, mcp_app):
        self.app = app
        self.mcp_app = mcp_app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            path = scope.get("path", "")
            if path == "/mcp" or path.startswith("/mcp/"):
                await self.mcp_app(scope, receive, send)
                return
        await self.app(scope, receive, send)

# 掛載統一 MCP 路由器與中介軟體
mcp_unified_app = UnifiedMCPApp(sse_app, session_manager)
app.add_middleware(MCPRoutingMiddleware, mcp_app=mcp_unified_app)
app.add_middleware(AuthenticationMiddleware)
app.mount("/mcp", mcp_unified_app)
logger.info("MCP 整合端點已成功掛載於 /mcp (支援 Streamable HTTP 及 SSE)")

# 掛載 Admin UI 靜態檔案
admin_static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(admin_static_dir):
    app.mount("/admin/tools", StaticFiles(directory=admin_static_dir, html=True), name="admin_tools")

# 尋找前端 React SPA 編譯目錄 (支援 /app/web_dist, /app/static/dist, 或 ../web/dist)
possible_web_dirs = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "web", "dist")),
    os.path.join(os.path.dirname(__file__), "web_dist"),
    os.path.join(os.path.dirname(__file__), "static", "dist"),
    "/app/web_dist",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "web", "dist")),
]
web_dist_dir = None
for d in possible_web_dirs:
    if os.path.exists(d) and os.path.exists(os.path.join(d, "index.html")):
        web_dist_dir = d
        break

if web_dist_dir:
    logger.info(f"成功找到 React 前端編譯目錄: {web_dist_dir}")
    assets_dir = os.path.join(web_dist_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/admin")
    @app.get("/admin/")
    async def admin_ui():
        return FileResponse(os.path.join(web_dist_dir, "index.html"), headers={"Cache-Control": "no-cache"})

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # 排除 API, MCP, Admin 與文件路徑
        if full_path == "mcp" or full_path.startswith(("api/", "internal/", "mcp/", "admin", "docs", "openapi.json", "redoc")):
            raise HTTPException(status_code=404, detail="Not Found")
            
        file_path = os.path.join(web_dist_dir, full_path)
        from pathlib import Path
        if not Path(file_path).resolve().is_relative_to(Path(web_dist_dir).resolve()):
            raise HTTPException(status_code=404, detail='Not Found')
        if full_path and os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(web_dist_dir, "index.html"))
else:
    logger.info("未偵測到 React 前端編譯目錄，使用內建預設首頁。")
    @app.get("/")
    async def root():
        index_file = os.path.join(admin_static_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {
            "message": "Global City AI Governance Vertex AI Search & MCP Hub is running.",
            "admin_ui": "/admin",
            "docs": "/docs",
            "mcp_streamable_endpoint": "/mcp",
            "mcp_sse_endpoint": "/mcp/sse"
        }

@app.post('/internal/jobs/{job_id}')
def execute_job(job_id: str, request: Request):
    from google.oauth2 import id_token
    from google.auth.transport.requests import Request as GoogleRequest
    from app.services import jobs
    from sqlalchemy import select
    import time
    verify_worker(request)
    with store.session() as db:
        job=db.scalar(select(store.Job).where(store.Job.id==job_id).with_for_update())
        if not job or job.expires_at<=time.time():
            return {'status':'expired'}
        if job.status=='running':
            if job.lease_until>time.time():
                raise HTTPException(503,'Task already running; retry after lease expiry')
            job.status='render_queued' if job.draft and job.kind not in {'translation','index'} else 'queued'
            db.commit()
    jobs.run(job_id)
    jobs.purge_expired()
    return {'status':'handled'}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run('app.main:app', host='0.0.0.0', port=8080, reload=True)


def verify_worker(request: Request):
    from google.oauth2 import id_token
    from google.auth.transport.requests import Request as GoogleRequest
    if not settings.WORKER_SERVICE_ACCOUNT:
        raise HTTPException(503, 'Cloud worker is not configured')
    try:
        credential=request.headers.get('authorization','').removeprefix('Bearer ')
        claims=id_token.verify_oauth2_token(credential,GoogleRequest(),None)
        if claims.get("aud") not in [settings.APP_ORIGIN, *settings.WORKER_LEGACY_ORIGINS]:
            raise ValueError("Wrong worker audience")
        if claims.get('email') != settings.WORKER_SERVICE_ACCOUNT or not claims.get('email_verified'):
            raise ValueError('Wrong worker identity')
    except Exception:
        raise HTTPException(401,'Invalid worker credential') from None


@app.post('/internal/cleanup')
def cleanup(request: Request):
    verify_worker(request)
    from app.services import jobs
    jobs.purge_expired()
    from app.services import chunks
    chunks.cleanup_pending()
    return {'status': 'cleaned'}
