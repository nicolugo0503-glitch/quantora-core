QNT30502 — LIVE BACKEND CONTROL + STATE ENDPOINTS

PURPOSE
Add the backend contract required by QNT30501 so the deployed control panel can read state and send runtime actions.

ADDS
- qnt30502_router.py
- fastapi_integration_example.py
- sample_state_payload.json

PRIMARY ENDPOINTS
- GET /api/runtime/state
- GET /api/funds/summary
- GET /api/investors/overview
- GET /api/exposure/summary
- POST /api/runtime/control

ALSO ADDS FALLBACK ALIASES
- GET /runtime/state
- GET /funds/summary
- GET /investors/overview
- GET /exposure/summary
- POST /api/qnt30501/runtime-control
- GET /api/qnt30501/runtime-state
- GET /api/qnt30501/fund-summary
- GET /api/qnt30501/investor-overview
- GET /api/qnt30501/exposure-summary

WHAT THIS UNLOCKS
- live polling from QNT30501 frontend page
- real Start / Pause / Resume / Kill requests
- fund rows, investor rows, exposure, and runtime status in one backend router

STABILITY
Additive only. No existing backend files are modified.
