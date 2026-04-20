# QNT30658 — Institutional Conversion Engine

Institutional conversion layer merged into the full Quantora system.

## Scope
- converts allocator command into governed commitment lanes
- scores conversion readiness, friction, and closing probability
- supervises onboarding release and subscription launch readiness
- persists audit runs and policy thresholds per authenticated operator

## Endpoints
- `GET /api/institutional-conversion-engine/summary`
- `POST /api/institutional-conversion-engine/run`
- `GET /api/institutional-conversion-engine/audit`
- `POST /api/institutional-conversion-engine/policy`

## Frontend
- `frontend/mission_qnt30658_institutional_conversion_engine.html`
