# QNT30372 — Opportunity Arbitration Engine + Cross-Strategy Capital Auction

## Mission
Force validated strategies to compete in a capital auction, arbitrate bid quality across candidates, and award capital to the strongest cross-strategy opportunities.

## Shipped
- `backend/opportunity_auction_engine.py`
- `frontend/opportunity_auction_panel.html`
- `backend/smoke_test_qnt30372.py`

## New endpoints
- `GET /opportunity-auction/status`
- `POST /opportunity-auction/rules/update`
- `POST /opportunity-auction/run`
- `POST /opportunity-auction/award`

## What it adds
- cross-strategy capital bidding
- weighted bid scoring
- priority multipliers
- limited winner set
- capital awards from auction results
- governance ledger events for auction and award actions

## Validation
- compile checks passed
- smoke test passed
