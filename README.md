# 全球城市 AI 治理研究 (Global City AI Governance) RAG & MCP Hub

本專案為「**全球城市 AI 治理研究**」的多語顧問 RAG 系統核心庫，整合 **Haystack 2.x**、**PostgreSQL (pgvector)**、**MCP Server**、**Haystack Admin UI** 以及 **LibreChat** 前端。

---

## 系統架構

- **多語向量模型 (Multilingual Embedding)**: Google Vertex AI `text-embedding-004` (768 維度，跨 100+ 語言對齊)。
- **生成問答模型 (LLM)**: Google Gemini 1.5 Pro / Flash (可隨時擴充切換為 Claude 3.5 / GPT-4o)。
- **向量資料庫 (Vector DB)**: GCP Cloud SQL (PostgreSQL 16 + `pgvector`) 最小方案 (`db-f1-micro`)。
- **協定介面**: 
  - **MCP (Model Context Protocol)**: 提供 SSE 端點 `/mcp/sse` 供 LibreChat、Claude Desktop、Cursor 等 AI Agent 呼叫。
  - **REST API**: 提供 Swagger API (`/docs`) 供前端與外部系統整合。
- **管理後台 (Admin UI)**:
  - 支援 PDF / Word / TXT / Markdown 檔案上傳。
  - LLM 智能預處理與自動標註治理 Metadata（城市、國家、領域、文件類型、年份、摘要）。
  - 切片 (Chunking) 參數設定與分佈預覽。
  - 多語 RAG 檢索生成實驗室。

---

## 專案結構

```
city-ai-governance-rag/
├── backend/                         # Haystack 2.x + FastAPI + MCP Server
│   ├── app/
│   │   ├── core/                    # 設定檔 (GCP Project, DB連線, Model配置)
│   │   ├── pipelines/               # Haystack 索引、檢索與清理流水線
│   │   ├── mcp/                     # Model Context Protocol (MCP) 伺服器
│   │   ├── api/                     # REST API 端點
│   │   ├── models/                  # Pydantic 資料模型與 Metadata Schema
│   │   └── static/                  # Admin UI 靜態前端頁面
│   ├── Dockerfile
│   └── requirements.txt
│
├── librechat/                       # LibreChat 設定檔
│   └── librechat.yaml               # 掛載 Gemini 與 MCP 知識庫工具
│
└── infra/                           # GCP 部署腳本與 Cloud Build
    ├── create_cloud_sql.sh          # 建立 Cloud SQL PostgreSQL 腳本
    └── cloudbuild.yaml              # 自動化建置部署至 Cloud Run
```

---

## 本機快速啟動

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 啟動後端與 Admin UI
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```
開啟瀏覽器訪問：
- **Admin UI**: [http://localhost:8080/admin](http://localhost:8080/admin)
- **Swagger API Docs**: [http://localhost:8080/docs](http://localhost:8080/docs)
- **MCP SSE 端點**: `http://localhost:8080/mcp/sse`

---

## 部署至 GCP Cloud Run

```bash
gcloud builds submit --project=tdf-ocf --config=infra/cloudbuild.yaml
```
