#!/usr/bin/env sh
set -eu
PORT_TO_USE="${PORT:-8010}"
exec python -m uvicorn run:app --host 0.0.0.0 --port "$PORT_TO_USE" --workers 1
