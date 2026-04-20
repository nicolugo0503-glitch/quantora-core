# QNT30369 — Autonomous Capital Escalation Board + Performance-Based Capital Ladder

## Mission
Escalate winning strategies up the capital ladder, reduce degrading performers, and kill capital paths that violate institutional performance or drawdown thresholds.

## Shipped
- `backend/capital_escalation_board.py`
- `frontend/capital_escalation_board_panel.html`
- `backend/smoke_test_qnt30369.py`

## New endpoints
- `GET /capital-escalation-board/status`
- `POST /capital-escalation-board/rules/update`
- `POST /capital-escalation-board/strategy/review`
- `POST /capital-escalation-board/review-batch`

## What it adds
- autonomous capital ladder
- sandbox / limited live / scaled live / priority capital tiers
- promotion, reduction, and kill decisions
- drawdown-aware capital shutdown logic
- performance-based capital compounding pathway
- governance ledger events for escalation decisions

## Validation
- compile checks passed
- smoke test passed
