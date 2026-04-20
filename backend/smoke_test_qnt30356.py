
from allocator_intelligence import (
    allocator_intelligence_state_view,
    allocator_summary,
    build_allocator_snapshot,
    default_allocator_intelligence_state,
    propose_rebalance,
    release_reserve,
    update_treasury_policy,
)
from portfolio_risk_fabric import default_portfolio_risk_state, upsert_exposure, build_risk_snapshot


def main():
    alloc = allocator_intelligence_state_view(default_allocator_intelligence_state())
    operator_state = {
        "strategies": {"strategies": [
            {"strategy_id": "strat_aapl", "name": "AAPL Momentum", "symbol": "AAPL", "enabled": True, "capital_limit": 12000},
            {"strategy_id": "strat_btc", "name": "BTC Breakout", "symbol": "BTCUSD", "enabled": True, "capital_limit": 15000},
            {"strategy_id": "strat_es", "name": "ES Hedge", "symbol": "ES1!", "enabled": True, "capital_limit": 9000},
        ]},
        "strategy_engine": {"metrics": {
            "strat_aapl": {"realized_pnl": 1200, "unrealized_pnl": 180, "win_rate": 0.62, "orders_count": 12, "capital_in_use": 11000},
            "strat_btc": {"realized_pnl": 1900, "unrealized_pnl": 220, "win_rate": 0.58, "orders_count": 16, "capital_in_use": 14000},
            "strat_es": {"realized_pnl": 450, "unrealized_pnl": -50, "win_rate": 0.55, "orders_count": 8, "capital_in_use": 7000},
        }}
    }
    risk = default_portfolio_risk_state()
    upsert_exposure(risk, symbol="AAPL", market="equities", side="long", qty=100, mark_price=180, beta=1.1, strategy_id="strat_aapl")
    upsert_exposure(risk, symbol="BTCUSD", market="crypto", side="long", qty=0.4, mark_price=68000, beta=1.4, strategy_id="strat_btc")
    upsert_exposure(risk, symbol="ES1!", market="futures", side="short", qty=1, mark_price=18000, beta=0.8, strategy_id="strat_es", hedge_tag="index_hedge")
    build_risk_snapshot(risk)
    update_treasury_policy(alloc, total_capital_usd=250000, reserve_ratio_target=0.2, min_reserve_usd=30000, max_deploy_ratio=0.8)
    snapshot = build_allocator_snapshot(alloc, operator_state=operator_state, portfolio_risk=risk)
    assert snapshot["treasury"]["total_capital_usd"] == 250000
    result = propose_rebalance(alloc, operator_state=operator_state, portfolio_risk=risk, market_bias="neutral")
    assert result["status"] == "ok"
    assert len(result["proposals"]) == 3
    released = release_reserve(alloc, amount_usd=5000, reason="governed_deploy")
    assert released["released_usd"] >= 0
    summary = allocator_summary(alloc)
    assert summary["strategies"] == 3, summary
    print("QNT30356 smoke test passed")


if __name__ == "__main__":
    main()
