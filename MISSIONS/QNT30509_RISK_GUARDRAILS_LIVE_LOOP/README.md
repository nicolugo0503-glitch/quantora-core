QNT30509 — RISK GUARDRAILS IN LIVE LOOP

PURPOSE
Add guardrails that can block loop start/resume when live risk conditions are breached, so Quantora gains a real operating safety layer.

ADDS
- qnt30509_risk_guardrails.py
- qnt30509_risk_router.py
- risk_binding_example.py
- risk_guardrails_contract.json
- frontend/mission_qnt30509_risk_guardrails.html

ALSO CHANGES
- frontend/index.html (adds QNT30509 Risk button)
- frontend/conversation_missions_hub.html (adds QNT30509 card)

PRIMARY ENDPOINTS
- GET /api/risk/report

WHAT THIS UNLOCKS
- max notional exposure guardrail
- max drawdown guardrail
- max position count guardrail
- blocked symbol guardrail
- scheduler start/resume blocking on critical breaches
- deployable frontend risk visibility

STABILITY
Additive only. Minimal frontend button/card patch.
