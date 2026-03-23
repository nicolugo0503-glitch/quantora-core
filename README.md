# Quantora QNT30322 Unified Command Center

This mission extends QNT30321 without resetting the system.

## What is included
- Unified single-screen command center UI
- Preserved auth, strategy registration, capital allocation, policy engine, approvals, governance ledger, and admin control tower
- New command-center snapshot endpoint for one-call system state hydration
- Operator workspace and execution feed on the same operating surface

## Run locally
### macOS
- Double-click `0_START_ALL_MAC.command`

### Windows
- Double-click `START_QUANTORA.bat`

## Manual backend start
```bash
cd backend
python3 -m pip install -r requirements.txt
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8010 --reload
```

Open:
- http://127.0.0.1:8010/
- http://127.0.0.1:8010/docs
