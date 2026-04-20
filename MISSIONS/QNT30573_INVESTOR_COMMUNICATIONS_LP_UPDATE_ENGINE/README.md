QNT30573 — INVESTOR COMMUNICATIONS + LP UPDATE ENGINE

ADDS
- backend/app/qnt30573_lp_update_router.py
- frontend/mission_qnt30573_lp_update_engine.html
- backend/artifacts/investor_communications/
- backend/artifacts/lp_update_distribution/

UPGRADES
- LP-style update generation
- CRM-linked recipient selection
- reporting and reconciliation preview inside updates
- distribution log workflow
- investor portal navigation into LP updates
- command center entry for QNT30573 LP Updates

API
- GET /api/lp-updates
- POST /api/lp-updates/generate
- GET /api/lp-updates/latest
- POST /api/lp-updates/distribute
- GET /api/lp-updates/distribution-log

PURPOSE
- create allocator-grade investor communications workflows
- connect fundraising pipeline, reporting, and diligence posture into outgoing updates
- prepare Quantora for systematic LP communications
