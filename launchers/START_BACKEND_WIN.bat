@echo off
cd /d "%~dp0backend"
if not exist requirements.txt (
  echo Missing backend\requirements.txt
  pause
  exit /b 1
)
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8010 --reload
