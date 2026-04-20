QNT30603 — BROKER RECONCILIATION BRIDGE + ALPACA MATCH ENGINE

ADDS
- backend/app/qnt30603_broker_reconciliation_router.py
- frontend/mission_qnt30603_broker_reconciliation.html
- backend/artifacts/broker_reconciliation_bridge/

UPGRADES
- broker reconciliation summary
- add broker trade workflow
- run broker match workflow
- investor portal navigation into broker reconciliation
- command center entry for QNT30603 Broker Reconciliation

API
- GET /api/broker-reconciliation
- POST /api/broker-reconciliation/add-broker-trade
- POST /api/broker-reconciliation/run
- GET /api/broker-reconciliation/summary

PURPOSE
- bridge internal trade attribution to broker-side execution records
- detect missing fills and unexpected broker trades
- prepare Quantora for institutional broker reconciliation controls
