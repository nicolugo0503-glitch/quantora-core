# QNT30355 — Portfolio Risk Fabric + Cross-Market Exposure Netting

## Objective
Extend Quantora from venue-aware execution into portfolio-aware institutional risk orchestration.

## What was added
- `backend/portfolio_risk_fabric.py`
- `GET /portfolio-risk/status`
- `POST /portfolio-risk/exposures/upsert`
- `POST /portfolio-risk/netting/evaluate`
- `POST /portfolio-risk/limits/evaluate`
- `frontend/portfolio_risk_fabric_panel.html`
- `backend/smoke_test_qnt30355.py`

## Portfolio Risk Fabric
The new fabric normalizes positions into USD notional, stores signed exposures, buckets risk by market, and groups concentration using correlation families. It now tracks:
- gross notional
- net notional
- largest symbol notional
- portfolio leverage proxy
- hedge coverage ratio

## Cross-Market Netting
The netting layer computes offset-aware residual risk instead of only raw gross exposure. This provides:
- equities vs futures offset awareness
- crypto vs FX overlay adjustment
- diversification scoring
- residual net exposure telemetry

## Limit Evaluation
Risk now evaluates portfolio-level breaches for:
- gross notional
- net notional
- single-symbol concentration
- per-market exposure
- correlated group concentration
- leverage proxy

## Why this matters
Quantora now sees risk as a portfolio fabric rather than disconnected orders or brokers. That is a prerequisite for allocator-grade autonomy, cross-market capital scaling, and investor-grade governance.
