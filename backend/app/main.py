import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.db import init_db
from app.api.routes import router as api_router
from app.mcp.server import mcp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("city-governance-rag")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("正在初始化 全球城市 AI 治理 RAG & MCP 伺服器...")
    init_db()
    yield
    logger.info("伺服器關閉。")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# CORS Middleware (支援 LibreChat 與 Web 前端存取)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 掛載 REST API
app.include_router(api_router)

# 掛載 FastMCP SSE 端點 (支援 LibreChat / Claude / Cursor 透過 MCP Protocol 對接)
# FastMCP 提供 sse_app() 可直接作為子應用掛載
try:
    mcp_app = mcp.sse_app()
    app.mount("/mcp", mcp_app)
    logger.info("MCP SSE 端點已成功掛載於 /mcp/sse")
except Exception as e:
    logger.warning(f"掛載 MCP SSE 端點時發生提示 (仍可透過內部調用): {e}")

# 掛載 Admin UI 靜態檔案
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/admin", StaticFiles(directory=static_dir, html=True), name="static")

@app.get("/")
async def root():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {
        "message": "Global City AI Governance RAG & MCP Hub is running.",
        "admin_ui": "/admin",
        "docs": "/docs",
        "mcp_endpoint": "/mcp/sse"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=True)
