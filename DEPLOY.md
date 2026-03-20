# QNT30000 Deploy

## Local boot
### Windows
Run `0_START_ALL_WIN.bat` from the project root.

### Mac
Run `0_START_ALL_MAC.command` from the project root.

## Backend
- Local health: http://127.0.0.1:8010/health
- Local docs: http://127.0.0.1:8010/docs

## Frontend
- Local index: http://127.0.0.1:5173/index.html

## Railway
Deploy from the project root using the root `Dockerfile`.

## Vercel
Deploy the `frontend` directory as a static site.


Railway note: Dockerfile copies frontend into /app/frontend and serves it through FastAPI.
