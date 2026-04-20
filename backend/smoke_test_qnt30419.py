from qnt30419_unified_dashboard_runtime import build_activity_feed, build_operator_brief, build_unified_dashboard_summary

summary = build_unified_dashboard_summary(
    operator={"operator_id": "op_1", "email": "ops@quantora.ai", "display_name": "Quantora Operator"},
    billing={"billing_mode": "simulation", "billing": {"plan": "institutional", "subscription_status": "active"}},
    deployment={"environment": "production", "readiness_score": 92, "overall_status": "ready"},
    attribution={
        "portfolio_attribution": {"allocated_capital": 100000, "used_capital": 24000, "remaining_capital": 76000, "daily_realized_pnl": 1200, "drawdown_pct": 1.4},
        "strategy_attribution": [{"strategy_name": "Alpha", "realized_pnl": 500, "orders_count": 4}],
        "execution_attribution": [{"execution_venue": "alpaca", "avg_execution_quality": 91, "orders_count": 4}],
    },
    strategies={"strategies": [{"strategy_id": "s1", "enabled": True, "status": "running", "name": "Alpha"}]},
    orders=[{"symbol": "AAPL", "side": "buy", "qty": 1, "status": "filled", "mode": "paper", "timestamp": "2026-04-03T00:00:00Z"}],
    runtime_modules=[{"module_id": "billing", "status": "ok", "critical": True}],
)
brief = build_operator_brief(summary)
feed = build_activity_feed(summary)
assert summary["mission"] == "QNT30419"
assert summary["headline"]["plan"] == "institutional"
assert brief["mission"] == "QNT30419"
assert len(feed) >= 1
print("QNT30419 smoke test passed")
