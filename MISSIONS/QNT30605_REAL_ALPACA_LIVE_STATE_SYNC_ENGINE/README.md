QNT30605 — REAL ALPACA LIVE STATE SYNC ENGINE

ADDS
- backend/app/qnt30605_alpaca_live_sync_router.py
- frontend/mission_qnt30605_alpaca_live_sync.html
- backend/artifacts/alpaca_live_state_sync/

UPGRADES
- alpaca sync summary
- import live state workflow
- run live sync workflow
- investor portal navigation into alpaca sync
- command center entry for QNT30605 Alpaca Live Sync

API
- GET /api/alpaca-sync
- POST /api/alpaca-sync/import
- POST /api/alpaca-sync/run
- GET /api/alpaca-sync/summary

PURPOSE
- sync live broker cash and positions into Quantora
- feed three-way reconciliation with live state
- prepare Quantora for production-grade Alpaca state synchronization
