QNT30575 — INVESTOR TASKING + ONBOARDING CHECKLIST ENGINE

ADDS
- backend/app/qnt30575_checklist_router.py
- frontend/mission_qnt30575_onboarding_checklist.html
- backend/artifacts/investor_onboarding_checklists/

UPGRADES
- onboarding checklist summary
- task completion / reopening workflow
- auto-reconciliation against KYC, funding, statements, deposits, and secure inbox activity
- investor portal navigation into checklist
- command center entry for QNT30575 Checklist

API
- GET /api/onboarding-checklist
- POST /api/onboarding-checklist/task
- GET /api/onboarding-checklist/summary

PURPOSE
- create structured investor onboarding progression
- unify task completion with actual platform activity
- prepare Quantora for guided investor operations at scale
