# 人工切片發布：Chunk-as-Document

2026-09-17。採用 Vertex AI Search v1 標準 Document 匯入，取代巢狀 BYO chunks；不使用 pgvector 或自行呼叫 embedding 模型。

## 發布與檢索

1. Editor／Admin 上傳原始 PDF、DOCX、TXT 或 Markdown。原始檔存入私有 GCS `managed-originals/{document_id}/{sha256}/...`，保留 SHA256、原始擷取 blocks 與頁碼。既有 `documents/` 來源沿用原連結。
2. 自動切片依段落、斷句及約 1500 字上限處理，合併短段落並保留各原文範圍。短文件可小於 500 字。舊文件可使用「還原自動切片」產生新的 baseline。
3. 來源文件庫並排顯示原文／頁碼及草稿；可以修正文句、合併、拆分、儲存草稿。文字未變更的拆分能縮小 refs；已修正文字無法精確對齊時保留較寬原文範圍，不捏造頁碼。
4. 查看差異後，以當次 revision 與 diff hash 發布。單次發布最多 3,000 個 Chunk；超過上限仍可儲存草稿，但須整理至上限內才可發布。版本快照與背景任務存入 PostgreSQL；每個 Chunk 產生獨立 TXT 及一筆 Document JSONL，寫入時使用 GCS generation 前置條件，拒絕覆寫不同內容。
5. Cloud Tasks 以 `dataSchema: document`、`INCREMENTAL` 匯入。沿用既有佇列；operation 存入資料庫，每 120 秒續查同一個 operation，不因等待而重複匯入。預估約 10～30 分鐘，依 Vertex 佇列與索引狀態而定，並非保證時限。
6. 匯入作業完成後，使用標準 Search 空查詢、publication filter 及分頁核對全部 Document IDs、版本、Chunk IDs、內容 hash。空查詢用於完整性核對，實際跨語語意能力另用有意義的研究問題驗收。新 metadata 尚未完成索引、暫時性服務錯誤會繼續等待。
7. 全部符合後，以同一資料庫交易更新 Publication、Document 發布指標及 Job 完成狀態。等待／失敗／取消期間維持前版；首次發布尚未完成時，草稿不提供給 RAG。
8. 新版生效後刪除前版的遠端 Chunk Documents。失敗顯示 `indexed_cleanup_pending`，每小時清理工作會重試；檢索仍只允許目前發布版本。GCS 版本快照保留，支援稽核與回復。
9. 回復會將上一個可用版本的內容建立為新的遞增版本，重新匯入並核對後才切換。它也需要等待索引，不會立即將資料庫指標指向已刪除的遠端文件。

FE 和 MCP 共用同一個 retrieve。送往 Search 前就依登入身分、文件 ACL、城市、來源語言及目前發布版本限定候選文件；取得結果後再核對版本與權限。回傳資料庫保存的完整切片文字、原始文件 ID／連結、Chunk ID、版本及頁碼，避免以搜尋摘要截短後的文字替代編修內容。已人工發布的來源不再混入舊索引的原文 snippets。

## 設定

- `CHUNK_INDEX_ENABLED=true`
- `CHUNK_DATA_STORE_ID=city-governance-chunk-validation-20260916`：既有隔離驗證 store，使用 digital parser，**未啟用自動 chunking**。保留既有名稱，避免建立重複資源。
- `CHUNK_SEARCH_ENGINE_ID` 留空，使用該 store 的 `default_search`。
- Schema 的 `document_id`、`publication_key`、`chunk_id`、`language`、`city` 必須是 indexable/retrievable 字串；version、頁碼、hash、原文 URI 必須可讀回。Schema 更新也有傳播延遲。
- 既有 `city-governance-datastore` 保留為尚未人工發布的原始文件檢索來源。
- 延續既有 Cloud SQL、GCS 與 `city-governance-jobs`，沒有建立新的發布佇列。

原 pgvector 試驗曾啟用 Cloud SQL `vector` extension 與空的 `chunk_embeddings` 表；新流程不讀寫它們，repo 無 pgvector 相依。試驗資料已清除，沒有把原研究文件移轉進向量表。

## 驗收證據

- 標準 Document probe：4 個獨立 TXT（en、ja、zh-TW、無關干擾項），operation `import-documents-12897766788439098219`，2026-09-16 16:38:58 UTC 建立，16:40:18 UTC 完成，4/4 成功。
- 實際中文提問限定 en／ja，命中英文及日文政策；英文提問限定 zh-TW，命中繁中政策。兩者回應 `semanticState: ENABLED`，無關午餐文件沒有命中。這是該測試的實際結果，不是所有查詢／所有索引必然可用的保證。
- 本機 70 項後端、5 項前端測試通過，前端 TypeScript／Vite build 通過。
- 雲端 Admin API 發布、更新、回復、原文 hash、FE／MCP 引用及流量切換結果另記於 `verification.md`。

官方介面：[GcsSource 標準 Document JSONL](https://docs.cloud.google.com/generative-ai-app-builder/docs/reference/rest/v1/GcsSource)、[metadata filters](https://docs.cloud.google.com/generative-ai-app-builder/docs/filter-search-metadata)、[schema 設定](https://docs.cloud.google.com/generative-ai-app-builder/docs/provide-schema)。
