# QNT50001 — Live Broker Integration Layer

Quantora enters the live-capital execution phase with a broker-agnostic execution foundation added without altering the reference package structure.

## Added backend modules
- `backend/app/brokers/`
- `backend/app/execution/`
- `backend/app/models/execution_models.py`
- `backend/app/state/execution_state.json`
- `backend/app/qnt50001_live_broker_integration_layer_router.py`

## Institutional controls
- Default mode remains `paper`
- `safe_mode: true` blocks live execution
- Live mode requires explicit broker activation
- Binance transport is wired for signed REST order submission
- IBKR is staged as the next institutional venue connector
- Every order carries strategy, allocation, risk, and decision trace fields

## API surface
- `GET /execution/health`
- `GET /execution/mode`
- `GET /execution/logs`
- `POST /execution/mode`
- `POST /execution/activate-broker`
- `POST /execution/submit`

## Live unlock rule
Live execution only proceeds when:
- mode = `live`
- safe_mode = `false`
- active_broker is a live venue (`binance` or future `ibkr`)

## Packaging rule respected
This mission was merged into the attached reference structure without rebuilding or changing the root layout.
