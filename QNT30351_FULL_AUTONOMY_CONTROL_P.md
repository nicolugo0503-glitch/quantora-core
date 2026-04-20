
# QNT30351 — Full Autonomy Control Plane

## Mission
Promote Quantora from governed optimization to machine-enforced autonomy states.

## Shipped
- `backend/autonomy_control_plane.py`
- new routes:
  - `GET /autonomy/status`
  - `POST /autonomy/evaluate`
  - `POST /autonomy/transition`
  - `POST /autonomy/delegation/update`
  - `POST /autonomy/run-cycle`
- new frontend panel:
  - `frontend/autonomy_control_plane_panel.html`
- command center navigation updated
- startup now seeds `backend/artifacts/autonomy_control_plane.json`
- new smoke test:
  - `backend/smoke_test_qnt30351.py`

## Architecture effect
This adds an explicit autonomy state machine above execution:
- `supervised`
- `constrained_autonomy`
- `delegated_autonomy`
- `locked`

Autonomy promotion is now conditioned on:
- governance enforcement snapshot
- pending approvals
- risk state
- performance score
- delegation tier for live operation

## Operational meaning
Quantora can now:
- score whether an operator is ready for autonomy
- refuse unsafe promotions
- enforce delegation limits for live execution
- lock autonomy when governance or risk conditions degrade
- run governed autonomy cycles with machine checks before execution
