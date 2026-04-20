QNT30564 — INVESTOR STATEMENTS + REPORTING

ADDS
- backend/app/qnt30564_reporting_router.py
- frontend/mission_qnt30564_reporting_center.html
- backend/artifacts/user_statements/

UPGRADES
- user-scoped statement generation
- reporting summary from capital, performance, and reconciliation truth
- investor portal navigation into statements
- command center entry for QNT30564 Statements

API
- GET /api/user-statements
- POST /api/user-statements/generate
- GET /api/user-statements/latest
- GET /api/user-reports/summary

PURPOSE
- deliver investor-facing statements from user-isolated financial truth
- prepare Quantora for reporting delivery and LP-style communication
