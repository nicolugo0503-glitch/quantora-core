QNT30568 — LIVE EXTERNAL FUNDING DEPLOYMENT PASS

ADDS
- backend/app/qnt30568_live_external_funding_router.py
- frontend/mission_qnt30568_live_external_funding_center.html
- backend/artifacts/live_external_funding_deployment/

UPGRADES
- live funding deployment readiness checks
- live funding enable/disable control
- provider env template exposure
- investor portal navigation into live funding deployment
- command center entry for QNT30568 Live Funding Deploy

API
- GET /api/live-funding-deployment/status
- POST /api/live-funding-deployment/check
- POST /api/live-funding-deployment/enable
- POST /api/live-funding-deployment/disable
- GET /api/live-funding-deployment/env-template

IMPORTANT
- this mission does not inject live secrets
- it enables operational readiness checks and live-mode control once deployment env vars exist

PURPOSE
- convert provider activation into deployment-governed live external funding control
- make live funding a visible, auditable operational state
