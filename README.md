# Quantora QNT30324B - Capital Source of Truth

This package extends QNT30325A and formalizes capital hierarchy across Quantora.

## What was fixed

- added a real capital source layer: `internal` or `broker`
- aligned risk calculations to the selected capital source
- aligned performance summaries to the selected capital source
- removed the internal-vs-Alpaca capital mismatch that caused risk instability
- added safe fallback state when broker capital mode is selected but broker data is unavailable
- exposed capital source controls in the unified command center
- preserved Alpaca, Strategy Engine, Risk Engine, Governance, Control Tower, and Railway-safe startup

## Main endpoints

- `/health`
- `/version`
- `/command-center/snapshot`
- `/capital-source/status`
- `/capital-source/update`
- `/performance/metrics`
- `/risk-engine/status`
- `/admin/control-tower`

## Clean deploy behavior

This build ships with empty users/session artifacts. Register your admin email after deploy to start with a clean operator state.

## Health checks

- Backend: `http://127.0.0.1:8010/health`
- Docs: `http://127.0.0.1:8010/docs`
- Frontend: `http://127.0.0.1:8010/`
- Version: `http://127.0.0.1:8010/version`
