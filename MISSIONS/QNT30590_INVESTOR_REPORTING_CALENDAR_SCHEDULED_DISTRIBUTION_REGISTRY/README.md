QNT30590 — INVESTOR REPORTING CALENDAR + SCHEDULED DISTRIBUTION REGISTRY

ADDS
- backend/app/qnt30590_reporting_calendar_router.py
- frontend/mission_qnt30590_reporting_calendar.html
- backend/artifacts/investor_reporting_calendar/

UPGRADES
- reporting calendar summary
- schedule event workflow
- execute event workflow
- investor portal navigation into reporting calendar
- command center entry for QNT30590 Reporting Calendar

API
- GET /api/reporting-calendar
- POST /api/reporting-calendar/schedule
- POST /api/reporting-calendar/run
- GET /api/reporting-calendar/summary

PURPOSE
- create a registry for recurring investor reporting events
- track scheduled and executed distribution cycles
- prepare Quantora for institutional reporting operations cadence
