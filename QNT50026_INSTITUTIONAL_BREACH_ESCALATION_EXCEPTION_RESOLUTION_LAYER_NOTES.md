# QNT50026 — Institutional Breach Escalation + Exception Resolution Layer

This mission adds an institutional control surface for breach registration, escalation, and exception resolution.

## Added
- Breach case registry with directive lineage
- Escalation log for supervisory and operations review
- Exception resolution ledger with approval gating
- Context sync against risk, settlement, control loop, and charter layers

## Primary backend endpoints
- `GET /institutional-breach/health`
- `GET /institutional-breach/summary`
- `GET /institutional-breach/cases`
- `GET /institutional-breach/resolutions`
- `GET /institutional-breach/escalations`
- `POST /institutional-breach/configure`
- `POST /institutional-breach/sync-context`
- `POST /institutional-breach/register-case`
- `POST /institutional-breach/escalate`
- `POST /institutional-breach/resolve`
- `POST /institutional-breach/reset`
