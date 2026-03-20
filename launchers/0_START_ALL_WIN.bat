@echo off
setlocal
set SCRIPT_DIR=%~dp0
set ROOT=%SCRIPT_DIR%
if not exist "%ROOT%backend\app\main.py" (
  if exist "%ROOT%..\backend\app\main.py" set ROOT=%ROOT%..\
)
if not exist "%ROOT%backend\app\main.py" (
  echo [ERROR] Could not find project root from:
  echo %SCRIPT_DIR%
  pause
  exit /b 1
)
start "Quantora Backend" cmd /k call "%ROOT%START_BACKEND_WIN.bat"
echo [INFO] Waiting for backend...
timeout /t 6 /nobreak >nul
start "" "http://127.0.0.1:8010/health"
start "" "http://127.0.0.1:8010/docs"
start "" "http://127.0.0.1:8010/index.html"
endlocal
