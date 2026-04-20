@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

echo === Quantora GitHub Deploy (QNT30424 batch fix) ===
set "REPO_URL=https://github.com/nicolugo0503-glitch/quantora-core.git"
echo Repo: %REPO_URL%

where git >nul 2>nul
if errorlevel 1 (
  echo ERROR: git is not installed or not on PATH.
  pause
  exit /b 1
)

if not exist ".git" (
  git init
  if errorlevel 1 goto :fail
)

for /f "delims=" %%i in ('git config --get user.name 2^>nul') do set "GIT_USER_NAME=%%i"
if not defined GIT_USER_NAME (
  git config user.name "nicolugo0503"
  if errorlevel 1 goto :fail
)

for /f "delims=" %%i in ('git config --get user.email 2^>nul') do set "GIT_USER_EMAIL=%%i"
if not defined GIT_USER_EMAIL (
  git config user.email "nicolugo0503@gmail.com"
  if errorlevel 1 goto :fail
)

git add -A
if errorlevel 1 goto :fail

git diff --cached --quiet >nul 2>nul
if errorlevel 1 (
  git commit -m "QNT-REAL01A operator mode + github deploy hardening"
  if errorlevel 1 goto :fail
) else (
  echo No staged changes to commit.
)

git branch -M main
if errorlevel 1 goto :fail

git remote remove origin >nul 2>nul
git remote add origin %REPO_URL%
if errorlevel 1 goto :fail

git push -u origin HEAD:main --force
if errorlevel 1 goto :fail

echo DEPLOYED QNT-REAL01A
pause
exit /b 0

:fail
echo DEPLOY FAILED. Review the error above.
pause
exit /b 1
