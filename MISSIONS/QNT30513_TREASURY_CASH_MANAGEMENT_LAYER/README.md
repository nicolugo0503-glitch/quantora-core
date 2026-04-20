QNT30513 — TREASURY + CASH MANAGEMENT LAYER

PURPOSE
Add a treasury and cash management layer so Quantora can track available cash, reserved cash, and fund-level treasury events in a structured way.

ADDS
- qnt30513_treasury_engine.py
- qnt30513_treasury_router.py
- treasury_binding_example.py
- treasury_contract.json
- frontend/mission_qnt30513_treasury.html

ALSO CHANGES
- frontend/index.html (adds QNT30513 Treasury button)
- frontend/conversation_missions_hub.html (adds QNT30513 card)

PRIMARY ENDPOINTS
- POST /api/treasury/cash-event
- POST /api/treasury/reserve
- POST /api/treasury/release
- GET /api/treasury/summary
- GET /api/treasury/ledger

WHAT THIS UNLOCKS
- fund-level cash event tracking
- available cash visibility
- reserved cash handling
- treasury ledger visibility
- deployable treasury workflow in the frontend

STABILITY
Additive only. Minimal frontend button/card patch.
