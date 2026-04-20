QNT30595 — INVESTOR SUBSCRIPTION / REDEMPTION QUEUE + CAPITAL ACTIVITY CONTROL

ADDS
- backend/app/qnt30595_capital_activity_router.py
- frontend/mission_qnt30595_capital_activity.html
- backend/artifacts/investor_capital_activity_control/

UPGRADES
- capital activity summary
- submit request workflow
- review request workflow
- process request workflow
- investor portal navigation into capital activity
- command center entry for QNT30595 Capital Activity

API
- GET /api/capital-activity
- POST /api/capital-activity/request
- POST /api/capital-activity/review
- POST /api/capital-activity/process
- GET /api/capital-activity/summary

PURPOSE
- create a controlled subscription/redemption queue
- gate capital activity before ledger movement
- prepare Quantora for institutional capital activity controls
