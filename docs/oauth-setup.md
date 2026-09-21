# Google 登入設定

2026-09-16 已在 `tdf-ocf` 建立 **城市 AI 治理研究** 品牌與 **City AI Governance Web** 網頁應用程式用戶端。

公開 Client ID：`59297909591-86jaj8lhabibrl9gvs04ime6p2sbmtvm.apps.googleusercontent.com`

已授權的 JavaScript 來源：

- `https://city-rag-backend-dev-wvswpuk2tq-de.a.run.app`
- `http://localhost:8080`
- `http://localhost:5173`
- `https://candidate---city-rag-backend-dev-wvswpuk2tq-de.a.run.app`（dev 候選版）
- `https://city-rag-backend-dev-59297909591.asia-east1.run.app`（Cloud Run Console 顯示的網址，2026-09-17 核對已登記）

網站來源必須同時存在於 Google OAuth 的 JavaScript 來源及後端 `ALLOWED_ORIGINS`。漏掉前者會出現 Google `origin_mismatch`，漏掉後者會在 `/api/auth/login` 回傳 `403 Untrusted request origin`。2026-09-17 已將 Console 網址補入 `infra/env.dev.yaml` 與 `.env.example`；Cloud Run 的兩種網址皆須保留，不能只設定其中一個。來源只填 scheme、hostname 與必要的 port，不含路徑或末尾斜線。

目前採 Google Identity Services 的 JavaScript callback，後端驗證 ID token；不使用授權碼交換，因此沒有 redirect URI，也不需要 client secret。未下載或保存 Google 產生的 client secret。

目標對象採「外部／測試」，已核對的 Google 測試帳號為 `hcchien@gmail.com`、`hcchien@reviz.tw`。後端另以 `LOGIN_ALLOWED_EMAILS` 實際限制可登入帳號；2026-09-21 設定的名單為：

- `hcchien@gmail.com`
- `hcchien@reviz.tw`
- `azoezoe@reviz.tw`
- `azoezoe@gmail.com`

Google 的基本身分登入（openid/email/profile）適用測試名單例外，因此不需逐一加入 Google 名單；詳見 https://support.google.com/cloud/answer/15549945?hl=en 。所有 cookie 與 MCP bearer 登入均套用後端名單。`ADMIN_EMAILS`、`EDITOR_EMAILS` 決定文件編輯與發布角色，登入本身不授予編輯權限。`hcchien@reviz.tw`、`azoezoe@reviz.tw`、`azoezoe@gmail.com` 設為管理員，可編輯文件切片、儲存草稿與送出索引；`hcchien@gmail.com` 為閱讀者。

初次登入只使用基本身分與電子郵件，不要求 Drive 權限。原始文件及使用者明確選定的有限對話內容會傳送至專案設定的 Gemini global endpoint；對話不永久存入 session。

## 選用：另存 Google Slides

使用同一個 OAuth Web client。Google Identity Services token model 在使用者點擊匯出時才要求 `https://www.googleapis.com/auth/drive.file`；不用 client secret、授權碼或 refresh token。此範圍僅涵蓋本應用建立或由使用者選取的檔案，不要求完整 `drive`／`presentations` 範圍。短期 access token 只存在瀏覽器記憶體，直接呼叫 Google Drive REST API，不經本站後端。

部署前須啟用 `drive.googleapis.com`，並在 OAuth「資料存取權」宣告 `drive.file`。2026-09-17 已啟用 Drive API，並核對「目標對象」確實包含 `hcchien@gmail.com`、`hcchien@reviz.tw`；額外的 Drive 授權不適用僅基本登入的測試名單例外。兩個 `azoezoe` 帳號的 Google 測試對象設定尚未核對，後端登入白名單不代表已啟用 Google Slides 匯出。網站仍採外部／測試狀態，尚未開放一般帳號。

完成投影片後，前端重新下載已通過本人及來源 ACL／版本檢查的 PPTX，以 Drive resumable upload 及 `application/vnd.google-apps.presentation` 轉成原生簡報。`about.user.emailAddress` 必須符合目前登入者；`about.importFormats` 必須支援 PowerPoint 轉換。以任務版本的雜湊寫入 `appProperties.cityRagExport`，重試時先搜尋副本，同來源分頁以 Web Locks 避免同時上傳；不自動重試結果不明的寫入。不同裝置同時匯出仍可能建立兩份，沒有宣稱跨裝置 exactly-once。

開啟連結後由使用者在 Google Slides 編輯與分享；本站不修改 Drive 分享權限，刪除任務或 24 小時到期不刪除 Google 副本。若使用者拒絕授權、帳號不符或 Google 不支援轉換，仍可下載 PPTX 與 PDF。

參考：[GIS token model](https://developers.google.com/identity/oauth2/web/guides/use-token-model)、[Drive 檔案轉換](https://developers.google.com/workspace/drive/api/guides/manage-uploads)、[drive.file 最小範圍](https://developers.google.com/workspace/drive/api/guides/api-specific-auth)。

本機使用 `.env.example` 的公開設定，另從環境注入隨機 `AUTH_SESSION_SECRET`。Cloud Run 使用 Secret Manager 注入簽章金鑰與 PostgreSQL 連線字串，並設定持久化 artifact bucket 及 Cloud Tasks。2026-09-16 已在 localhost 及 dev 候選版以 `hcchien@gmail.com` 完成真實 Google 登入；候選版重新載入後仍可存取本人已完成的產出。`hcchien@reviz.tw` 亦已完成候選版真人登入，文件庫顯示新增文件及修正草稿入口；Gmail 帳號為閱讀者。

設定入口：[OAuth 用戶端](https://console.cloud.google.com/auth/clients?project=tdf-ocf)、[測試對象](https://console.cloud.google.com/auth/audience?project=tdf-ocf)。Google 提示設定可能需要數分鐘至數小時生效。
