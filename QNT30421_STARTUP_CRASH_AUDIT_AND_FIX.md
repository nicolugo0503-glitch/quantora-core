# QNT30421 Startup Crash Audit and Fix

## Root cause
QNT30420 deployment hardening blocked startup in production mode when `QUANTORA_APP_BASE_URL` was not set.

On Railway, the app can still have a valid public domain via `RAILWAY_PUBLIC_DOMAIN`, but the old logic treated missing `QUANTORA_APP_BASE_URL` as a critical startup blocker.

## Fix applied
- Infer `QUANTORA_APP_BASE_URL` automatically from `RAILWAY_PUBLIC_DOMAIN` when available.
- Downgrade missing base URL from a production-blocking critical error to a guarded-mode warning.
- Preserve hard blocking for genuinely unsafe conditions like live execution without live billing readiness or broken runtime imports.

## Operational effect
- Railway deployments no longer crash just because `QUANTORA_APP_BASE_URL` is unset.
- Startup doctor still reports guarded/degraded status until canonical config is completed.
- Existing health and deployment endpoints remain intact.
