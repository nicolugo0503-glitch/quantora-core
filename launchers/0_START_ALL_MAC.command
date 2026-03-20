#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
osascript -e 'tell application "Terminal" to do script "cd "'"$DIR"'"; ./1_START_BACKEND_MAC.command"'
sleep 3
open http://127.0.0.1:8010/
open http://127.0.0.1:8010/docs
