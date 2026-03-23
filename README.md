# Quantora QNT30322B - Alpaca Reintegration Layer

This package extends QNT30322A and restores a visible broker layer inside the Unified Command Center.

## What was added

- Alpaca broker status panel inside the UI
- Alpaca account snapshot: equity, cash, buying power, account status
- Alpaca positions table
- Alpaca open orders table
- Manual order submission route: `/orders/submit`
- Strategy execution routed to Alpaca when execution mode = `alpaca`
- Broker block included in `/command-center/snapshot`
- Railway-safe startup preserved from QNT30322A

## Alpaca configuration

### Preferred production / Railway setup
Set these environment variables in Railway:

- `ALPACA_API_KEY`
- `ALPACA_SECRET_KEY`
- `ALPACA_BASE_URL` (example: `https://paper-api.alpaca.markets`)

### Local fallback
Admin users can connect through the UI broker panel. That stores credentials in `backend/artifacts/broker_config.json` for local use.

## Local run

### macOS
```bash
cd QNT30322B_QUANTORA_ALPACA_REINTEGRATION_LAYER
chmod +x *.command
xattr -dr com.apple.quarantine *.command 2>/dev/null || true
./0_START_ALL_MAC.command
```

### Windows
Run:
- `START_BACKEND_WIN.bat`
- or `START_QUANTORA.bat`

## Health checks
- Backend: `http://127.0.0.1:8010/health`
- Frontend: `http://127.0.0.1:8010/`
- Snapshot: `http://127.0.0.1:8010/command-center/snapshot`

## Notes

- If no Alpaca credentials are configured, broker status returns `disconnected` and strategy/manual orders in `alpaca` mode will be rejected.
- This package was validated locally for startup, auth, snapshot, and disconnected-broker handling. Live Alpaca calls require real credentials and network access from your deployment environment.


## QNT30322B1 Frontend Sync Hotfix

This hotfix resolves the split deployment state where Railway/browser cache could serve the old command-center HTML while the QNT30322B backend was already live. The backend now serves HTML with strict no-cache headers and exposes `/version` for deployment verification.
