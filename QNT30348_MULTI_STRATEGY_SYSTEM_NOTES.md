# QNT30348 — Multi-Strategy System

## Mission delivered
Quantora now supports portfolio-style strategy orchestration instead of treating each strategy as an isolated runner.

## What was added
- `GET /multi-strategy/status`
  - ranks all strategies by live score
  - shows active vs reserve set
  - includes AI decision snapshot context
- `POST /multi-strategy/optimize`
  - auto-enables highest-ranked strategies
  - auto-pauses weaker or capacity-blocked strategies
  - optionally rebalances strategy capital limits
- `POST /multi-strategy/rebalance`
  - recalculates per-strategy capital limits from the AI allocation snapshot
- automation engine support for optional background optimizer controls:
  - `auto_strategy_optimizer_enabled`
  - `auto_strategy_optimizer_max_active`
  - `auto_strategy_optimizer_min_score`
  - `auto_strategy_optimizer_pause_score`
- new frontend panel:
  - `frontend/multi_strategy_panel.html`
- command center updated with direct navigation to the multi-strategy panel
- new smoke test:
  - `backend/smoke_test_qnt30348.py`

## Scoring model
Each strategy is scored from 0 to 100 using:
- realized PnL
- unrealized PnL
- win rate
- capital utilization
- PnL efficiency versus gross notional
- current signal confidence from the AI signal engine
- lifecycle penalties for paused/stopped strategies
- hard penalty when kill switch is active

## Why this matters
This moves Quantora from "run strategies" to "govern a portfolio of competing strategies".
It creates the operating foundation for:
- dynamic fleet selection
- capital migration to stronger systems
- reserve strategy benches
- future automatic deallocation and strategy retirement logic

## Validation
- Python compile check passed
- `backend/smoke_test_qnt30348.py` passed end-to-end
