
# QNT30359 — Scenario Engine + Stress Testing Fabric

## Mission
Pressure-test autonomy, allocation, and cross-market exposure before capital is deployed.

## Shipped
- `backend/scenario_engine.py`
- `backend/smoke_test_qnt30359.py`
- `frontend/scenario_engine_panel.html`

## New endpoints
- `GET /scenario-engine/status`
- `POST /scenario-engine/define`
- `POST /scenario-engine/run`
- `GET /scenario-engine/library`

## Core behavior
- define reusable scenarios with volatility, liquidity, spread, and correlation shocks
- run stress verdicting against:
  - portfolio risk summary
  - allocator treasury / reserve floor
  - autonomy mode
  - execution optimizer slippage state
- produce governance actions:
  - recommended autonomy mode
  - throttle allocation
  - hold large orders
  - rebalance requirement

## Institutional effect
Quantora now has a forward-looking pressure-test layer instead of relying only on historical performance and live-state snapshots.
