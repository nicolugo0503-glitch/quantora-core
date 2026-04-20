FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /tmp/build-context
COPY . /tmp/build-context

RUN set -eux; \
    APP_ROOT="/tmp/build-context"; \
    if [ ! -d "$APP_ROOT/backend" ] || [ ! -f "$APP_ROOT/backend/requirements.txt" ] || [ ! -f "$APP_ROOT/backend/app/main.py" ]; then \
      CANDIDATE="$(find /tmp/build-context -mindepth 1 -maxdepth 6 -type d | while read -r d; do if [ -d "$d/backend" ] && [ -f "$d/backend/requirements.txt" ] && [ -f "$d/backend/app/main.py" ]; then echo "$d"; break; fi; done)"; \
      test -n "$CANDIDATE"; \
      APP_ROOT="$CANDIDATE"; \
    fi; \
    mkdir -p /app; \
    cp -R "$APP_ROOT"/. /app/; \
    test -d /app/backend; \
    test -f /app/backend/requirements.txt; \
    test -f /app/backend/app/main.py; \
    if [ ! -f /app/start.sh ]; then \
      printf '%s\n' '#!/usr/bin/env sh' 'set -eu' 'PORT_TO_USE="${PORT:-8010}"' 'test -f /app/backend/app/main.py' 'exec python -m uvicorn backend.app.main:app --host 0.0.0.0 --port "$PORT_TO_USE"' > /app/start.sh; \
    fi; \
    chmod +x /app/start.sh; \
    python -m pip install --no-cache-dir -r /app/backend/requirements.txt

WORKDIR /app
EXPOSE 8010
CMD ["/app/start.sh"]
