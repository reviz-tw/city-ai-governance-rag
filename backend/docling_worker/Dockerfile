FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 HF_HOME=/opt/docling/cache DOCLING_ARTIFACTS_PATH=/opt/docling/models TIKTOKEN_CACHE_DIR=/opt/docling/tokenizer
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
COPY backend/docling_worker/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu
RUN docling-tools models download layout tableformer rapidocr --output-dir /opt/docling/models
RUN python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')"
RUN apt-get update && apt-get install -y --no-install-recommends libreoffice-writer && rm -rf /var/lib/apt/lists/*
COPY backend/docling_worker /app/docling_worker
CMD ["uvicorn", "docling_worker.server:app", "--host", "0.0.0.0", "--port", "8080"]
