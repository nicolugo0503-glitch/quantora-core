# QNT30720 — Capital Committee Deliberation Layer

This mission adds a governed capital committee layer for high-impact allocation, tilt, hold, and defense decisions.

## Core capabilities
- committee deliberation scoring
- cross-checks against operator, release, safety, fund admin, forensic, recovery, executive, memory, and allocation governance posture
- vote capture for committee outcomes
- alerting when committee blockers are present
- dedicated mission page for supervised committee review

## Main endpoints
- `GET /api/capital-committee-deliberation-layer/summary`
- `POST /api/capital-committee-deliberation-layer/evaluate`
- `POST /api/capital-committee-deliberation-layer/vote`
- `POST /api/capital-committee-deliberation-layer/policy`
- `POST /api/capital-committee-deliberation-layer/bootstrap-demo`
