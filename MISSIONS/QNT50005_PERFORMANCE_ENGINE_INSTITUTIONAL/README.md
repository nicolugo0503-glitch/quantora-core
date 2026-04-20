# QNT50005 — Performance Engine (Institutional)

This mission adds the institutional performance intelligence layer to Quantora.

## Added files
- `backend/app/performance_engine/engine.py`
- `backend/app/performance_engine/state_store.py`
- `backend/app/models/performance_engine_models.py`
- `backend/app/qnt50005_performance_engine_institutional_router.py`
- `backend/app/state/performance_engine_state.json`
- `frontend/mission_qnt50005_performance_engine_institutional.html`

## Core capabilities
- Sharpe, Sortino, volatility, and drawdown computation from NAV snapshots
- Strategy-level pnl and return contribution attribution
- Investor metrics for MTD, QTD, YTD, and inception return
- Risk-layer synchronization for drawdown and daily loss signals
