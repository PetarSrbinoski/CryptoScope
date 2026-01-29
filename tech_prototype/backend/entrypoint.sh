#!/bin/bash
set -e

echo "[Entrypoint] Starting CryptoScope API..."
echo "[Entrypoint] Python path: $PYTHONPATH"
echo "[Entrypoint] Database path: $DB_PATH"

# Start uvicorn in the foreground; pipeline runs in background via startup event
exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
