# QNT30702 — Operator Command Console

Mission adds the institutional human supervision seat for Quantora.

## Added backend
- `backend/app/qnt30702_operator_command_console_router.py`
- `backend/test_qnt30702_smoke.py`

## Added frontend
- `frontend/mission_qnt30702_operator_command_console.html`

## Core capabilities
- operator summary across safety and release posture
- emergency stop, pause, resume, override commands
- governed release approve / deploy / rollback commands
- operator profile and watchlist management
- command, incident, and note audit trail

## Core endpoints
- `GET /api/operator-command-console/summary`
- `POST /api/operator-command-console/command`
- `POST /api/operator-command-console/operator-profile`
- `POST /api/operator-command-console/watchlist`
- `POST /api/operator-command-console/bootstrap-demo`
