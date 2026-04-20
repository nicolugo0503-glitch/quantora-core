# QNT50003 — Strategy Deployment Engine

Quantora now has a dedicated strategy deployment layer merged into the existing package without changing the root structure.

## Added backend modules
- `backend/app/strategy_deployment/`
- `backend/app/models/strategy_deployment_models.py`
- `backend/app/state/strategy_deployment_state.json`
- `backend/app/qnt50003_strategy_deployment_engine_router.py`

## Institutional controls
- Allocation plans no longer jump directly into unmanaged activation.
- Deployment plans select a governed number of active strategies based on regime fit and readiness.
- Non-selected active strategies are explicitly retired into the release queue.
- Safe mode forces deployment tickets toward paper routing until real-time kill-switch governance is added.
- Source allocation IDs and deployment decision IDs are synchronized into execution decision memory.

## API surface
- `GET /strategy-deployment/health`
- `GET /strategy-deployment/state`
- `GET /strategy-deployment/summary`
- `GET /strategy-deployment/profiles`
- `POST /strategy-deployment/profiles/register`
- `POST /strategy-deployment/evaluate`
- `POST /strategy-deployment/deploy`
- `POST /strategy-deployment/switch-regime`
- `GET /strategy-deployment/release-queue`
- `GET /strategy-deployment/history`

## Packaging rule respected
This mission was added into the same reference package structure and only extended the system with QNT50003 files.
