# 全球城市 AI 治理研究

React／FastAPI 研究工作區，以 Google 登入、Vertex AI Search 原文檢索、Gemini 問答與共用背景產出服務，提供引用閱讀、段落／全文翻譯、SVG／PNG 圖表、PDF 報告及可編輯 PPTX。前端與 MCP 使用同一套權限、研究 context 和產出服務。

目前實作與雲端驗收分開追蹤：[TODO](TODO.md)、[實作計畫](docs/implementation-plan.md)、[驗證紀錄](docs/verification.md)。未通過實際 Search 命中驗收前，自訂切片發布保持停用。

## 本機執行

需要 Python 3.12、Node.js 20、LibreOffice Impress，以及 CJK 與拉丁字型。Dockerfile 包含部署所需系統相依。

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
cp .env.example .env
cd web
npm ci
npm run build
cd ..
PYTHONPATH=backend .venv/bin/python backend/scripts/dev_server.py
```

開啟 http://localhost:8080 。開發啟動器在程序內產生隨機 session 簽章金鑰；重新啟動會使舊登入失效。SQLite 與本機檔案僅供開發，Cloud Run 使用 PostgreSQL、私有 GCS 與 Cloud Tasks。呼叫 Google Cloud 需有效 ADC；不能以一般 gcloud 登入推論 ADC 已就緒。正式設定見 [Google 登入](docs/oauth-setup.md) 與 [部署方案](docs/deployment-plan.md)。

## 登入與文件權限

只取得 Google 基本身分，不要求 Gmail 郵件或 Drive 權限。`LOGIN_ALLOWED_EMAILS` 限制可登入帳號；空名單代表允許所有通過 Google 身分驗證的帳號，**目前 dev 限定兩個已核准帳號**。`ADMIN_EMAILS`、`EDITOR_EMAILS` 決定編輯角色。新文件預設私人，只有擁有者／管理員可修改；分享名單另行管理讀取權。歷史 `documents/` 公開資料集按原有公開範圍登錄，與新私人文件分開處理。

原始檔不可由清理／切片草稿覆寫。每份來源保留雜湊、段落與頁碼；人工切片修改另存版本、差異與操作者。儲存草稿不會發布，每個 Chunk 以標準 Document 匯入，並經 Search 核對全部切片後才切換發布版本。預估等待 10～30 分鐘（依 Vertex 索引狀態），期間維持前版。詳見 [Chunk-as-Document](docs/chunk-as-document.md)。舊 Admin 的本地切片視圖明確標為預覽。

## 語言與研究 context

- `interface_language` 控制介面。提供繁中、英、日、法、西、俄六種既有介面語言；不支援的舊介面設定回退英文。新增工作區面板目前以繁中說明為主。
- `response_language` 控制回答；`auto` 依明確指令、固定偏好、問題語言、近期主要語言、介面 fallback 解析。內容支援繁中、簡中、英、日、法、西、俄、韓、德。
- `source_languages` 僅篩選原文，預設空陣列搜尋全部語言，不由回答語言隱含限制。
- 翻譯使用獨立 `target_language`；不把譯本當成新原始證據或自動加入索引。

前端傳入有限近期歷史與滾動摘要。MCP 只使用 host 明確提供的 `research_context`，不讀取桌面對話。更改城市會開始新的研究範圍；重新開始、登出、重新載入頁面會清除前端對話。對話不永久保存為伺服器 session；使用者選定的產出輸入則隨背景任務暫存至到期。

模型輸入採保守 UTF-8 byte 預算（不是精確 tokenizer 計量）；預設總輸入 16,000、歷史 3,000、證據 9,000，並預留模型輸出。搜尋結果重新取得、去重、限制長度。無來源時不補寫政策事實。

## 產出與翻譯

明確選擇回答／對話與 source IDs 後才建立任務，重新載入有權存取的原始證據。PDF／PPTX／圖表先提供草稿，確認後渲染；投影片頁數依修改後內容重新計算。統計圖的數字、單位、期間與引用必須對應原文，不能由質性文字捏造數據。PPTX 可編輯，PDF 用於預覽；沒有宣稱已整合 Google Slides 原生寫入。

翻譯保留段落、可擷取表格、數字、來源版本與定位，並排閱讀標示 AI 輔助、非官方譯本。掃描文件需先 OCR；複雜 PDF 擷取會提示限制。全文代表選定擷取文字全部完成，不代表圖片、註腳或原版面完整重製。長文分批、可續作；部分成功不標為完整。

每人每小時預設 10 個產出任務，證據上限 100,000 字元。任務預設保存 24 小時，下載再驗證原文權限與版本；使用者可取消、重試、刪除。Cloud Tasks 處理不依賴瀏覽器存活，定期清理移除到期任務與檔案；GCS `jobs/` 一日 lifecycle 為額外清理機制，實際刪除可能延後，下載權限在到期時立即終止。一般 logs 不保存完整原文、對話或譯文。

## MCP

Streamable HTTP 端點為 `/mcp`，也保留 `/mcp/sse`。在研究網站 Google 登入後，從「MCP」面板建立**個人一小時憑證**，設定 `Authorization: Bearer <token>`。資料庫只存雜湊，新建會撤銷前一個，面板可隨時撤銷；每次請求都套用當前登入名單與角色。憑證不共用、不寫入版本控制、不貼入模型對話。

每位使用者提供自己的憑證，沒有全域共用管理員 token。下載路徑需本人在網站登入，知道 ID 不會取得權限。只有支援自訂 Authorization header 的 host 能使用這條連線；未實作自動 OAuth discovery／PKCE，不能宣稱任意 MCP host 都可自動登入。

工具包含搜尋、問答、原文閱讀、清理預覽、圖表／報告／投影片草稿、翻譯，以及任務狀態／確認／取消／重試／刪除。建立任務與下載不會隱含讀取 host 的全部歷史。

## 測試與部署

```bash
PYTHONPATH=backend .venv/bin/pytest -q backend/tests
cd web
npm test
npm run build
```

Python 相依以 `requirements.in` 為輸入，`requirements.txt` 鎖定全部直接／間接版本；使用 uv 0.8.22、Python 3.12 universal compile 更新。`.github/workflows/test.yml` 與容器建置執行測試。

`infra/cloudbuild.verify.yaml` 僅建置驗證。`infra/cloudbuild.yaml` 建置、推送並部署 `candidate` 標籤，`--no-traffic` 保留既有流量；不是 push main 後自動切換服務。新模型為 Vertex `gemini-3.7-flash`／清理 `gemini-3.5-flash-lite`、`global`，沒有跨認證來源的隱性 fallback。持續計費資源、切換及回復方式見 [部署方案](docs/deployment-plan.md)。
