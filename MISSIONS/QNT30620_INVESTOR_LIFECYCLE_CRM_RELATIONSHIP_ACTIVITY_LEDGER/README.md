QNT30620 — INVESTOR LIFECYCLE CRM + RELATIONSHIP ACTIVITY LEDGER

ADDS
- backend/app/qnt30620_crm_router.py
- frontend/mission_qnt30620_crm.html
- backend/artifacts/investor_lifecycle_crm/

UPGRADES
- crm summary
- create relationship workflow
- update stage workflow
- log relationship activity workflow
- investor portal navigation into crm
- command center entry for QNT30620 Investor CRM

API
- GET /api/crm
- POST /api/crm/relationship
- POST /api/crm/stage
- POST /api/crm/activity
- GET /api/crm/summary

PURPOSE
- create an investor lifecycle crm with relationship tracking
- maintain a relationship activity ledger across stages and owners
- prepare Quantora for allocator-grade investor relationship management
