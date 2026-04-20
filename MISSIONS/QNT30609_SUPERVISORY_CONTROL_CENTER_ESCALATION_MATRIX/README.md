QNT30609 — SUPERVISORY CONTROL CENTER + ESCALATION MATRIX

ADDS
- backend/app/qnt30609_supervisory_control_router.py
- frontend/mission_qnt30609_supervisory_control.html
- backend/artifacts/supervisory_control_center/

UPGRADES
- supervisory summary
- run supervisory control workflow
- acknowledge escalation workflow
- close escalation workflow
- investor portal navigation into supervisory control
- command center entry for QNT30609 Supervisory Control

API
- GET /api/supervisory-control
- POST /api/supervisory-control/run
- POST /api/supervisory-control/ack
- POST /api/supervisory-control/close
- GET /api/supervisory-control/summary

PURPOSE
- create supervisory oversight and escalation routing for operational breaks
- apply severity-based escalation matrix to open alerts
- prepare Quantora for institutional supervisory control governance
