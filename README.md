# Quantora QNT30322 Unified Command Center

Institutional-grade unified operating surface for Quantora.

## Included systems
- Auth + operator system
- Strategy registration and monitoring
- Capital allocation view and controls
- Governance policy engine
- Approval workflows
- Control tower
- Governance ledger

## Mission objective
QNT30322 unifies the existing Quantora systems into one command center UI without resetting backend logic.

## Run locally
- Windows: `START_QUANTORA.bat`
- Mac: `0_START_ALL_MAC.command`

## Default local URLs
- App: `http://127.0.0.1:8010/`
- API docs: `http://127.0.0.1:8010/docs`
- Health: `http://127.0.0.1:8010/health`


## Alpaca environment variables

Set these in Railway or your shell before starting the backend:

- `ALPACA_API_KEY`
- `ALPACA_SECRET_KEY`
- `ALPACA_LIVE=false` for paper trading, `true` for live
- optional `ALPACA_BASE_URL` to override the default Alpaca endpoint

New endpoints:
- `/api/alpaca/account`
- `/api/alpaca/positions`
- `/api/alpaca/orders`
