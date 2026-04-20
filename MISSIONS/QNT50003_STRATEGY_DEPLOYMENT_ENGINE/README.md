# QNT50003 — Strategy Deployment Engine

This mission adds the institutional deployment layer that sits between capital allocation and execution.

Primary runtime files:
- `backend/app/strategy_deployment/engine.py`
- `backend/app/qnt50003_strategy_deployment_engine_router.py`
- `backend/app/state/strategy_deployment_state.json`

Core behaviors:
- convert allocation plans into deployment plans
- activate, scale, hold, or retire strategies by regime
- create release tickets for controlled execution handoff
- preserve decision lineage for audit and governance
