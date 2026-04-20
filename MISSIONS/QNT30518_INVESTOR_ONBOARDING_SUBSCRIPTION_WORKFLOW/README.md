QNT30518 — INVESTOR ONBOARDING + SUBSCRIPTION WORKFLOW

PURPOSE
Add investor onboarding and subscription workflow management so Quantora can handle investor intake, review, and subscription requests at the platform layer.

ADDS
- qnt30518_onboarding_engine.py
- qnt30518_onboarding_router.py
- onboarding_binding_example.py
- onboarding_contract.json
- frontend/mission_qnt30518_onboarding.html

ALSO CHANGES
- frontend/index.html (adds QNT30518 Onboarding button)
- frontend/conversation_missions_hub.html (adds QNT30518 card)

PRIMARY ENDPOINTS
- POST /api/onboarding/create
- POST /api/onboarding/status
- POST /api/subscription/request
- POST /api/subscription/approve
- POST /api/subscription/reject
- GET /api/onboarding/summary

WHAT THIS UNLOCKS
- investor onboarding intake
- onboarding review status
- investor subscription requests
- subscription approval / rejection workflow
- deployable investor intake workflow in the frontend

STABILITY
Additive only. Minimal frontend button/card patch.
