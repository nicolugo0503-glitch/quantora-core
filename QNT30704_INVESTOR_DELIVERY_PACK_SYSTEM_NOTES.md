# QNT30704 — Investor Delivery Pack System

Institutional mission added on top of the QNT30702 merged baseline.

## What was added
- Router: `backend/app/qnt30704_investor_delivery_pack_system_router.py`
- Mission UI: `frontend/mission_qnt30704_investor_delivery_pack_system.html`
- Smoke test: `backend/test_qnt30704_smoke.py`

## Functional scope
- standardized investor delivery pack generation
- recipient registry for institutional routing
- delivery event logging with acknowledgement posture
- template and policy configuration
- integration with statement packs, reporting calendar, delivery log, safety layer, release control, and operator console

## Core API
- `GET /api/investor-delivery-pack-system/summary`
- `POST /api/investor-delivery-pack-system/build`
- `POST /api/investor-delivery-pack-system/deliver`
- `POST /api/investor-delivery-pack-system/template`
- `POST /api/investor-delivery-pack-system/bootstrap-demo`
