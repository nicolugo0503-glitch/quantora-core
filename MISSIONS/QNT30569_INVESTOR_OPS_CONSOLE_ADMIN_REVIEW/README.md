QNT30569 — INVESTOR OPS CONSOLE + ADMIN REVIEW

ADDS
- backend/app/qnt30569_investor_ops_router.py
- frontend/mission_qnt30569_investor_ops_console.html
- backend/artifacts/investor_ops_console/
- backend/artifacts/investor_admin_reviews/

UPGRADES
- investor ops summary across capital, performance, funding, reporting, and reconciliation
- investor review request workflow
- review decision workflow
- investor portal navigation into investor ops
- command center entry for QNT30569 Investor Ops

API
- GET /api/investor-ops/summary
- GET /api/investor-ops/history
- GET /api/investor-admin/reviews
- POST /api/investor-admin/review-request
- POST /api/investor-admin/review-decision

PURPOSE
- create an operational support surface for investor lifecycle management
- centralize issue review across funding, reconciliation, and reporting workflows
- prepare Quantora for real investor operations handling
