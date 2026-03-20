#!/bin/bash
set -e
cd "$(dirname "$0")/backend"
[ -f app/main.py ] || { echo "[ERROR] backend/app/main.py not found"; exit 1; }
[ -f requirements.txt ] || printf "fastapi
uvicorn
pydantic
python-dotenv
requests
" > requirements.txt
python3 -m pip install -r requirements.txt || true
python3 -m uvicorn --app-dir . app.main:app --reload --port 8010
