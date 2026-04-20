# QNT30361 — Institutional Portfolio Brain + Cross-Strategy Coordination Layer

## Mission
Build the institutional portfolio brain that coordinates strategies as a portfolio-of-strategies system rather than independent strategy silos.

## Shipped
- `backend/institutional_portfolio_brain.py`
- `frontend/institutional_portfolio_brain_panel.html`
- `backend/smoke_test_qnt30361.py`

## New endpoints
- `GET /portfolio-brain/status`
- `POST /portfolio-brain/ingest`
- `POST /portfolio-brain/coordinate`
- `POST /portfolio-brain/allocator-sync`

## What it adds
- cross-strategy overlap detection
- symbol-conflict penalties
- ranked active-set selection
- portfolio diversification scoring
- allocator sync with reserve-aware deployable capital
- governance ledger events for portfolio-brain operations

## Validation
- compile checks passed
- smoke test passed
