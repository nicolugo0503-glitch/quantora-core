#!/bin/bash
set -e
cd "$(dirname "$0")/.."
echo "Quantora security self-check"
echo "PORT=${PORT:-8000}"
python3 - <<'PY'
import json, pathlib
root = pathlib.Path('.').resolve()
users = root / 'backend' / 'artifacts' / 'users.json'
session = root / 'backend' / 'artifacts' / 'session.json'
def show(path):
    if path.exists():
        print(f"[OK] {path}")
        print(path.read_text()[:400])
    else:
        print(f"[MISS] {path}")
show(users)
show(session)
PY
echo "[DONE] security self-check complete"
