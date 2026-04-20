# QNT30374 — Execution Quality Scoreboard + Venue Accountability Layer

## Mission
Score venue execution quality, flag weak routing venues, and create institutional accountability over slippage, fills, rejects, and latency.

## Shipped
- `backend/execution_quality_scoreboard.py`
- `frontend/execution_quality_panel.html`
- `backend/smoke_test_qnt30374.py`

## New endpoints
- `GET /execution-quality/status`
- `POST /execution-quality/rules/update`
- `POST /execution-quality/venues/ingest`
- `POST /execution-quality/scores/refresh`

## What it adds
- venue quality scoring
- accountability flags
- ingestible venue metrics
- venue ranking
- routing transparency layer
- governance ledger events for venue quality actions

## Validation
- compile checks passed
- smoke test passed
