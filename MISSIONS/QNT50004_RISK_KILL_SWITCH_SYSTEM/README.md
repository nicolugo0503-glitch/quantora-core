# QNT50004 — Risk Kill-Switch System

This mission adds a hard-stop control layer to Quantora.

## Added files
- `backend/app/risk_control/engine.py`
- `backend/app/risk_control/state_store.py`
- `backend/app/models/risk_kill_switch_models.py`
- `backend/app/qnt50004_risk_kill_switch_system_router.py`
- `backend/app/state/risk_kill_switch_state.json`
- `frontend/mission_qnt50004_risk_kill_switch_system.html`

## Core capabilities
- Portfolio and strategy drawdown enforcement
- Daily loss and notional breach detection
- Venue connectivity and latency monitoring
- Automatic safe-mode fallback on critical breach
- Override, reset, and audit-grade trigger ledger
