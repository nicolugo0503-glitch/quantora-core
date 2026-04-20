
# QNT30356 — Allocator Intelligence + Treasury Layer

## Mission outcome
Quantora now converts portfolio-risk output into governed deployable capital, reserve discipline, and strategy-level target budgets.

## What was added
- `backend/allocator_intelligence.py`
- `GET /allocator-intelligence/status`
- `POST /allocator-intelligence/treasury/update`
- `POST /allocator-intelligence/rebalance/propose`
- `POST /allocator-intelligence/reserves/release`
- `frontend/allocator_intelligence_panel.html`
- `backend/smoke_test_qnt30356.py`

## Capability added
- treasury reserve target and reserve floor controls
- deployable capital calculation after risk haircut
- strategy allocator scoring using pnl, win rate, activity, and confidence
- proposal engine for increasing, decreasing, or holding strategy budgets
- reserve-release guardrails

## Validation
- python compile check passed
- smoke test passed
