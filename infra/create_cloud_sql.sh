#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-tdf-ocf}"
REGION="${GCP_REGION:-asia-east1}"
INSTANCE_NAME="city-rag-sql-dev"
DB_NAME="city_governance"
DB_USER="rag_user"
DB_PASSWORD="${DB_PASSWORD:-GovRAG2026SecurePass!}"
TIER="db-f1-micro"

echo "=== 1. 確認專案設定 ==="
gcloud config set project "${PROJECT_ID}"

echo "=== 2. 啟用 Cloud SQL API ==="
gcloud services enable sqladmin.googleapis.com

echo "=== 3. 建立 Cloud SQL PostgreSQL 16 執行個體 (最小方案: ${TIER}) ==="
if ! gcloud sql instances describe "${INSTANCE_NAME}" --project="${PROJECT_ID}" &>/dev/null; then
  echo "正在建立 Cloud SQL 執行個體 ${INSTANCE_NAME} (約需 3-5 分鐘)..."
  gcloud sql instances create "${INSTANCE_NAME}" \
    --project="${PROJECT_ID}" \
    --database-version=POSTGRES_16 \
    --edition=ENTERPRISE \
    --tier="${TIER}" \
    --region="${REGION}" \
    --storage-type=SSD \
    --storage-size=10GB \
    --storage-auto-increase \
    --availability-type=zonal \
    --root-password="${DB_PASSWORD}"
  echo "Cloud SQL 執行個體建立成功！"
else
  echo "Cloud SQL 執行個體 ${INSTANCE_NAME} 已存在。"
fi

echo "=== 4. 建立資料庫: ${DB_NAME} ==="
if ! gcloud sql databases describe "${DB_NAME}" --instance="${INSTANCE_NAME}" --project="${PROJECT_ID}" &>/dev/null; then
  gcloud sql databases create "${DB_NAME}" --instance="${INSTANCE_NAME}" --project="${PROJECT_ID}"
  echo "資料庫 ${DB_NAME} 建立完成。"
else
  echo "資料庫 ${DB_NAME} 已存在。"
fi

echo "=== 5. 建立使用者: ${DB_USER} ==="
if ! gcloud sql users describe "${DB_USER}" --instance="${INSTANCE_NAME}" --project="${PROJECT_ID}" &>/dev/null; then
  gcloud sql users create "${DB_USER}" \
    --instance="${INSTANCE_NAME}" \
    --project="${PROJECT_ID}" \
    --password="${DB_PASSWORD}"
  echo "使用者 ${DB_USER} 建立完成。"
else
  echo "使用者 ${DB_USER} 已存在。"
fi

CONNECTION_NAME=$(gcloud sql instances describe "${INSTANCE_NAME}" --project="${PROJECT_ID}" --format='value(connectionName)')

echo "=========================================="
echo " Cloud SQL 設定完成！"
echo " Connection Name: ${CONNECTION_NAME}"
echo " Database: ${DB_NAME}"
echo " User: ${DB_USER}"
echo "=========================================="
