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

處理器滿載（429）或暫時不可用（5xx）時，背景工作會保留原始檔與草稿，延後重試；退避由 60 秒逐步增加至 600 秒，最多 12 次，且每次仍核對帳號、來源 hash、草稿版本及 review 狀態。解析錯誤不會標記成功。

批次重跑建議 maxConcurrentDispatches=1，以免大量 PDF 同時耗盡處理器容量。容量不足與連線中斷會延後重試（最多 144 次，最長間隔 10 分鐘）；rechunk 工作紀錄保留 7 天。線上 runtime service account 必須在指定 Docling queue 具有 roles/cloudtasks.enqueuer，才能建立延後任務。
