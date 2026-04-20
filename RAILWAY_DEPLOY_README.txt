QNT30476 FULL RAILWAY COMPLETE

This package is the complete Quantora project zip with Railway-safe deployment fixes.

Root deploy structure:
- backend/
- frontend/
- Dockerfile
- start.sh
- .dockerignore

Key Railway fix:
- Dockerfile now uses COPY . /app instead of COPY backend /app/backend
- build step auto-detects backend/frontend if Railway wrapped the upload in another folder
