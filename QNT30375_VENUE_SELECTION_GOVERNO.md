# QNT30375 — Venue Selection Governor + Adaptive Routing Policy Engine

## Mission
Turn venue intelligence into routing control, dynamically select the best venue, block weak venues, and apply adaptive policy before orders are routed.

## Shipped
- `backend/venue_selection_governor.py`
- `frontend/venue_governor_panel.html`
- `backend/smoke_test_qnt30375.py`

## New endpoints
- `GET /venue-governor/status`
- `POST /venue-governor/policy/update`
- `POST /venue-governor/venues/ingest`
- `POST /venue-governor/select`
- `POST /venue-governor/batch-select`

## What it adds
- adaptive routing policy
- venue filtering and blocking
- fallback routing logic
- order-by-order venue selection
- venue accountability execution control
- governance ledger events for routing decisions

## Validation
- compile checks passed
- smoke test passed
