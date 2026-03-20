@echo off
start cmd /k START_BACKEND_WIN.bat
timeout /t 3 >nul
start http://127.0.0.1:8010/
start http://127.0.0.1:8010/docs
