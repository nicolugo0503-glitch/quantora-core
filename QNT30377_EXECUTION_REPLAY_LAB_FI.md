# QNT30377 — Execution Replay Lab + Fill Attribution Engine

## Mission
Replay execution event streams, reconstruct order behavior, and attribute fills and realized economics back to specific venues.

## Shipped
- `backend/execution_replay_lab.py`
- `frontend/execution_replay_panel.html`
- `backend/smoke_test_qnt30377.py`

## New endpoints
- `GET /execution-replay/status`
- `POST /execution-replay/rules/update`
- `POST /execution-replay/replay`
- `POST /execution-replay/attribute`

## What it adds
- execution replay snapshots
- latency and slippage alerts
- venue-level fill attribution
- realized PnL attribution by venue
- replay telemetry
- governance ledger events for replay and attribution

## Validation
- compile checks passed
- smoke test passed
