#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
REPO_URL="https://github.com/nicolugo0503-glitch/quantora-core.git"
echo "=== Quantora GitHub Deploy ==="
echo "Repo: $REPO_URL"
command -v git >/dev/null 2>&1 || { echo "ERROR: git is not installed."; exit 1; }
if [ ! -d .git ]; then
  git init
fi
git config user.name >/dev/null 2>&1 || git config user.name "nicolugo0503"
git config user.email >/dev/null 2>&1 || git config user.email "nicolugo0503@gmail.com"
git add -A
if ! git diff --cached --quiet; then
  git commit -m "QNT-REAL01A operator mode + github deploy hardening"
else
  echo "No staged changes to commit."
fi
git branch -M main
git remote remove origin >/dev/null 2>&1 || true
git remote add origin "$REPO_URL"
git push -u origin HEAD:main --force
