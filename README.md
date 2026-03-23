# Quantora QNT30324 - Risk Engine

This package extends QNT30322B1 and upgrades Quantora from broker-connected command center into a real strategy operating layer.

## What was added

- Strategy lifecycle controls: register, start, stop, pause, delete
- Persistent strategy state and migration for existing operator state files
- Per-strategy performance tracking:
  - realized PnL
  - unrealized PnL
  - win rate
  - gross notional
  - capital in use
- Strategy execution logs inside the command center
- Capital guard on buy execution so strategies cannot keep allocating beyond operator capital
- Strategy-level capital limits
- Improved capital accounting based on open net exposure instead of cumulative filled notional
- Existing Alpaca broker layer preserved
- Railway-safe startup preserved

## Main endpoints

- `/strategies/register`
- `/strategies/lifecycle`
- `/strategies/delete`
- `/strategies/performance`
- `/strategies/logs`
- `/operator/run-once`
- `/command-center/snapshot`
- `/broker/alpaca/status`
- `/version`

## Alpaca configuration

Preferred production / Railway setup:

- `ALPACA_API_KEY`
- `ALPACA_SECRET_KEY`
- `ALPACA_BASE_URL`

Local fallback:
Admin users can connect through the UI broker panel. That stores credentials in `backend/artifacts/broker_config.json` for local use.

## Local run

### macOS
```bash
cd QNT30324_QUANTORA_REAL_STRATEGY_ENGINE
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
- Version: `http://127.0.0.1:8010/version`
- Snapshot: `http://127.0.0.1:8010/command-center/snapshot`

## Notes

- Existing operator state files are migrated in-place when loaded.
- Buy orders are now blocked if operator capital is zero or insufficient.
- Sells are allowed so exposure can be reduced.
- Live Alpaca calls require valid credentials and internet access from the deployment environment.
