QNT30514 — CAPITAL CALLS + REDEMPTION WORKFLOW

PURPOSE
Add investor capital call and redemption workflow management so Quantora can begin handling real capital movement requests at the fund layer.

ADDS
- qnt30514_capital_workflow_engine.py
- qnt30514_capital_workflow_router.py
- capital_workflow_binding_example.py
- capital_workflow_contract.json
- frontend/mission_qnt30514_capital_workflow.html

ALSO CHANGES
- frontend/index.html (adds QNT30514 Capital button)
- frontend/conversation_missions_hub.html (adds QNT30514 card)

PRIMARY ENDPOINTS
- POST /api/capital/call
- POST /api/capital/call/fulfill
- POST /api/redemption/request
- POST /api/redemption/approve
- POST /api/redemption/reject
- GET /api/capital/summary

WHAT THIS UNLOCKS
- capital call issuance
- redemption request intake
- capital call fulfillment
- redemption approval / rejection states
- deployable workflow visibility in the frontend

STABILITY
Additive only. Minimal frontend button/card patch.
