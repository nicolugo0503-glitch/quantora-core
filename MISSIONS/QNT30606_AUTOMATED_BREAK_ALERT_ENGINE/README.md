QNT30606 — AUTOMATED BREAK ALERT ENGINE

ADDS
- backend/app/qnt30606_break_alert_router.py
- frontend/mission_qnt30606_break_alerts.html
- backend/artifacts/automated_break_alerts/

UPGRADES
- break alert summary
- alert scan workflow
- acknowledge alert workflow
- resolve alert workflow
- investor portal navigation into break alerts
- command center entry for QNT30606 Break Alerts

API
- GET /api/break-alerts
- POST /api/break-alerts/run
- POST /api/break-alerts/ack
- POST /api/break-alerts/resolve
- GET /api/break-alerts/summary

PURPOSE
- automatically surface reconciliation and broker control breaks
- centralize alert generation for operational oversight
- prepare Quantora for real-time exception monitoring
