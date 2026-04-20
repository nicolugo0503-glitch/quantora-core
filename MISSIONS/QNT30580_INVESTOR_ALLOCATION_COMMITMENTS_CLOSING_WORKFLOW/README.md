QNT30580 — INVESTOR ALLOCATION COMMITMENTS + CLOSING WORKFLOW

ADDS
- backend/app/qnt30580_allocation_closing_router.py
- frontend/mission_qnt30580_allocation_closing.html
- backend/artifacts/investor_allocation_commitments/

UPGRADES
- allocation commitment summary
- create commitment workflow
- close commitment workflow
- investor portal navigation into closing workflow
- command center entry for QNT30580 Closing Workflow

API
- GET /api/allocation-commitments
- POST /api/allocation-commitments/create
- POST /api/allocation-commitments/close
- GET /api/allocation-commitments/summary

PURPOSE
- create a structured investor commitment and closing layer
- transition commitments into closed allocations as the fundraising cycle finalizes
- prepare Quantora for close management across investors
