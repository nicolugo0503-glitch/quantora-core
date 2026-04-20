# QNT30700 — Institutional Release Control

## Added
- Backend router: `backend/app/qnt30700_institutional_release_control_router.py`
- Frontend mission page: `frontend/mission_qnt30700_institutional_release_control.html`
- Smoke test: `backend/test_qnt30700_smoke.py`

## Capabilities
- release proposal registry
- pre-release validation using live broker safety layer posture
- operator approval workflow
- deployment controller
- rollback command
- configurable governance rules
- demo bootstrap path

## Endpoints
- `GET /api/institutional-release-control/summary`
- `POST /api/institutional-release-control/propose`
- `POST /api/institutional-release-control/validate`
- `POST /api/institutional-release-control/approve`
- `POST /api/institutional-release-control/deploy`
- `POST /api/institutional-release-control/rollback`
- `POST /api/institutional-release-control/rules`
- `POST /api/institutional-release-control/bootstrap-demo`
