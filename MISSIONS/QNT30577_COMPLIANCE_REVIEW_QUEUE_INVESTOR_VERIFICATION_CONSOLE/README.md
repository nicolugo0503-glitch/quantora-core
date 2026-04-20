QNT30577 — COMPLIANCE REVIEW QUEUE + INVESTOR VERIFICATION CONSOLE

ADDS
- backend/app/qnt30577_compliance_queue_router.py
- frontend/mission_qnt30577_compliance_queue.html
- backend/artifacts/compliance_review_queue/

UPGRADES
- compliance queue summary
- verification decisions workflow
- cross-investor document and KYC review visibility
- investor portal navigation into compliance queue
- command center entry for QNT30577 Compliance Queue

API
- GET /api/compliance-queue
- GET /api/compliance-queue/summary
- POST /api/compliance-queue/decision
- GET /api/compliance-queue/activity

PURPOSE
- create an institutional verification console for onboarding and compliance review
- centralize investor document and KYC review decisions
- prepare Quantora for compliance operations at scale
