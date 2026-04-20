QNT30604 — CASH / POSITION / BROKER THREE-WAY RECONCILIATION ENGINE

ADDS
- backend/app/qnt30604_threeway_reconciliation_router.py
- frontend/mission_qnt30604_threeway_reconciliation.html
- backend/artifacts/threeway_reconciliation/

UPGRADES
- three-way reconciliation summary
- import broker state workflow
- run three-way reconciliation workflow
- investor portal navigation into three-way reconciliation
- command center entry for QNT30604 Three-Way Recon

API
- GET /api/threeway
- POST /api/threeway/import-broker-state
- POST /api/threeway/run
- GET /api/threeway/summary

PURPOSE
- reconcile internal expected state, broker state, and official NAV
- detect cash mismatches, position mismatches, and NAV consistency breaks
- prepare Quantora for prime-broker-grade reconciliation controls
