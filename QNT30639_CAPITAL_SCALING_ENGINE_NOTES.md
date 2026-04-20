
# QNT30639 - Capital Scaling Engine

## What was added
- Investor inflow queue with automatic tier classification.
- Multi-vehicle capital scaling plan generator with reserve floor enforcement.
- Capital deployment workflow that updates vehicle NAVs and commits queued inflows.
- Audit trail for inflow registration, plan generation, tier updates, and deployment.
- New institutional frontend panel: `frontend/capital_scaling_engine_panel.html`.

## Key routes
- `GET /capital-scaling/status`
- `POST /capital-scaling/inflows/register`
- `POST /capital-scaling/tiers/update`
- `POST /capital-scaling/plan`
- `POST /capital-scaling/deploy`
- `GET /capital-scaling/audit`
