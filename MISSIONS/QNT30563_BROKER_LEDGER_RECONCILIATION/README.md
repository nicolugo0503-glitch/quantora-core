QNT30563 — BROKER-TO-LEDGER RECONCILIATION

ADDS
- backend/app/qnt30563_reconciliation_router.py
- frontend/mission_qnt30563_reconciliation_center.html
- backend/artifacts/user_broker_profiles/
- backend/artifacts/user_reconciliation/

UPGRADES
- user-scoped broker linking
- user-scoped reconciliation status
- drift detection between user ledger and broker truth
- controlled sync from broker into user ledger
- investor portal navigation into reconciliation center

API
- POST /api/user-broker/link
- POST /api/user-broker/unlink
- GET /api/user-broker/status
- GET /api/user-reconciliation
- POST /api/user-reconciliation/run
- POST /api/user-reconciliation/sync-from-broker

PURPOSE
- tie user-scoped capital and performance to broker truth
- detect and expose financial drift instead of hiding it
- create the trust layer required before investor statements and reporting
