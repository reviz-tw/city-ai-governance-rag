# Dev 持久化部署與驗收

目前 Cloud Run `city-rag-backend-dev` 的既有流量維持原版本。新程式需要共用 PostgreSQL、受控 GCS 儲存與 Cloud Tasks；不可以把 Cloud Run 的暫存 SQLite 當成持久化資料庫。

## 已核准建立的資源

| 資源 | 具體設定 | 用途 |
|---|---|---|
| Cloud SQL | `city-governance-postgres`，`asia-east1`，PostgreSQL 17，Enterprise `db-f1-micro`，10 GiB SSD，單區、每日備份、禁止自動擴容、開啟刪除保護 | dev 文件版本、授權、任務、速率限制 |
| 資料庫 | `city_governance`，專用應用程式使用者；Cloud SQL Auth Proxy／Cloud Run 連線，不設定公開授權網段 | 持久化記錄 |
| GCS | `tdf-ocf-city-governance-artifacts`，`asia-east1`，uniform access、public access prevention | 原始檔與產出；`jobs/` 前綴的物件保存 1 天 |
| Secret Manager | `city-governance-session`、`city-governance-database-url` | 隨機 session 簽章金鑰及資料庫連線；值不寫入 Git／設定檔／log |
| Cloud Tasks | `city-governance-jobs`，`asia-east1`，同時至多 2 個任務、每秒至多 1 次派送 | 瀏覽器關閉後仍繼續產出；OIDC 認證 worker |
| Worker 身分 | `city-governance-worker@tdf-ocf.iam.gserviceaccount.com` | 僅用於呼叫內部任務與清理端點 |

另以 Cloud Scheduler `city-governance-cleanup` 每小時呼叫精確 worker 身分保護的到期清理端點。GCS 關閉產出 bucket soft-delete，`originals/` 不套用一日清理；原始版本不以 lifecycle 自動刪除。

共用 CPU 規格是 dev 起步配置，不具有 Cloud SQL SLA；正式多人使用前需量測負載並選擇適當規格。Cloud SQL 在無請求時仍產生執行費，另計 SSD、備份及網路；Google 的[官方定價頁](https://cloud.google.com/sql/pricing)需選 Taiwan `asia-east1` 核對。Cloud Run、Cloud Tasks、GCS、Search 及 Gemini 依實際使用另計。

## 權限與連線

Cloud Run runtime 需在指定資源範圍取得：上述兩個 secrets 的讀取權、artifact bucket 的物件管理權、既有文件 bucket 的讀取及受管理索引前綴寫入權、Cloud SQL client、Vertex AI 生成、Discovery Engine 文件索引／搜尋、指定 queue 的 enqueue，以及使用 worker service account 派送 OIDC 任務的權限。Worker 身分僅需服務呼叫權；內部端點另檢查 OIDC audience 與精確 service account email。

外部登入仍限定 `hcchien@gmail.com`、`hcchien@reviz.tw`，管理員僅 `hcchien@reviz.tw`。OAuth Web Client 已建立；詳見 [oauth-setup.md](oauth-setup.md)。

## 部署步驟

1. 使用者已核准上述持續計費 dev 資源；資源與 Secret Manager version 1 已建立，未把 secret 值寫入本機檔案。
2. 核對 `infra/env.dev.yaml` 與兩個 secret 版本。資料庫連線格式為 `postgresql+psycopg://USER:PASSWORD@/city_governance?host=/cloudsql/tdf-ocf:asia-east1:city-governance-postgres`；密碼需 URL encode。
3. 執行 `gcloud builds submit --project tdf-ocf --config infra/cloudbuild.verify.yaml`，從乾淨 Linux 環境建置並執行測試。此檔不 push image、不 deploy。
4. 使用 `infra/cloudbuild.yaml` 建置候選 revision；`--no-traffic --tag=candidate` 保留既有流量。目前 APP_ORIGIN 固定為 candidate 標籤 URL，Cloud Tasks／Scheduler 派送該候選版本，OAuth／CORS 已加入同一來源。切換流量後可保留此 worker 標籤；移動／刪除標籤前必須先處理佇列中的任務與更新 worker URL。
5. 驗證：未登入拒絕 API、兩個帳號登入與角色、跨使用者隔離、Google Gen AI ADC、實際 RAG／SSE／MCP、完整 PDF／PPTX／SVG／PNG／翻譯任務，以及原文授權下載、取消／重試、到期清理。
6. 自訂切片必須先通過實際 Search 命中與跨語驗收，才設定 `CHUNK_INDEX_ENABLED=true`、正式管理用 datastore／engine。僅能列出 chunks 不能視為已可檢索。
7. 全部驗收完成後才切換流量；目前既有 revision `city-rag-backend-dev-00031-dpk` 仍為 100%，候選標籤供登入驗收。首次部署建立資料表；未來 schema 改動需資料庫 migration，不能以 `create_all` 更新既有欄位。

## 回復

先記錄 `gcloud run services describe city-rag-backend-dev --region asia-east1 --project tdf-ocf` 的 serving revision。回復時以 `gcloud run services update-traffic ... --to-revisions=PREVIOUS_REVISION=100` 切回既有 revision；保留資料庫與原始檔供修復。模型可透過 `GEMINI_CHAT_MODEL` 回復至已驗證的 `gemini-3.5-flash-lite`，仍使用相同 `google-genai` SDK。不得回復至 1.5 系列 fallback。

自訂切片版本以資料庫的 `published_version` 為準；匯入失敗、無搜尋結果或取消均不推進指標。管理員可回復前一個可用內容版本，重新匯入並驗證後才發布。

索引作業在 Cloud Tasks 每 120 秒續查同一個已保存的匯入 operation，最多到任務的 24 小時期限，不因等待而重複匯入。Google 若回報「已匯入、尚未索引」，仍須驗證遠端 chunks 內容及實際 Search 命中才發布。其他匯入錯誤停止並保留前版；人工重試遭拒的匯入才建立新的 operation。取消、刪除、到期或 worker 中斷均解除待發布狀態，避免文件永久卡住。

## 已執行的資源檢查

2026-09-16：SQL PostgreSQL 17 / db-f1-micro / 10 GiB SSD / asia-east1 / 每日 19:00 UTC 備份與 7 份保留 / 無授權公開網段 / 刪除保護；artifact bucket public access prevention + uniform access；queue 並行 2、每秒 1、最多 5 次派送；Scheduler 每小時第 15 分鐘清理。兩組 Secret Manager 第 1 版已建立，秘密值未保存到本機。

`backend/scripts/dev_cloud_acceptance.py` 使用隔離的 `dev-fixture-` 資料驗證任務與權限，Google 真實登入另從瀏覽器獨立驗收。腳本需要 localhost:54329 的 Cloud SQL Auth Proxy；不要在 production 或不明測試資料上執行。
