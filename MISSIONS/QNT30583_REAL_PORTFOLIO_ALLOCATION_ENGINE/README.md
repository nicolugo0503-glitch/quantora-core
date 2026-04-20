QNT30583 — REAL PORTFOLIO ALLOCATION ENGINE

ADDS
- backend/app/qnt30583_portfolio_allocation_router.py
- frontend/mission_qnt30583_portfolio_allocation_engine.html
- backend/artifacts/portfolio_allocation_engine/

UPGRADES
- strategy allocation summary from investor NAV
- target weight update workflow
- rebalance workflow
- investor portal navigation into allocation engine
- command center entry for QNT30583 Allocation Engine

API
- GET /api/portfolio-allocation
- POST /api/portfolio-allocation/weights
- POST /api/portfolio-allocation/rebalance
- GET /api/portfolio-allocation/summary

PURPOSE
- map investor NAV into strategy allocations
- bridge ownership state into actual portfolio construction
- prepare Quantora for live multi-strategy capital deployment
