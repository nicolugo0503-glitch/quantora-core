# QNT30378 — Execution Drift Monitor + Market Regime Deviation Alerts

## Mission
Monitor drift between baseline and live execution behavior, detect regime-driven deviations, and raise alerts before execution quality silently degrades.

## Shipped
- `backend/execution_drift_monitor.py`
- `frontend/execution_drift_panel.html`
- `backend/smoke_test_qnt30378.py`

## New endpoints
- `GET /execution-drift/status`
- `POST /execution-drift/rules/update`
- `POST /execution-drift/snapshot`
- `POST /execution-drift/evaluate`

## What it adds
- baseline vs live execution drift snapshots
- regime deviation alerting
- slippage, latency, and fill-rate drift checks
- alert registry
- drift telemetry
- governance ledger events for drift monitoring

## Validation
- compile checks passed
- smoke test passed
