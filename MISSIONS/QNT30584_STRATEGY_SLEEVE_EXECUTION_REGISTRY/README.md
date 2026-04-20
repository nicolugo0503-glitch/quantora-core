QNT30584 — STRATEGY SLEEVE EXECUTION REGISTRY

ADDS
- backend/app/qnt30584_strategy_sleeve_execution_router.py
- frontend/mission_qnt30584_strategy_sleeve_execution.html
- backend/artifacts/strategy_sleeve_execution_registry/

UPGRADES
- sleeve execution summary
- deploy sleeve workflow
- sync sleeve workflow
- investor portal navigation into sleeve execution
- command center entry for QNT30584 Sleeve Execution

API
- GET /api/strategy-sleeves
- POST /api/strategy-sleeves/deploy
- POST /api/strategy-sleeves/sync
- GET /api/strategy-sleeves/summary

PURPOSE
- connect target allocation state to actual deployed strategy sleeves
- create execution visibility between portfolio design and capital deployment
- prepare Quantora for live multi-sleeve execution governance
