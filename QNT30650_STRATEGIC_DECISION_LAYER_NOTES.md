# QNT30650 — Strategic Decision Layer

Institutional executive intelligence layer added on top of Quantora operating intelligence.

## Added
- Backend router: `backend/app/qnt30650_strategic_decision_router.py`
- Frontend mission page: `frontend/mission_qnt30650_strategic_decision_layer.html`
- Mission registry entry for QNT30650
- Main app wiring for strategic decision router

## Core outputs
- Capital directives
- Strategy rankings with executive actions
- Product lifecycle decisions
- Distribution channel priorities
- Risk interrupt stream
- Audit trail for each executive run

## API
- `GET /api/strategic-decision-layer/summary`
- `POST /api/strategic-decision-layer/run`
- `GET /api/strategic-decision-layer/audit`
- `POST /api/strategic-decision-layer/policy`

## Design posture
Hybrid institutional decision engine:
- deterministic scoring and governance thresholds
- cross-layer synthesis from allocation, performance, ledger, and pipeline state
- auditable run history persisted under `backend/artifacts/strategic_decision_layer/`
