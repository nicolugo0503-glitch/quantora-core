# QNT30630 — Autonomous Allocation Engine

Added in this merged build:
- backend router: `backend/app/qnt30630_allocation_engine_router.py`
- allocator artifacts store: `backend/artifacts/allocation_engine/`
- governed scoring with explicit policy thresholds
- deployable capital plan with reserve floor enforcement
- rebalance deltas against live strategy execution allocations
- decision registry for auditable allocation runs
- frontend mission page: `frontend/mission_qnt30630_allocation_engine.html`
- command center navigation + mission registry entry
- smoke test: `backend/smoke_test_qnt30630.py`

Core endpoints:
- `GET /api/allocation-engine/summary`
- `GET /api/allocation-engine/decisions`
- `POST /api/allocation-engine/plan`
- `POST /api/allocation-engine/run`
- `POST /api/allocation-engine/policy`
- `POST /api/allocation-engine/bootstrap-demo`

Design standard:
- explainable scoring
- hard risk constraints
- reserve-aware deployment
- decision persistence for auditability
