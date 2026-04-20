QNT30607 — AUTONOMOUS BREAK RESOLUTION SUGGESTION ENGINE

ADDS
- backend/app/qnt30607_resolution_suggestion_router.py
- frontend/mission_qnt30607_resolution_suggestions.html
- backend/artifacts/autonomous_break_resolution_suggestions/

UPGRADES
- suggestion summary
- generate suggestions workflow
- accept suggestion workflow
- investor portal navigation into resolution suggestions
- command center entry for QNT30607 Resolution Suggestions

API
- GET /api/resolution-suggestions
- POST /api/resolution-suggestions/run
- POST /api/resolution-suggestions/accept
- GET /api/resolution-suggestions/summary

PURPOSE
- propose remediation playbooks for open breaks
- accelerate operational response to reconciliation issues
- prepare Quantora for semi-autonomous control remediation
