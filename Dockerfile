# ==========================================
# Stage 1: Build React Frontend (Topos Style)
# ==========================================
FROM node:20-alpine AS web-builder

WORKDIR /build/web

COPY web/package*.json ./
RUN npm install

COPY web/ ./
RUN npm run build

# ==========================================
# Stage 2: Python Backend & Unified Server
# ==========================================
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

WORKDIR /app

# Install system dependencies for build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application source code
COPY backend/app/ ./app/

# Copy compiled React frontend bundle to backend static web_dist
COPY --from=web-builder /build/web/dist ./app/web_dist

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
