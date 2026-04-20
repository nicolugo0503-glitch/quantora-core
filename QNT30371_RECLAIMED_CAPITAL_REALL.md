# QNT30371 — Reclaimed Capital Reallocation Board + Opportunity Queue Engine

## Mission
Rank fresh opportunities against reclaimed capital, build a prioritized queue, and reallocate freed institutional capital toward validated higher-edge candidates.

## Shipped
- `backend/reallocation_opportunity_queue.py`
- `frontend/reallocation_board_panel.html`
- `backend/smoke_test_qnt30371.py`

## New endpoints
- `GET /reallocation-board/status`
- `POST /reallocation-board/rules/update`
- `POST /reallocation-board/queue/refresh`
- `POST /reallocation-board/capital/execute`

## What it adds
- prioritized opportunity queue
- reclaimed-capital aware routing
- watchlist haircut logic
- per-candidate max reallocation cap
- executed reallocation events
- governance ledger events for reallocation actions

## Validation
- compile checks passed
- smoke test passed
