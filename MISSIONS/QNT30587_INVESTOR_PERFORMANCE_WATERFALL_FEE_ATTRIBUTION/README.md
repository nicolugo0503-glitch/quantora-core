QNT30587 — INVESTOR PERFORMANCE WATERFALL + FEE ATTRIBUTION

ADDS
- backend/app/qnt30587_waterfall_router.py
- frontend/mission_qnt30587_performance_waterfall.html
- backend/artifacts/investor_performance_waterfall/

UPGRADES
- performance waterfall summary
- fee configuration workflow
- waterfall calculation workflow
- investor portal navigation into performance waterfall
- command center entry for QNT30587 Waterfall

API
- GET /api/performance-waterfall
- POST /api/performance-waterfall/fees
- POST /api/performance-waterfall/calculate
- GET /api/performance-waterfall/summary

PURPOSE
- convert investor pnl into gross-to-net performance attribution
- attribute management and performance fees
- prepare Quantora for investor-grade economics reporting
