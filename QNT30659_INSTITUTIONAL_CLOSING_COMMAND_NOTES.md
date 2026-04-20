# QNT30659 — Institutional Closing Command

## Mission intent
Promote Quantora from conversion readiness into governed final close authority.

## What this layer does
- Ranks institutional closes by final close readiness.
- Scores packet readiness and settlement readiness.
- Produces a settlement matrix tied to treasury and mobility posture.
- Generates a final release queue for institutional closing committee action.
- Persists run audits and policy thresholds per operator session.

## Core endpoints
- `GET /api/institutional-closing-command/summary`
- `POST /api/institutional-closing-command/run`
- `GET /api/institutional-closing-command/audit`
- `POST /api/institutional-closing-command/policy`

## Dependency chain
- QNT30658 Institutional Conversion Engine
- QNT30656 Capital Mobility Control Plane
- QNT30655 Sovereign Treasury Command
- Existing fund close infrastructure

## Institutional outcome
Quantora can now decide which institutional commitments are not only conversion-ready, but governance-cleared, settlement-ready, and authorized for final close execution.
