# QNT30370 — Autonomous Strategy Retirement Board + Capital Reclamation Engine

## Mission
Retire broken strategies, reclaim trapped capital, and move borderline performers into watchlist before they continue consuming institutional capital.

## Shipped
- `backend/strategy_retirement_board.py`
- `frontend/strategy_retirement_board_panel.html`
- `backend/smoke_test_qnt30370.py`

## New endpoints
- `GET /strategy-retirement-board/status`
- `POST /strategy-retirement-board/rules/update`
- `POST /strategy-retirement-board/strategy/review`
- `POST /strategy-retirement-board/review-batch`

## What it adds
- retirement thresholds for score, drawdown, and losses
- watchlist path for borderline performers
- capital reclamation events
- retired strategy registry
- reclaimed-capital accounting
- governance ledger events for retirement decisions

## Validation
- compile checks passed
- smoke test passed
