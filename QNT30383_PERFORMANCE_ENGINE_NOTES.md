# QNT30383 — Performance Engine

## Purpose
Quantora performance intelligence layer for PnL tracking, drawdown monitoring, Sharpe estimation, and strategy ranking.

## Included
- trade ingestion endpoint
- batch trade ingestion
- realized PnL tracking
- portfolio-level equity curve
- Sharpe estimation
- drawdown tracking
- win-rate tracking
- strategy rankings
- audit log
- frontend performance operations panel
- smoke test

## Core endpoints
- GET /performance/status
- POST /performance/trade/ingest
- POST /performance/trades/batch
- GET /performance/portfolio
- GET /performance/strategies
- GET /performance/rankings
- GET /performance/strategy/{strategy_id}
- GET /performance/audit

## Integration path
QNT30379 -> QNT30380 -> QNT30381 -> QNT30382 -> QNT30383

## Role in the system
This mission converts execution history into capital intelligence.
It is the measurement layer required before autonomous portfolio management and commercial productization.
