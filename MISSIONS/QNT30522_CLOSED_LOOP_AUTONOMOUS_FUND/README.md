QNT30522 — CLOSED-LOOP AUTONOMOUS FUND

PURPOSE
Connect signals, learning, allocation, and execution planning into a single closed-loop autonomous workflow.

ADDS
- qnt30522_closed_loop_fund.py
- qnt30522_router.py
- closed_loop_binding_example.py
- closed_loop_contract.json
- frontend/mission_qnt30522_closed_loop.html

ALSO CHANGES
- frontend/mission_registry.json (adds QNT30522 route)

PRIMARY ENDPOINTS
- POST /api/closed-loop/run
- GET /api/closed-loop/cycles

WHAT THIS UNLOCKS
- end-to-end autonomous fund cycle
- adaptive learning feedback in the same loop
- allocation + execution plan generation
- stored cycle history
- deployable UI for closed-loop operation

STABILITY
Additive only. Registry update only for frontend navigation.
