# QNT30703 — Live Broker Safety Layer

## Purpose
Institutional capital firewall that blocks trades failing pre-execution safety rules before broker dispatch.

## Included
- Backend router: `backend/app/qnt30703_live_broker_safety_layer_router.py`
- Frontend mission panel: `frontend/mission_qnt30703_live_broker_safety_layer.html`
- Mission registry wiring
- Main app router include
- Smoke test: `backend/test_qnt30703_smoke.py`

## Core controls
- Max position sizing by capital base
- Max risk per trade via stop-loss distance
- Max daily drawdown lock
- Max total open exposure
- Max strategy exposure
- Max symbol exposure
- Correlation stacking guard
- Kill switch, execution pause, operator override gate
- Worst-case-loss simulation with slippage

## Endpoints
- `GET /api/live-broker-safety-layer/summary`
- `POST /api/live-broker-safety-layer/run`
- `POST /api/live-broker-safety-layer/evaluate-trade`
- `POST /api/live-broker-safety-layer/policy`
- `POST /api/live-broker-safety-layer/controls`
- `POST /api/live-broker-safety-layer/bootstrap-demo`
