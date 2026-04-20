# QNT30429 — PnL / Attribution Hardening

Added:
- `/workspace/pnl/summary`
- `/workspace/attribution/strategies`
- `/workspace/attribution/symbols`

What it does:
- aggregates realized and unrealized PnL from org positions
- summarizes fills/orders/open and closed positions
- provides attribution by strategy and by symbol
- surfaces these views in `frontend/org_execution_capital_engine.html`

Acceptance:
- existing execution path continues to work
- PnL summary endpoint responds
- strategy attribution endpoint responds
- symbol attribution endpoint responds
