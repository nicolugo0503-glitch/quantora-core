# QNT30343 Automation Loop

This mission hardens the existing Quantora automation engine into an operator-facing control layer.

## Added
- `frontend/automation_loop_panel.html`
- `GET /automation/worker-status`
- `POST /automation/worker/start`
- `POST /automation/worker/stop`
- `POST /automation/run-once`
- `backend/smoke_test_qnt30343.py`

## Intent
Use the automation loop in paper mode first. Start with one operator, one symbol, broker reconcile ON, and PnL sync ON. Use `run once` before enabling recurring execution.
