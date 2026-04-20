# QNT50005 — Performance Engine (Institutional)

Quantora now includes an institutional performance measurement layer connected to NAV snapshots, strategy attribution, and risk telemetry.

## What was added
- Dedicated `performance_engine` package with persisted state and recomputation engine
- Router with health, summary, return-series, attribution, investor-metrics, snapshot, configuration, and recompute endpoints
- Risk synchronization so latest drawdown and daily loss can update QNT50004 thresholds context
- Frontend mission page, mission registry entry, mission directory, and smoke test

## Institutional metrics delivered
- Cumulative return
- Annualized return
- Annualized volatility
- Sharpe ratio
- Sortino ratio
- Calmar ratio
- Max/current drawdown
- Best and worst day
- Win rate
- MTD, QTD, YTD, inception return

This mission was added into the same reference package structure and only extended the system with QNT50005 files.
