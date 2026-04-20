QNT30600 — INVESTOR FULL LIFECYCLE RECONCILIATION ENGINE

ADDS
- backend/app/qnt30600_reconciliation_router.py
- frontend/mission_qnt30600_reconciliation.html
- backend/artifacts/investor_reconciliation/

UPGRADES
- reconciliation summary
- run reconciliation workflow
- issue detection across nav, capital activity, equalization, rollforward, and confirmations
- investor portal navigation into reconciliation
- command center entry for QNT30600 Reconciliation

API
- GET /api/reconciliation
- POST /api/reconciliation/run
- GET /api/reconciliation/summary

PURPOSE
- detect mismatches across the full investor lifecycle
- create institutional-grade control and accounting validation
- prepare Quantora for audit-ready reconciliation operations
