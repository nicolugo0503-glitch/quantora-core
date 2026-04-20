QNT30598 — INVESTOR ALLOCATION CONFIRMATION + CONTRACT NOTE REGISTRY

ADDS
- backend/app/qnt30598_allocation_confirmation_router.py
- frontend/mission_qnt30598_allocation_confirmation.html
- backend/artifacts/investor_allocation_confirmations/

UPGRADES
- allocation confirmation summary
- generate confirmation workflow
- deliver confirmation workflow
- acknowledge confirmation workflow
- investor portal navigation into allocation confirmation
- command center entry for QNT30598 Allocation Confirmation

API
- GET /api/allocation-confirmations
- POST /api/allocation-confirmations/generate
- POST /api/allocation-confirmations/deliver
- POST /api/allocation-confirmations/ack
- GET /api/allocation-confirmations/summary

PURPOSE
- create investor-facing allocation confirmations and contract notes
- bridge official nav strikes and capital activity into confirmation outputs
- prepare Quantora for allocator-grade post-valuation confirmation controls
