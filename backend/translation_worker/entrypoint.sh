#!/bin/sh
set -eu
# Runtime errors reach Cloud Logging. Request-body debug logging stays disabled.
export OLLAMA_DEBUG_LOG_REQUESTS=false
ollama serve >&2 &
translation_ollama_pid=$!
trap 'kill "$translation_ollama_pid" 2>/dev/null || true' EXIT
python - <<'PY'
import time, urllib.request
for attempt in range(60):
    try:
        urllib.request.urlopen('http://127.0.0.1:11434/api/tags',timeout=2).read()
        break
    except Exception:
        time.sleep(1)
else:
    raise SystemExit('Ollama did not start')
PY
python -m app.translation_worker "$@"
