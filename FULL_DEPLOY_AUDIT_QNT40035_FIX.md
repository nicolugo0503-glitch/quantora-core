# Quantora QNT40035 Deploy Audit and Fix

## Root cause fixed
The prior package embedded multiple historical `QUANTORA_FULL_PROJECT_*` directories at the zip root, and each of those directories contained its own `Dockerfile`.

That made the deploy surface ambiguous for platforms that auto-detect Dockerfiles and choose a build context heuristically. In that state, the platform could select the wrong Dockerfile and/or build context, which explains the observed failure where `/app/backend` was missing during `docker build` even though the canonical root package contained `backend/`.

## Fixes applied
- Removed embedded historical project bundles from the deploy artifact:
  - `QUANTORA_FULL_PROJECT_QNT30427_PORTFOLIO_RISK_GOVERNANCE`
  - `QUANTORA_FULL_PROJECT_QNT30428_POSITION_EXIT_REDUCE_ENGINE`
  - `QUANTORA_FULL_PROJECT_QNT30429_PNL_ATTRIBUTION_HARDENING`
- Preserved the canonical deploy root with:
  - `backend/`
  - `frontend/`
  - `Dockerfile`
  - `start.sh`
- Hardened Docker runtime:
  - set `PYTHONPATH=/app`
  - standardized default runtime port to `8010`
  - kept explicit filesystem checks in the image build step
- Removed transient cache files (`__pycache__`, `*.pyc`, `*.pyo`)

## Audit checks completed
- canonical root contains `backend/`, `frontend/`, `backend/requirements.txt`, and `backend/app/main.py`
- python dependency install completed successfully from `backend/requirements.txt`
- `compileall` passed for `backend/app`
- targeted smoke test passed for `QNT40035`
- runtime boot succeeded and `/health` responded successfully

## Operational note
The application still reports its existing guarded posture on `/health`:
- `status: degraded`
- `execution_mode: paper`
- `safe_mode.enabled: true`

That is not a Docker build failure. It is the current runtime control posture inside the app.
