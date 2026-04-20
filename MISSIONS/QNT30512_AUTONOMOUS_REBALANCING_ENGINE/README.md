QNT30512 — AUTONOMOUS REBALANCING ENGINE

PURPOSE
Add a backend rebalancing engine and deployable frontend page so Quantora can convert portfolio drift into a concrete rebalance plan and execution payload.

ADDS
- qnt30512_autonomous_rebalancing_engine.py
- qnt30512_rebalance_router.py
- rebalance_binding_example.py
- rebalance_contract.json
- frontend/mission_qnt30512_rebalancing.html

ALSO CHANGES
- frontend/index.html (adds QNT30512 Rebalance button)
- frontend/conversation_missions_hub.html (adds QNT30512 card)

PRIMARY ENDPOINTS
- POST /api/rebalance/build
- GET /api/rebalance/plan
- POST /api/rebalance/execute
- GET /api/rebalance/execution

WHAT THIS UNLOCKS
- target vs actual rebalance planning
- drift-based order generation
- dry-run broker execution payloads
- deployable UI for rebalancing workflows

STABILITY
Additive only. Minimal frontend button/card patch.
