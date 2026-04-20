
# QNT30341 — Stability Engine

Included:
- backend/sync_engine.py
- backend/truth_engine.py
- backend/reconciliation_guard.py
- backend/smoke_test_qnt30341.py

Added endpoints:
- GET /stability/status
- POST /stability/sync-now

What this patch does:
- creates a broker-first truth snapshot for positions/account/PnL
- flags broker/local drift with a reconciliation guard
- stores the latest truth snapshot in backend/artifacts/truth_engine_state.json
- makes broker-mode workspaces display broker positions as the visible truth
