#!/bin/bash
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
osascript -e "tell application \"Terminal\" to do script \"cd '$ROOT' && ./1_START_BACKEND_MAC.command\"" || true
osascript -e "tell application \"Terminal\" to do script \"cd '$ROOT' && ./2_START_FRONTEND_MAC.command\"" || true
