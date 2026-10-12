# Docling 文件解析與切片

Docling 2.134.0／docling-core 2.100.0 在獨立 worker 執行；網站不安裝 PyTorch 或 OCR 模型。`HybridChunker` 依文件元素、標題、表格結構切片，再以 token 上限拆分或合併。使用 cl100k_base tokenizer 作為明確的切片預算（不是 Vertex embedding tokenizer 的精確替代），預設 768 tokens。原文引用為文件元素範圍，PDF 額外保留頁碼與 bounding box；不宣稱每個拆片有精確的字元位置。

## 啟用

1. 將文件處理服務以 `infra/cloudbuild.docling.yaml` 部署到既有網站所在的 GCP project。服務保持 private、並僅授予網站實際 service account `roles/run.invoker`。初始配置 2 CPU／4 GiB、concurrency 1，後續依實測調整。
2. 部署含 pipeline 轉接的網站版本，將 `DOCLING_SERVICE_URL` 設為 worker URL。網站以 OIDC 身分呼叫，不使用第三方文件服務。
3. 本機操作可設定 `DOCLING_PYTHON` 為獨立環境的 Python，使用同一份 converter。依 `backend/docling_worker/requirements.txt` 安裝依賴；HF_HOME、TORCH_HOME、TIKTOKEN_CACHE_DIR 應指向可寫的模型快取。模型／tokenizer 首次下載不包含文件上傳。

配置服務時，新匯入文件使用 Docling 結果；未配置時保留原匯入流程並顯示未啟用。明確要求 Docling 但服務缺失、解析失敗或部分轉換時會報錯，不會悄悄改用字數切片後標記為 Docling。

## 未 review 文件批次重跑

`backend/scripts/rechunk_unreviewed.py --cloud` 先產生名單；加 `--apply` 才進行解析與草稿更新。`--workers 3` 可並行處理，`DOCLING_PERSISTENT=1` 可讓本機解析器重用模型；`--only DOCUMENT_ID` 可限制文件，`--report PATH` 保存逐件結果。雲端使用操作人目前的 hcchien@reviz.tw IAM 授權、核對既有 tdf-ocf 資料庫 instance，憑證僅在記憶體。遇到過期授權須先重新登入。

任何人的人工 review 紀錄（含舊版本）均保護該文件；pending 發布、原始 hash 改變或 draft revision 改變也會阻止更新。產生的候選稿有解析版本、tokenizer、切片上限、來源 blocks、原始 hash、base revision 與操作人紀錄。

僅原始自動草稿、或仍等同已知原始切片結果的發布草稿，批次可自動套用。已有人工內容或切片安排則保留原草稿，另存候選稿供編輯者預覽。套用前再次鎖定文件並檢查 review／版本。

套用會保存原草稿快照、附加新的不可變來源 blocks（舊 block IDs 保留）、再保存新草稿 revision。原始檔案、hash、review、發布版本與搜尋索引均不變。重新執行相同版本與參數時，已套用且未變更的 Docling 草稿會跳過。

管理介面可背景產生候選稿、查看原文、預覽與套用。儲存後仍須檢查差異，再明確送出索引；本次重跑不自動發布或標記已 review。舊 DOC 由 Docling 透過隔離的 LibreOffice 轉換後解析，原檔與 hash 不變；純文字依原有段落建立 Docling 文件元素再切片。新文件上傳仍限制 20 MiB；既有原始文件可處理至 256 MiB，大型雲端原檔由 private worker 直接讀取指定來源 bucket 的 documents/ 或既有 artifacts bucket 的 managed-originals/ 路徑，避免 Cloud Run HTTP request 大小限制。其他不支援格式或解析錯誤會記錄失敗，不能假裝成功。

## 部署後背景重跑

`--cloud --enqueue` 將尚未完成的文件交給部署後的 Cloud Tasks／Docling pipeline；已更新文件會跳過，可重用的候選稿會直接套用或保留人工草稿。批次任務由管理員建立，解析完成後僅對未 review 且未人工修改的草稿自動套用，保護規則與本機重跑相同。

`DOCLING_TASKS_QUEUE` 可指定獨立的文件處理 queue，建議 maxConcurrentDispatches=2，配合處理器最多兩個 instance；不佔滿原有投影片與 PDF 輸出 queue。任務及結果保存在既有 jobs 表，可從管理介面的「我的產出」查看。排程報告保存 document ID／job ID，供後續核對完成數與失敗原因。

處理器滿載（429）或暫時不可用（5xx）時，背景工作保留原始檔與草稿並記錄失敗，預設不重試。解析錯誤不會標記成功。

批次重跑建議 maxConcurrentDispatches=1，以免大量 PDF 同時耗盡處理器容量。容量不足與連線中斷會延後重試（最多 144 次，最長間隔 10 分鐘）；rechunk 工作紀錄保留 7 天。線上 runtime service account 必須在指定 Docling queue 具有 roles/cloudtasks.enqueuer，才能建立延後任務。

PDF backend 明確指定 PyPdfiumDocumentBackend（pypdfium2），解析結果與候選稿記錄 pdf_backend；PDFium 重新解析不重用舊 backend 的候選稿。OCR、表格辨識與 HybridChunker 設定保持一致。

2026-10-12：新 rechunk 工作預設不自動重試。成功／失敗與 document ID 保存於 jobs；解析採隔離子程序，預設單次 3600 秒（60 分鐘），逾時或取消會終止程序群組；Cloud Run HTTP 的 3600 秒也保留。呼叫端等待 3660 秒，工作 lease 3900 秒。Cloud Tasks 限期 1800 秒，只啟動 city-docling-batch Cloud Run Job，立即返回；Job 逐份執行 queued rechunk 工作，資料庫 advisory lock 避免多次啟動造成並行批次。Job max-retries=0，不挑選 failed 工作；整批 Job 上限 24 小時。日誌包含 request_id、來源 hash、PDF 頁數、轉換／切段開始完成、每 30 秒執行 heartbeat、失敗原因與耗時；不記錄全文。

2026-10-12：遠端解析改為 application/x-ndjson 串流。每 15 秒回傳執行訊息，避免無資料的 HTTP 連線達到 Cloud Run 對外閒置 20 分鐘上限。解析仍為 3600 秒，呼叫端整體限期 3660 秒；socket 無資料 90 秒視為斷線。串流結束但沒有 completed 結果不得標記成功。呼叫端會關閉回應，服務端在斷線時取消解析 task，終止程序群組並等待清理後才釋放鎖；docling_process_stopped 在失敗紀錄之前輸出。串流失敗記錄不自動重試。
