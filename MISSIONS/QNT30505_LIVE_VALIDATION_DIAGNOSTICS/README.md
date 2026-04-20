QNT30505 — LIVE VALIDATION + DIAGNOSTICS

PURPOSE
Add a deployable diagnostics layer so Quantora can prove whether it is truly live across runtime, fund, investor, and exposure data.

ADDS
- qnt30505_diagnostics_router.py
- diagnostics_binding_example.py
- diagnostics_contract.json
- frontend/mission_qnt30505_live_diagnostics.html

ALSO CHANGES
- frontend/index.html (adds QNT30505 Diagnostics button)
- frontend/conversation_missions_hub.html (adds QNT30505 card)

PRIMARY ENDPOINTS
- GET /api/diagnostics/live-validation
- GET /api/diagnostics/health-summary

WHAT THIS UNLOCKS
- explicit validation of live readiness
- deployable diagnostics page in the frontend
- visibility into which subsystem is blocking true live mode

STABILITY
Additive only. Minimal frontend button/card patch.
