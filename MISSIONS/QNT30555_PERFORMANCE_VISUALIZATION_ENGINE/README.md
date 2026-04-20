QNT30555 — PERFORMANCE VISUALIZATION ENGINE

ADDS
- backend/app/qnt30555_performance_router.py
- frontend/mission_qnt30555_performance_visualization_engine.html

UPGRADES
- QNT30553 capital mutations now auto-capture performance snapshots
- investor dashboard reads performance-history current snapshot + equity series
- command center includes QNT30555 performance entry point

BACKEND ENDPOINTS
- GET /api/performance-history/summary
- GET /api/performance-history/series
- POST /api/performance-history/snapshot
- GET /api/performance-history/attribution

ARTIFACTS
- backend/artifacts/performance_history.json

PURPOSE
- turn real capital into visible performance intelligence
- show equity curve, pnl, return %, and flow attribution
