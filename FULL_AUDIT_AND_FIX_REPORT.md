# Quantora Full Audit and Fix Report

## What was broken
1. `frontend/index.html` was overwritten by the QNT30391 launch page.
2. That launch page called `GET /status`, but the active app is `backend.app.main:app`, whose catch-all static route returned `{"error":"not found","page":"status"}`.
3. Later mission backend files were copied into `backend/`, but they were not wired into the live runtime entrypoint, so their endpoints were not actually active.
4. `backend/app.py` from QNT30391 conflicted with the existing `backend/app/` package shape.
5. Generic filenames like `index.html` and `panel.html` caused collisions.

## What was fixed
- Restored the original QNT30378 root command center.
- Added a new hub page for the later missions.
- Added safe route integration via `backend/routes_qnt30379_to_qnt30391.py`.
- Patched `backend/app/main.py` to include those routes.
- Renamed the later launch page to `frontend/launch_panel_qnt30391.html`.
- Renamed the later payments page to `frontend/payments_panel_qnt30390.html`.
- Preserved the original startup and Docker flow.

## Clean launch endpoints
- `/launch/status`
- `/launch/live-trade`
- `/launch/stripe/charge`
