QNT30594 — INVESTOR MULTI-SERIES NAV ROLLFORWARD ENGINE

ADDS
- backend/app/qnt30594_rollforward_router.py
- frontend/mission_qnt30594_rollforward.html
- backend/artifacts/investor_multi_series_rollforward/

UPGRADES
- rollforward summary
- generate period workflow
- lock period workflow
- investor portal navigation into rollforward
- command center entry for QNT30594 Rollforward

API
- GET /api/rollforward
- POST /api/rollforward/generate
- POST /api/rollforward/lock
- GET /api/rollforward/summary

PURPOSE
- create multi-series NAV rollforward periods
- bridge equalization accounting into period reporting
- prepare Quantora for allocator-grade series rollforward administration
