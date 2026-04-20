# QNT30376 — Multi-Venue Smart Order Router + Liquidity Split Engine

## Mission
Split orders across multiple venues using execution quality and available liquidity, while controlling fallback behavior and measuring child-order routing.

## Shipped
- `backend/smart_order_router.py`
- `frontend/smart_order_router_panel.html`
- `backend/smoke_test_qnt30376.py`

## New endpoints
- `GET /smart-order-router/status`
- `POST /smart-order-router/rules/update`
- `POST /smart-order-router/venues/ingest`
- `POST /smart-order-router/route`

## What it adds
- multi-venue order splitting
- liquidity-aware child order allocation
- quality-aware routing priority
- fallback routing when capacity is insufficient
- smart order routing telemetry
- governance ledger events for routed orders

## Validation
- compile checks passed
- smoke test passed
