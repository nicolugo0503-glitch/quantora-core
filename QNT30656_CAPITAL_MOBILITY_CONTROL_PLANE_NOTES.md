# QNT30656 — Capital Mobility Control Plane

Quantora now extends beyond treasury readiness into governed capital movement supervision.

## Institutional purpose
- decide which capital corridors can actually move capital now
- translate jurisdiction, vehicle, and reserve constraints into mobility passports
- queue transfers based on treasury ladder capacity and corridor readiness
- supervise reserve release before cross-border dispatch

## Backend surface
- `GET /api/capital-mobility-control-plane/summary`
- `POST /api/capital-mobility-control-plane/run`
- `GET /api/capital-mobility-control-plane/audit`
- `POST /api/capital-mobility-control-plane/policy`

## Dependencies
- QNT30650 Strategic Decision Layer
- QNT30652 Institutional Compliance Layer
- QNT30653 Multi-Fund Architecture
- QNT30654 Global Capital Network
- QNT30655 Sovereign Treasury Command

## Core outputs
- mobility overview and control plane posture
- entity passports
- mobility corridors
- transfer queues
- reserve release matrix
- mobility actions and run audit
