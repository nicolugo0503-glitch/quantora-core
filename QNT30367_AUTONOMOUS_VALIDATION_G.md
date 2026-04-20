# QNT30367 — Autonomous Validation Grid + Promotion Gatekeeper

## Mission
Build the institutional validation gatekeeper that reviews autonomous strategy candidates before promotion and blocks weak models from live capital.

## Shipped
- `backend/validation_gatekeeper.py`
- `frontend/validation_gatekeeper_panel.html`
- `backend/smoke_test_qnt30367.py`

## New endpoints
- `GET /validation-gatekeeper/status`
- `POST /validation-gatekeeper/rules/update`
- `POST /validation-gatekeeper/candidate/evaluate`
- `POST /validation-gatekeeper/promotion/review`

## What it adds
- promotion gate rules
- single-candidate approval review
- batch promotion review
- watchlist lane for near-threshold models
- hard rejection for weak or over-risked candidates
- governance ledger events for validation actions

## Validation
- compile checks passed
- smoke test passed
