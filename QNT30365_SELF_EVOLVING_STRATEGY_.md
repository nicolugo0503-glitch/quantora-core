# QNT30365 — Self-Evolving Strategy Factory + Autonomous Strategy Generation

## Mission
Build the institutional strategy factory that generates, backtests, scores, and promotes autonomous strategy candidates.

## Shipped
- `backend/strategy_factory.py`
- `frontend/strategy_factory_panel.html`
- `backend/smoke_test_qnt30365.py`

## New endpoints
- `GET /strategy-factory/status`
- `POST /strategy-factory/templates/upsert`
- `POST /strategy-factory/generate`
- `POST /strategy-factory/backtest`
- `POST /strategy-factory/promote`

## What it adds
- strategy template registry
- autonomous candidate generation
- synthetic backtest evaluation
- promotion scoring
- promoted-strategy registry
- governance ledger events for factory actions

## Validation
- compile checks passed
- smoke test passed
