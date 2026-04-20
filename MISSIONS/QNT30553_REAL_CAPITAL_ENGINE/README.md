QNT30553 — REAL CAPITAL ENGINE

ADDS
- backend/app/qnt30553_capital_router.py
- frontend/mission_qnt30553_real_capital_engine.html

UPGRADES
- frontend/quantora_sync.js now reads backend capital truth first
- mission_qnt30551_funding_flow.html now writes deposits and withdrawals into backend ledger
- mission_qnt30549_investor_dashboard_minimal.html now renders backend capital values
- mission_qnt30552_live_sync_engine.html now reflects backend-backed sync state

BACKEND ENDPOINTS
- GET /api/capital
- GET /api/capital/ledger
- POST /api/capital/deposit
- POST /api/capital/withdraw
- POST /api/capital/allocate
- POST /api/capital/deallocate

INTEGRATION
- router auto-mounted in backend/app/main.py
- ledger stored at backend/artifacts/capital_ledger.json
