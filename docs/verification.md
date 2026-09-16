# 驗證紀錄（2026-09-16～17）

本紀錄區分實際觀測與尚未通過的驗收。測試資料包含隔離合成政策及已授權研究文件，沒有把模型能翻譯視為搜尋能跨語命中的證據。

## 已通過

- 本機 pytest：61 項；前端 Node 契約測試：3 項；TypeScript／Vite build 成功。涵蓋語言優先序、短句 fallback、來源篩選、有限 context、SSE Unicode 逐 byte 分界、截斷錯誤、文件／任務隔離、版本變更、取消／重試／TTL、數字引用、草稿／實際發布差別、取消競爭、MCP 憑證範圍／撤銷與 worker 身分。包含索引延後續查、原 operation 重用、任務結束不殘留 pending、掃描頁拒絕翻譯、Word 表格順序及不支援語言在寫入儲存前拒絕等回歸測試。
- Linux 容器：最終 Cloud Build `a972317a-07ce-4bd4-92d2-785e3a9bd880` SUCCESS，2026-09-16 15:19:08 UTC 完成；build log 確認 61 項後端測試通過及前端建置成功。映像標籤 `todo-20260916-r7`，依賴層重用前版快取；前一個完整建置 `0b4f6553-210d-4047-8f75-c090abb24b16` 亦 SUCCESS。
- Google OAuth Client 已建立。localhost 以 hcchien@gmail.com 真實 Google 登入取得 HTTP 200，介面顯示本人帳號且沒有編輯／發布權限。Google Identity Services callback 僅傳 ID token；未讀取或保存 client secret。
- Vertex global 真實呼叫：`gemini-3.7-flash` 與 `gemini-3.5-flash-lite` 皆成功。繁中 RAG 有 `[1]` 原文引用；英文 SSE 有實際增量片段並完成。PDF、可編輯 PPTX、LibreOffice 預覽 PDF 及統計圖生成成功。
- 字型與排版：實際產出 PDF／PPTX 轉 PDF 的繁中字形已檢視；中英混排與流程箭頭有固定渲染檢查。不是僅檢查模型輸出字串。
- 隔離 data store `city-governance-chunk-validation-20260916-v2`：啟用 chunking／layout parser 後，BYO JSON 匯入可列出真實 chunks；同一文件第二版合併後只讀回新版 merged chunk，舊 a/b chunks 不再列出。

- Cloud Run revision `city-rag-backend-dev-00038-hev` 已就緒，[candidate 標籤](https://candidate---city-rag-backend-dev-wvswpuk2tq-de.a.run.app)可用；舊 revision `00031-dpk` 仍占 100% 流量。候選版真實 Gmail 登入 HTTP 200，hcchien@reviz.tw 管理員亦已完成真實 Google 登入且可見新增／修正文件入口，匿名文件 API 401。重新載入網頁後仍能從「我的產出」找到已完成的真實政策報告。
- Cloud Scheduler 實際 OIDC 清理呼叫 HTTP 200（14:09:57 UTC）。PostgreSQL 持久化 schema 已成功初始化；Secret Manager version 1、私有 bucket、Cloud Tasks queue、Scheduler 已建立。

- 實際 Cloud Tasks 四類合成任務均完成，PDF／PPTX＋預覽 PDF／SVG＋PNG／全文翻譯已授權下載；另一個測試身分讀取文件與任務均為 404。測試 session 與資料專門建立，未擷取真人 Google 憑證。真人 GIS 登入另有前述獨立驗證。
- 以過期合成任務驗證：下載立即 404，實際 Scheduler 執行後資料庫紀錄與 GCS 物件均刪除。
- 真實 200 段、19,005 字政策文件曾因模型回傳每節超過 12 個引用而失敗；schema 改為保留上限語意說明後，同文件輸出 5 節通過本機實際模型驗證。雲端重試、瀏覽器草稿確認及 PDF 渲染均已完成，保留該真實報告供使用者下載。
- r5 候選 MCP 實測：initialize、12 個工具清單、授權文件讀取成功；以中文問題及明確日文回答語言取得 `gemini-3.7-flash` 的回答與 3 個原文來源。撤銷個人 MCP 憑證後回傳 401。這不等於跨語搜尋已通過。

- 固定原文片段的模型比較已完成：繁中／英文／日文 4 題、2 個模型，共 8 次呼叫，引用、否定、例外條件、資料不足、延遲及成本門檻通過；詳見 [模型比較](model-benchmark.md)。Search 召回不在這組固定證據測試範圍。

- 調整語言範圍後，中文 PDF／6 頁可編輯 PPTX 與預覽 PDF／SVG／PNG、日文全文文字譯本皆已在 Cloud Tasks 完成並下載；實際檢視中文 PDF、投影片正文及圖表；最終 r7 重新渲染、下載後確認中文全形標點顯示正常。日文譯文保留 2026、20 件、禁止自動核准與使用 AI 前須評估隱私風險。投影片草稿曾將「需要審查」誤寫成「已完成審查」，已在確認前依原文修正，不能省略內容審閱。
- 延後續作使用同一份已完成的日文合成譯文，Cloud Tasks 排程 20 秒後處理；任務由 queued 回到 completed，未新增模型生成。
- 已移除的語言選項在候選頁面不再顯示，回答／來源語言／翻譯 API 均拒絕該代碼並回傳 422。
- 驗證結束後已刪除合成測試文件、任務、儲存物件與測試憑證；保留本機驗證產出及使用者的真實政策報告。本機測試伺服器與 Cloud SQL Proxy 已停止。

## 尚未通過

- 自訂 chunks 的 Search：隔離 store／engine 查詢仍回空結果，semanticState=DISABLED。三份英／繁中／日合成文件的 operation `import-documents-11482740810101247929` 在 14:30:38 UTC 回報 done=true、failureCount=3，錯誤 code 14：文件已匯入且分段完成，但尚未完成索引。15:14:22 UTC 再查仍回傳 0 筆、semanticState=DISABLED；英／繁中／日查詢均尚無命中；不能把 operation 結束或 chunks 可讀當成 Search 成功。因此跨語 Search 不算通過，也尚未開啟新文件發布。
- 完整政策文件的翻譯人工驗收。已有結構／數字保護與部分內容抽驗，不能宣稱所有真實內容品質已獲人工認可。

## Commit／push 後複驗

- 實作 commit `bd2f49841206c93f1cc1b3d1622cf6b302da91cb` 已依使用者要求推送至 `origin/main`，推送後核對遠端 SHA 相同。[GitHub Actions](https://github.com/reviz-tw/city-ai-governance-rag/actions/runs/35115888614) 於 2026-09-16 15:32:36 UTC 完成且成功；實際 log 為後端 61 項、前端 3 項測試通過及 Vite build 成功。
- 同次複驗重新呼叫 Vertex global 的 `gemini-3.7-flash` 與 `gemini-3.5-flash-lite`，最小測試提示均成功取得模型回覆。
- 15:32:10 UTC，原資料庫 `city-governance-datastore` 以「人工智慧」查詢，`totalSize=20`，要求的 5 筆結果均有回傳，`semanticState=ENABLED`。這確認既有搜尋可用，但不代表新的自訂 chunks 已可搜尋。
- 同時讀取隔離測試資料庫及 engine：chunking 設定存在，engine 為 Enterprise 且連接正確的 v2 store；英文、中文、英文來源 filter、直接 store／engine 路徑及 DOCUMENTS／CHUNKS 模式皆回空結果，沒有 API 權限錯誤。
- 三份多語文件的 `indexStatus.pendingMessage` 仍為分段完成、索引處理中；英文字塊可直接列出。較早的 `synthetic-chunk-document` 雖有 `indexTime=2026-09-16T12:44:26Z` 且只列出新版 `merged` chunk，以其原文關鍵字或 `*` 搜尋仍無結果。因此單憑 import 完成、indexTime 或 chunks.list 不能通過驗收。
- `semanticState=DISABLED` 僅表示該次回應沒有啟用語意搜尋；[官方欄位定義](https://docs.cloud.google.com/generative-ai-app-builder/docs/reference/rest/v1alpha/SearchResponse#SemanticState) 未提供原因。現有證據尚無法斷定是索引就緒時間、BYO chunks 服務問題或其他設定所致，也不能推論購買 LLM add-on 就能修復。此次未重新匯入、修改計費設定或切換 Cloud Run 流量，`CHUNK_INDEX_ENABLED=false` 及未完成驗收維持原狀。

## 流量切換

2026-09-16 15:39:55 UTC，使用者明確要求切換流量後，Cloud Run 已確認 `city-rag-backend-dev-00040-tod` 接收 100% 流量，Ready／RoutesReady 均為 True。切換前確認其映像 digest `sha256:26b5b2b609d1e12cc8e1b882fafc0c7432290d05d80db2503246966cbf7182ea`、環境變數、服務帳號與資源設定皆與已驗證的 `00038-hev` 相同。

[原網址](https://city-rag-backend-dev-wvswpuk2tq-de.a.run.app)的 `/api/health`、`/api/auth/config` 及新版 JS／CSS 皆回傳 200；匿名 `/api/library` 與 `/api/auth/me` 回傳 401。瀏覽器已透過真實 Google 登入進入新版研究工作區，顯示 `hcchien@reviz.tw`、文件庫、我的產出與 MCP 入口。自訂 chunks 搜尋仍關閉，未完成項目沒有因流量切換而標記通過。

## 外部依據

- [Google 基本身分登入的測試名單例外](https://support.google.com/cloud/answer/15549945?hl=en)：只要求基本身分時，使用者不必在 Google 測試名單內；網站另行限制兩個已核准帳號。
- [Search parsing/chunking](https://docs.cloud.google.com/generative-ai-app-builder/docs/parse-chunk-documents)：BYO chunks 為 Preview；須驗證實際 chunks 與 Search，不能以 console 匯入紀錄替代。
- [模型生命週期](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/model-versions)：原 TODO 對 2.5 的敘述過早；其退役日為 2026-10-20。這次移除舊 SDK／1.5 fallback，使用目標專案實測的新模型。
- [Search 支援語言](https://docs.cloud.google.com/generative-ai-app-builder/docs/languages-locales)：支援包含繁中、英文與日文，但官方建議依語言分開 data store；支援語言清單不保證任意跨語查詢的召回率。待隔離索引可檢索後，以明確來源語言和文件 ID 驗證三個跨語案例。

## 2026-09-17：標準 Chunk-as-Document

此節取代上述 BYO Preview 的發布方案；先前失敗紀錄保留為歷史。實作與設定見 [Chunk-as-Document](chunk-as-document.md)。

- 本機 70 項後端測試、5 項前端測試及 TypeScript／Vite build 通過。新增覆蓋標準 Document manifest、不可變物件寫入、Search 完整分頁、內容 hash 核對、schema 傳播延遲、ACL 前置篩選、舊來源排除、清理失敗不回退新版，以及後續版本發布後仍重試舊清理。
- 標準 store `city-governance-chunk-validation-20260916` 沒有開啟自動 chunking。4 筆標準 TXT Document 的匯入 operation `import-documents-12897766788439098219` 於 2026-09-16 16:38:58 UTC 建立，16:40:18 UTC 完成，4/4 成功。
- 以中文政策問題限定英文／日文來源，命中兩種原文，`semanticState=ENABLED`；英文問題限定 zh-TW 亦命中繁中原文，無關午餐測試文件不在結果內。空查詢能列舉指定版本，供發布完整性核對；它回傳 `semanticState=DISABLED` 不等於有意義的研究問題不能做語意搜尋。
- 第一個候選建置 `98df70cd-c207-4e39-bc6b-91555ae31280` SUCCESS，映像 `sha256:113ef1ea60e3a67fc1e15f9d3b09b91a1693db36553b44066263dd90ee653559`。真實 hcchien@reviz.tw GIS 登入成功，文件庫的兩頁合成 PDF 可合併、拆分及儲存草稿；頁 1／頁 2 refs 保留，草稿修訂遞增，已發布版本保持 v1。
- 另以隔離測試 session 操作與 Admin UI 相同的 HTTP API，建立英文 PDF、日文 TXT、繁中 TXT 三份 private 原始文件；另一個 reader 讀取回傳 404。這種 API fixture 不當成真實 GIS 登入測試。
- 三份文件均由既有 Cloud Tasks 實際執行發布，完成時分別核對 2／1／1 個 Chunk Documents；首次發布前維持 published_version=0。英文 PDF v2 將兩片合併並修正文句，在等待期間保持 v1，Search 核對成功後切至 v2；舊 v1 的兩筆遠端 Documents 已確認 GET 404，新 v2 Document 存在。
- 第三版回復成功，內容等於 v1，原始 PDF／TXT SHA256 保持不變；v1／v2 遠端 Documents 皆已 GET 404，只有目前版本存在。reader 原文存取先為 404，明確加入 readers 後可讀，但發布仍為 403。
- FE SSE 及 MCP 問答均以中文問題取得 en v3／ja v1，並以繁中完成回答；英文 PDF 引用包含 c1、頁 1 與原始文件連結。另直接核對 MCP Search 的 Unicode 全文與 canonical chunk 完全相同；source_languages=[en] 僅回傳英文，指定 en／ja 時兩者皆命中。驗收腳本強制使用 SSE 規定的 UTF-8，避免 requests 的 text 預設解碼造成亂碼。
- 最終建置 `ea965c1b-deb2-4ba5-83bd-6cdf72f793e5` SUCCESS，映像 `sha256:1cd63085057b6bc4b538bcbdf85789756bbe3cb51da71639e5c806f8f85029bd`，revision `city-rag-backend-dev-00044-tuj` Ready。2026-09-16 17:09:04 UTC 已切換 100% 主網址流量，保留同版 candidate worker 標籤。

- 切換後主網址 MCP 再次通過 en／ja 跨語及 en 單語篩選；健康檢查與文件庫入口 HTTP 200，匿名文件庫 HTTP 401。本次合成測試 Documents、Publication／DraftRevision／Job 記錄、MCP 憑證與對應 GCS 物件已清除。
- 追加切片 Diff 修正：即使合併／拆分後完整文字相同，仍顯示 Chunk 邊界、順序與原文範圍差異；隔離來源快照 70 項後端測試通過。

- 隔離來源建置 `ba8092c2-cbdf-4bc9-a6aa-8af62b5ed325` SUCCESS，70 項後端測試，digest `sha256:5e227aff6d5fa4d4dcacbf72ba13d165e64c374e1a2b4f96a691fdb2c543c346`。以正常 Google 登入在候選版檢視既有文件 Diff，確認切片邊界／原文範圍可見，確認發布按鈕可用，未修改或發布該研究文件。
- 實作 commit `61584f6e7087851181bf3af2a0e23cf61a4413a7` 已推送；[GitHub CI](https://github.com/reviz-tw/city-ai-governance-rag/actions/runs/35127373067) success。相同 commit 的區域自動建置 `e94d3930-0c95-4c9e-a414-11ec07d9659e` 產生 `00047-pol`，digest 與隔離建置完全一致；追加修正已切換 100% 流量至此 revision。
