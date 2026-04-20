# QNT30368 — Capital Promotion Router + Execution Gate Integration

## Mission
Route validated strategies into capital lanes and gate execution so only approved strategies can reach live orders.

## Shipped
- `backend/capital_promotion_router.py`
- `frontend/capital_promotion_router_panel.html`
- `backend/smoke_test_qnt30368.py`

## New endpoints
- `GET /capital-promotion-router/status`
- `POST /capital-promotion-router/rules/update`
- `POST /capital-promotion-router/candidate/route`
- `POST /capital-promotion-router/execution/decide`

## What it adds
- approved/watchlist/rejected capital lanes
- live vs sandbox vs blocked execution routing
- execution gating decisions
- released-order tracking
- governance ledger events for capital routing decisions

## Validation
- compile checks passed
- smoke test passed
