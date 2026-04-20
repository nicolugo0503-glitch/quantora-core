QNT30596 — INVESTOR DEALING DAY / NAV CUTOFF CONTROL ENGINE

ADDS
- backend/app/qnt30596_dealing_day_router.py
- frontend/mission_qnt30596_dealing_day.html
- backend/artifacts/investor_dealing_day_control/

UPGRADES
- dealing day summary
- create dealing day workflow
- cutoff policy workflow
- apply cutoff workflow
- investor portal navigation into dealing day control
- command center entry for QNT30596 Dealing Day

API
- GET /api/dealing-day
- POST /api/dealing-day/policy
- POST /api/dealing-day/create
- POST /api/dealing-day/apply-cutoff
- GET /api/dealing-day/summary

PURPOSE
- create dealing day and nav cutoff controls
- gate subscriptions and redemptions by cutoff windows
- prepare Quantora for institutional dealing-day operations
