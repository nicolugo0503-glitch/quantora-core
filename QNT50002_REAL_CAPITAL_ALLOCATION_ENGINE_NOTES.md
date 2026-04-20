# QNT50002 — Real Capital Allocation Engine

Quantora now has a portfolio-level allocation layer merged into the existing package without changing the root structure.

## Added backend modules
- `backend/app/allocation/`
- `backend/app/models/allocation_models.py`
- `backend/app/state/allocation_state.json`
- `backend/app/qnt50002_real_capital_allocation_engine_router.py`

## Institutional controls
- Capital is split into reserve capital and deployable capital
- Reserve weight expands under stressed liquidity and bearish regimes
- Strategy weights are capped by mandate to reduce concentration risk
- Allocation plans require explicit committee approval before becoming active
- Approved plans generate execution handoff tickets and sync decision memory into the execution layer

## API surface
- `GET /allocation/health`
- `GET /allocation/state`
- `GET /allocation/summary`
- `GET /allocation/strategies`
- `POST /allocation/strategies/register`
- `POST /allocation/recommend`
- `POST /allocation/approve`
- `POST /allocation/rebalance-preview`
- `GET /allocation/history`
- `GET /allocation/execution-handoff`

## Packaging rule respected
This mission was added into the same reference package structure and only extended the system with QNT50002 files.
