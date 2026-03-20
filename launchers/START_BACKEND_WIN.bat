@echo off
setlocal
set SCRIPT_DIR=%~dp0
set ROOT=%SCRIPT_DIR%
if not exist "%ROOT%backend\app\main.py" (
  if exist "%ROOT%..\backend\app\main.py" set ROOT=%ROOT%..\
)
cd /d "%ROOT%backend" || (
  echo [ERROR] Could not open backend folder.
  echo Expected: %ROOT%backend
  pause
  exit /b 1
)
if not exist app\main.py (
  echo [ERROR] app\main.py not found in:
  cd
  pause
  exit /b 1
)
if not exist requirements.txt (
  > requirements.txt echo fastapi
  >> requirements.txt echo uvicorn
  >> requirements.txt echo pydantic
  >> requirements.txt echo python-dotenv
  >> requirements.txt echo requests
)
py -m pip install -r requirements.txt
if errorlevel 1 (
  echo [ERROR] Failed to install Python packages.
  pause
  exit /b 1
)
py -m uvicorn --app-dir . app.main:app --host 127.0.0.1 --port 8010
endlocal
