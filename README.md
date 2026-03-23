# Quantora QNT30325A - System Stabilization Hotfix

This package extends QNT30324 and fixes the deployment and integration issues discovered during live use.

## What was fixed

- clean deployment state (no stale session, users, or operator artifacts shipped in the package)
- admin/session parity with normalized email + explicit `is_admin` session flag
- structured API errors instead of raw 500 fallthroughs
- snapshot hardening so modules degrade independently instead of crashing the command center
- integrated Performance Engine summary endpoints and UI panel
- preserved Alpaca, Strategy Engine, Risk Engine, Governance, and Control Tower
- Railway-safe startup preserved

## Main endpoints

- `/health`
- `/version`
- `/command-center/snapshot`
- `/performance/metrics`
- `/performance/strategy/{strategy_id}`
- `/performance/operator/{operator_id}`
- `/risk-engine/status`
- `/admin/control-tower`

## Clean deploy behavior

This build ships with empty users/session artifacts. Register your admin email after deploy to start with a clean operator state.

## Health checks

- Backend: `http://127.0.0.1:8010/health`
- Docs: `http://127.0.0.1:8010/docs`
- Frontend: `http://127.0.0.1:8010/`
- Version: `http://127.0.0.1:8010/version`
