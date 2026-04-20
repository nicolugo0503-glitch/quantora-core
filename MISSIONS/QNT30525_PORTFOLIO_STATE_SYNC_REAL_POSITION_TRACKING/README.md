QNT30525 — PORTFOLIO STATE SYNC + REAL POSITION TRACKING

PURPOSE
Add real position and account state synchronization so Quantora can observe live holdings, balances, and PnL after execution.

ADDS
- qnt30525_portfolio_state_sync.py
- qnt30525_router.py
- portfolio_sync_binding_example.py
- portfolio_sync_contract.json
- frontend/mission_qnt30525_portfolio_sync.html

ALSO CHANGES
- frontend/mission_registry.json (adds QNT30525 route)

PRIMARY ENDPOINTS
- POST /api/portfolio/sync
- GET /api/portfolio/state
- GET /api/portfolio/history

WHAT THIS UNLOCKS
- position syncing
- account syncing
- total market value aggregation
- total PnL aggregation
- deployable portfolio-state UI

STABILITY
Additive only. Registry update only for frontend navigation.
