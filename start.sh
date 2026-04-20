#!/usr/bin/env sh
set -eu
PORT_TO_USE="${PORT:-8010}"
test -f /app/backend/app/main.py
exec python -m uvicorn backend.app.main:app --host 0.0.0.0 --port "$PORT_TO_USE"
