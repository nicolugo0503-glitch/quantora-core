# QNT-REAL01A — Operator Mode + Live Execution Activation

## Objective
Reduce visible control-surface complexity while preserving the full institutional backend.

## Added
- simplified default `frontend/index.html`
- preserved prior UI as `frontend/institutional_console.html`
- `backend/app/qntreal01a_operator_cockpit_router.py`
- GitHub deploy hardening via `.github/workflows/docker-build.yml`
- nested-context-tolerant Dockerfile
- Mac GitHub deploy script `0_DEPLOY_TO_GITHUB.command`

## Operator endpoints
- `GET /operator/health`
- `GET /operator/summary`
- `POST /operator/mode`
- `POST /operator/safe-mode`
- `POST /operator/kill-switch`
