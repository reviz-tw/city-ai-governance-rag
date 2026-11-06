# Supply immutable upstream image references from deployment preflight.
ARG OLLAMA_IMAGE
ARG PYTHON_IMAGE
FROM ${OLLAMA_IMAGE} AS ollama
FROM ${PYTHON_IMAGE}
RUN apt-get update && apt-get install -y --no-install-recommends libstdc++6 libgomp1 ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=ollama /bin/ollama /usr/local/bin/ollama
COPY --from=ollama /usr/lib/ollama /usr/local/lib/ollama
RUN LD_LIBRARY_PATH=/usr/local/lib/ollama /usr/local/lib/ollama/llama-server --version
ENV PYTHONUNBUFFERED=1 OLLAMA_HOST=127.0.0.1:11434 OLLAMA_MODELS=/opt/translation-models OLLAMA_NO_CLOUD=1 OLLAMA_NUM_PARALLEL=1 TRANSLATION_RUNTIME=ollama
WORKDIR /app
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
ARG TRANSLATION_MODEL
ARG TRANSLATION_MODEL_REVISION
ENV TRANSLATION_MODEL=${TRANSLATION_MODEL} TRANSLATION_MODEL_REVISION=${TRANSLATION_MODEL_REVISION}
RUN ollama serve >/tmp/model-build.log 2>&1 & \
    translation_server_pid=$!; \
    sleep 3; \
    ollama pull "${TRANSLATION_MODEL}" && \
    python -c 'import json,os,urllib.request; rows=json.load(urllib.request.urlopen("http://127.0.0.1:11434/api/tags"))["models"]; assert any(r["name"]==os.environ["TRANSLATION_MODEL"] and r["digest"].removeprefix("sha256:")==os.environ["TRANSLATION_MODEL_REVISION"].removeprefix("sha256:") for r in rows), "Model digest mismatch"'; \
    translation_result=$?; kill "$translation_server_pid"; exit "$translation_result"
COPY backend/app /app/app
COPY backend/translation_worker/entrypoint.sh /app/translation-entrypoint.sh
RUN chmod +x /app/translation-entrypoint.sh
ENTRYPOINT ["/app/translation-entrypoint.sh"]
CMD ["--backfill", "--max-seconds", "720"]
