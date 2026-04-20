# QNT30653 — Multi-Fund Architecture

## Institutional objective
Convert Quantora from a single-vehicle operating system into a governed multi-fund architecture with master, feeder, and sleeve-aware capital routing.

## Added in this merge
- Backend router: `backend/app/qnt30653_multi_fund_architecture_router.py`
- Frontend mission page: `frontend/mission_qnt30653_multi_fund_architecture.html`
- Main app wiring in `backend/app/main.py`
- Mission registry update in `frontend/mission_registry.json`
- Manifest update in `QUANTORA_FULL_PROJECT_MANIFEST.json`

## New endpoints
- `GET /api/multi-fund-architecture/summary`
- `POST /api/multi-fund-architecture/run`
- `GET /api/multi-fund-architecture/audit`
- `POST /api/multi-fund-architecture/policy`

## Core behavior
- Seeds governed fund vehicles from QNT30650 strategic product decisions
- Incorporates QNT30651 growth posture and QNT30652 compliance release state
- Produces fund matrix, vehicle stack, cross-fund flow plan, and overlap constraints
- Stores persistent per-user architecture state in `backend/artifacts/multi_fund_architecture/`
