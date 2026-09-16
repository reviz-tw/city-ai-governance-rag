# Google 登入設定

2026-09-16 已在 `tdf-ocf` 建立 **城市 AI 治理研究** 品牌與 **City AI Governance Web** 網頁應用程式用戶端。

公開 Client ID：`59297909591-86jaj8lhabibrl9gvs04ime6p2sbmtvm.apps.googleusercontent.com`

已授權的 JavaScript 來源：

- `https://city-rag-backend-dev-wvswpuk2tq-de.a.run.app`
- `http://localhost:8080`
- `http://localhost:5173`
- `https://candidate---city-rag-backend-dev-wvswpuk2tq-de.a.run.app`（dev 候選版）

目前採 Google Identity Services 的 JavaScript callback，後端驗證 ID token；不使用授權碼交換，因此沒有 redirect URI，也不需要 client secret。未下載或保存 Google 產生的 client secret。

目標對象採「外部／測試」，測試帳號為 `hcchien@gmail.com`、`hcchien@reviz.tw`。後端另以 `LOGIN_ALLOWED_EMAILS` 限制相同帳號，實際限制可登入帳號。Google 的基本身分登入（openid/email/profile）適用測試名單例外，因此不需逐一加入 Google 名單；詳見 https://support.google.com/cloud/answer/15549945?hl=en 。所有 cookie 與 MCP bearer 登入均套用名單。`ADMIN_EMAILS` 決定文件編輯與發布權限，登入本身不授予管理員身分。

只使用基本登入身分與電子郵件，不要求 Gmail 郵件、Google Drive 或其他 API 存取權。原始文件及使用者明確選定的有限對話內容會傳送至專案設定的 Gemini global endpoint；對話不永久存入 session。

本機使用 `.env.example` 的公開設定，另從環境注入隨機 `AUTH_SESSION_SECRET`。Cloud Run 使用 Secret Manager 注入簽章金鑰與 PostgreSQL 連線字串，並設定持久化 artifact bucket 及 Cloud Tasks。2026-09-16 已在 localhost 及 dev 候選版以 `hcchien@gmail.com` 完成真實 Google 登入；候選版重新載入後仍可存取本人已完成的產出。`hcchien@reviz.tw` 亦已完成候選版真人登入，文件庫顯示新增文件及修正草稿入口；Gmail 帳號為閱讀者。

設定入口：[OAuth 用戶端](https://console.cloud.google.com/auth/clients?project=tdf-ocf)、[測試對象](https://console.cloud.google.com/auth/audience?project=tdf-ocf)。Google 提示設定可能需要數分鐘至數小時生效。
