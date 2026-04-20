# QNT30420 — Production Deployment Hardening

This mission adds a production safety spine above the Quantora runtime.

## Included
- Startup Doctor and environment classifier
- `/health`, `/health/runtime`, `/health/billing`, `/health/persistence`, `/health/execution`, `/health/attribution`, `/health/deployment`
- Safe mode summary with guarded/read-only behavior
- Deployment verification script: `backend/verify_deployment.py`
- Operator UI: `frontend/deployment_hardening_panel.html`

## Safety model
- Local environments can boot degraded for development
- Production blocks startup on critical readiness failures
- `QUANTORA_ALLOW_UNSAFE_STARTUP=true` can override blocking for emergency recovery only

## Recommended Railway variables
- `QUANTORA_ENV=production`
- `QUANTORA_APP_BASE_URL=https://<your-domain>`
- `QUANTORA_EXECUTION_MODE=paper` until canonical live path is approved
- all Stripe variables from QNT30417.1 when live billing is enabled
