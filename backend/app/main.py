import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from starlette.types import Receive, Scope, Send

from app.core.config import settings
from app.api.routes import router as api_router
from app.mcp.server import mcp

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
    logger.info("正在初始化 全球城市 AI 治理 Vertex AI Search & MCP 伺服器...")
    if session_manager is not None:
        try:
            async with session_manager.run():
                yield
        except Exception as e:
            logger.error(f"MCP Session Manager lifespan 執行異常: {e}")
            yield
    else:
        yield
    logger.info("伺服器關閉。")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 掛載 REST API
app.include_router(api_router)

class UnifiedMCPApp:
    """
    整合式 MCP ASGI 路由器：
    - GET /mcp/sse: 傳統 SSE 串流 (供 LibreChat 等客戶端)
    - POST /mcp/messages/...: 傳統 SSE 訊息發送 (供 LibreChat 等客戶端)
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

        # 1. 傳統 SSE GET 端點: GET /mcp/sse (LibreChat 等傳統用戶端)
        if method == "GET" and (path == "/sse" or path == "/sse/"):
            if self.sse_asgi:
                await self.sse_asgi(scope, receive, send)
                return

        # 2. 傳統 SSE 訊息發送端點: POST /mcp/messages/...
        if path.startswith("/messages"):
            if self.sse_asgi:
                await self.sse_asgi(scope, receive, send)
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
        scope["headers"] = new_headers

        if self.streamable_mgr:
            await self.streamable_mgr.handle_request(scope, receive, send)
        elif self.sse_asgi:
            await self.sse_asgi(scope, receive, send)
        else:
            raise HTTPException(status_code=503, detail="MCP service unavailable")

# 掛載統一 MCP 路由器於 /mcp
mcp_unified_app = UnifiedMCPApp(sse_app, session_manager)
app.mount("/mcp", mcp_unified_app)
logger.info("MCP 整合端點已成功掛載於 /mcp (支援 Streamable HTTP 及 SSE)")

# 掛載 Admin UI 靜態檔案
admin_static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(admin_static_dir):
    app.mount("/admin", StaticFiles(directory=admin_static_dir, html=True), name="admin_static")

# 尋找前端 React SPA 編譯目錄 (支援 /app/web_dist, /app/static/dist, 或 ../web/dist)
possible_web_dirs = [
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

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # 排除 API, MCP, Admin 與文件路徑
        if full_path == "mcp" or full_path.startswith(("api/", "mcp/", "admin", "docs", "openapi.json", "redoc")):
            raise HTTPException(status_code=404, detail="Not Found")
            
        file_path = os.path.join(web_dist_dir, full_path)
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=True)

