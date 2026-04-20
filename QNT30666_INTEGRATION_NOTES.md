# QNT30666 — Live Allocation Control Tower

## Purpose
Control live capital allocation after dispatch supervision by combining strategic direction, deployment readiness, and execution governance into a governed allocation authority layer.

## Added components
- `backend/app/qnt30666_live_allocation_control_tower_router.py`
- `frontend/mission_qnt30666_live_allocation_control_tower.html`
- mission registry entry for QNT30666
- manifest update for QNT30666

## Endpoints
- `GET /api/live-allocation-control-tower/summary`
- `POST /api/live-allocation-control-tower/run`
- `GET /api/live-allocation-control-tower/audit`
- `POST /api/live-allocation-control-tower/policy`

## Dependency chain
- QNT30665 Capital Dispatch Supervision Layer
- QNT30661 Live Capital Deployment Orchestrator
- QNT30662 Execution Governance Command
- QNT30650 Strategic Decision Layer
