# QNT30346 — AI Decision Layer + Capital Allocation System

## What was added
- New backend decisioning module: `backend/ai_decision_layer.py`
- New API endpoints:
  - `GET /ai-decision/status`
  - `POST /ai-decision/run`
  - `GET /capital-allocation/status`
  - `POST /capital-allocation/rebalance`
- Strategy cycle now routes signals through an AI decision snapshot before execution.
- Signal execution now supports risk-aware fractional sizing via `recommended_qty`.
- New frontend panel: `frontend/ai_decision_panel.html`
- Unified Command Center now links to the AI Decision Layer panel.

## Architecture effect
This inserts an institutional control layer between signal generation and execution:
1. strategy engine generates signal book
2. AI decision layer ranks and risk-scores signals
3. capital allocator assigns deployable capital
4. execution layer only submits decisions marked `execute`

## Guardrails preserved
- existing risk engine remains the hard gate
- existing capital checks remain enforced before order submission
- no schema reset / no rebuild from scratch
- automation loop can consume the upgraded cycle without route changes

## Validation
- FastAPI OpenAPI loaded successfully
- new endpoints exposed successfully
- authenticated flow tested:
  - register/login
  - set capital
  - register strategy
  - decision snapshot
  - capital rebalance
  - AI decision execution cycle
