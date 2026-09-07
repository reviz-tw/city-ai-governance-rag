# 全球城市 AI 治理顧問系統 (Global City AI Governance Advisor)

基於 **Google Cloud (Vertex AI Search + Cloud Storage + Cloud Run)** 與 **Topos 模式輕量級 React 前端** 構建的城市 AI 政策研究與訪談知識庫顧問平台。

---

## 系統架構

```
[ 使用者瀏覽器 (React + Vite + Tailwind: Topos Edition) ]
                    │
                    ▼ (POST /api/chat/stream 雙向 SSE 串流問答)
[ FastAPI 後端 (city-rag-backend-dev) - Cloud Run (0 Idle Cost) ]
      ├─ 1. /api/chat/stream (Vertex AI Search 檢索 ➜ Gemini 串流問答 ➜ 文獻出處引用)
      ├─ 2. /api/topics (台北市 4 大 AI 治理焦點專題與關鍵爭點矩陣)
      ├─ 3. /api/documents/list (22 份政策報告與首長/業務訪談影音清單)
      └─ 4. 直接託管 React SPA 靜態檔案與 Admin 管理端 (/admin)
                    │
                    ▼
[ Google Cloud: Vertex AI Search Data Store + GCS Document Store ]
```

---

## 專案結構

```
city-ai-governance-rag/
├── web/                             # Topos 風格輕量級顧問前端 (React + Vite + Tailwind)
│   ├── src/
│   │   ├── components/              # Header, TopicSelector, CruxCard, ChatView
│   │   ├── types.ts                 # 專題、爭點、訊息與文獻型別定義
│   │   └── App.tsx                  # 顧問問答、文獻清單與爭點矩陣導航
│   ├── package.json
│   └── vite.config.ts
├── backend/                         # FastAPI + Vertex AI Search + FastMCP 後端
│   ├── app/
│   │   ├── api/routes.py            # 串流問答、專題與文獻 API
│   │   ├── pipelines/vertex_search.py # Vertex AI Search 語意檢索與 Gemini 串流生成
│   │   ├── mcp/server.py            # FastMCP SSE 協議端點 (/mcp/sse)
│   │   └── static/                  # Admin 管理後台與切片檢視工具 (/admin)
│   ├── Dockerfile
│   └── requirements.txt
├── Dockerfile                       # 多階段 Docker 建置 (Node 前端編譯 + Python 後端)
└── infra/
    └── cloudbuild.yaml              # GCP Cloud Build 自動部署至 Cloud Run
```

---

## 本機快速啟動

```bash
# 1. 啟動前端開發伺服器
cd web
npm install
npm run dev

# 2. 啟動後端伺服器 (另一視窗)
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

---

## GCP 自動部署 (CI/CD)

本專案已設定 GCP Cloud Build Trigger (`city-rag-backend-dev-trigger`)，只要 push 至 `main` 分支即可自動完成多階段容器編譯並部署至 Cloud Run。

