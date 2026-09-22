# 需求規格的實作核對紀錄

整理日期：2026-09-22。原始碼基準：`22f6882` 與本次工作目錄可見內容。1.0 版僅整理規格；1.1 版依使用者要求，將產品的單次文件發布上限同步擴充為 3,000 段。未修改部署設定；既有未追蹤的 `backend/scripts/cleanup_byo_resources.py` 不屬本次範圍。

主文件為 [需求規格書](requirements-specification.md)。此紀錄供維護者追溯依據，不是需求書的技術附件或特定平台採購要求。以下路徑均相對於專案根目錄。

|需求|主要實作依據|核對事項|
|---|---|---|
|01 至 06|`web/src/App.tsx`；`backend/app/services/context.py`；`backend/app/pipelines/vertex_search.py`|無固定城市、有限歷史、來源引用、錯誤處理；網頁重載清除對話|
|07 至 08|`web/src/lib/languages.ts`；`backend/app/services/languages.py`；`backend/app/models/schema.py`；`backend/app/mcp/server.py`|六種介面、九種內容語言；網頁來源語言預設空清單；外部工具可指定來源語言|
|09 至 11|`web/src/components/SourceReader.tsx`；`backend/app/services/documents.py`；`backend/app/services/jobs.py`；`backend/app/mcp/server.py`|網頁引用段落翻譯；外部工具全文翻譯；可擷取文字、版本、OCR 限制及 TXT 下載|
|12 至 16|`backend/app/services/documents.py`；`backend/app/api/routes.py`；`backend/app/api/workspace.py`；`web/src/components/Library.tsx`|支援格式、不可覆寫原始檔、段落整理、活動時間、舊工具整理與分類建議|
|17 至 21|`web/src/components/ChunkDraftEditor.tsx`；`web/src/components/Library.tsx`；`web/src/App.tsx`；`backend/app/services/chunks.py`|編輯、合併、拆分、重切、草稿、diff、衝突與同帳號重新登入|
|22 至 26|`backend/app/services/chunks.py`；`backend/app/services/jobs.py`；`docs/chunk-as-document.md`|逐段 Search 核對後發布、前版保留、清理與回復；不以本地預覽或匯入結束冒充搜尋就緒|
|27 至 30|`web/src/components/ArtifactPanel.tsx`；`web/src/components/SlideDraftEditor.tsx`；`backend/app/models/artifacts.py`；`backend/app/services/jobs.py`；`backend/app/services/slide_authoring.py`；`backend/app/services/renderers.py`|重新讀取原始擷取證據、草稿確認、PDF、PPTX、SVG/PNG；統計資料驗證|
|31|`web/src/components/GoogleSlidesExport.tsx`；`web/src/lib/google-slides.ts`|現有 Google Slides 串接；需求正文用中性名稱，不宣稱任意供應商均已相容|
|32 至 36|`backend/app/services/jobs.py`；`backend/app/services/dispatch.py`；`backend/app/services/auth.py`；`backend/app/mcp/server.py`；`web/src/components/MCPAccess.tsx`|背景任務、本人存取、到期、三次重試、短效個人連線及撤銷；非自動 OAuth 登入|
|37 至 40|`backend/app/services/auth.py`；`backend/app/services/auth_middleware.py`；`backend/app/services/documents.py`；`backend/app/api/workspace.py`；`backend/app/services/jobs.py`|登入名單與角色；私人、shared、readers；管理者無任意其他使用者 job 存取；下載核對原始版本|
|41|`web/src/components/Library.tsx`；`web/src/App.tsx`；`web/src/index.css`；`infra/cloudbuild.yaml`；`infra/verify_deployment.py`|錯誤與窄螢幕行為、固定服務入口及驗證後切換；本次未做真機 RWD 或雲端驗收|
|第 10 章|`backend/app/core/config.py`；`backend/app/models/artifacts.py`；`backend/app/services/documents.py`；`backend/app/services/chunks.py`；`backend/app/services/jobs.py`|程式預設值與硬上限分開描述；不得視為正式容量或服務時限|
|第 11 章|`docs/verification.md`；`TODO.md`；上述程式|既有驗證紀錄按日期閱讀；翻譯人工驗收仍有未完成項目|

## 技術概念如何改寫

- RAG：先找有權閱讀的相關文件，再依內容回答並附引用，對應需求 02、04、09。
- Vertex AI：以資料搜尋、人工智慧協助回答及背景處理能力描述，不寫供應商綁定條件。
- Chunking：依原文段落整理、可合併拆分及對照修正，對應需求 14、17、18。
- Embedding：以「意思相近也能找得到」描述使用需求，對應需求 03、08。現行採服務代管搜尋；專案並沒有自行呼叫 embedding 模型或使用自建向量資料表的正式流程，故不添加此類建置要求。
- Reindex：發布後更新可查詢內容、核對完整性、保留前版與回復，對應需求 22 至 26。

## 重要範圍區別

1. 使用者已確認不要指定特定平台；主文件沿用中性登入與線上簡報描述，但明確要求替代服務另驗收，沒有宣稱現有程式已可任意替換供應商。
2. 主網頁只提供 passage 翻譯；document 全文模式存在於服務及 MCP。來源語言篩選亦未提供主網頁控制。
3. 文件 sharing 服務支援 readers，但 Library 只提供 shared 勾選，沒有指定讀者名單編輯 UI。
4. 工作區主流程用 paragraph baseline，預設 1,500 字元；舊清理預覽使用 500/80，不能混為正式段落發布規格。
5. 主文件成果下載的版本要求指原始來源版本。jobs.inputs 使用 original_hash 及原始擷取，不將人工 chunk 草稿視為產出證據；SourceReader 對 chunk 引用另核對 published_version。
6. docs/verification.md 早期 BYO 搜尋失敗紀錄已由 2026-09-17 標準 Chunk-as-Document 紀錄取代，不能將早期未通過當成目前實作缺失。反之，舊成功紀錄也不等於本次已重測正式環境。
7. 保存 24 小時針對產出任務，不擴張成原始文件、草稿及發布紀錄的刪除政策。

## 本次檢查界線

1.0 版已查閱上述程式與專案文件，未重跑產品測試。1.1 版新增 3,000／3,001 段發布邊界及 3,000 段分頁核對測試，並執行相關後端測試、前端測試與建置。雲端搜尋回應使用隔離模擬，不能視為正式環境已驗證 3,000 段發布。

兩版均未重新連線正式環境、未改變任何線上權限或發布狀態。交付前另檢查規格編號、平台名稱與術語排除、Word 與 PDF 內容一致性及所有頁面排版。
