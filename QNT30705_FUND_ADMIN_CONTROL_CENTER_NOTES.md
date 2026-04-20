# QNT30705 — Fund Administration Control Center

This mission adds an institutional fund administration layer on top of the working QNT30704 deployable root package.

## Added components
- backend router: `backend/app/qnt30705_fund_admin_control_center_router.py`
- frontend mission panel: `frontend/mission_qnt30705_fund_admin_control_center.html`
- smoke test: `backend/test_qnt30705_smoke.py`

## Core capabilities
- aggregate AUM and capital accounting from the investor capital ledger
- reconcile ledger NAV against performance engine NAV
- link waterfall, statement, operations, safety, release, operator, and delivery context
- run a governed period close
- record capital/compliance events for audit
- bootstrap a realistic fund admin demo state

## API surface
- `GET /api/fund-admin-control-center/summary`
- `POST /api/fund-admin-control-center/bootstrap-demo`
- `POST /api/fund-admin-control-center/run-close`
- `POST /api/fund-admin-control-center/record-flow`
- `POST /api/fund-admin-control-center/policy`
