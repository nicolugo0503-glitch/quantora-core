#!/bin/bash
set -e
cd "$(dirname "$0")"
python3 -m pip install -r backend/requirements.txt >/dev/null 2>&1 || true
python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8010
