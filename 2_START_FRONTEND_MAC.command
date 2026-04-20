#!/bin/bash
set -e
cd "$(dirname "$0")"
python3 -m http.server 5173 --directory frontend
