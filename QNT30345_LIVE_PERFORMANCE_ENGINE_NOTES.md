# QNT30345 — Live Performance Engine

Added:
- `/performance/live-status` for live operator visibility
- `frontend/live_performance_panel.html`
- `backend/smoke_test_qnt30345.py`

Purpose:
- show current equity, realized and unrealized PnL
- expose truth alignment and risk-lock state in one place
- provide trade journal and attribution for live monitoring

Validation:
- Python compile check passed
- smoke test passed
