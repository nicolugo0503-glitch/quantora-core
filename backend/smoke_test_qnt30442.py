from qnt30442_capital_intelligence import build_capital_intelligence_package


def run():
    package = build_capital_intelligence_package(
        strategies=[
            {"strategy_key": "momentum_alpha", "display_name": "Momentum Alpha", "status": "active"},
            {"strategy_key": "breakout_v2", "display_name": "Breakout V2", "status": "active"},
        ],
        allocations=[
            {"strategy_key": "momentum_alpha", "allocated_capital": 12000, "reserve_capital": 1000, "status": "active"},
            {"strategy_key": "breakout_v2", "allocated_capital": 12000, "reserve_capital": 1000, "status": "active"},
        ],
        positions=[
            {"strategy_key": "momentum_alpha", "market_value": 9500, "unrealized_pnl": 420, "realized_pnl": 160},
            {"strategy_key": "breakout_v2", "market_value": 10800, "unrealized_pnl": -310, "realized_pnl": -90},
        ],
        fills=[
            {"strategy_key": "momentum_alpha", "fill_value": 12000, "fill_price": 100, "qty": 120},
            {"strategy_key": "breakout_v2", "fill_value": 15000, "fill_price": 100, "qty": 150},
        ],
    )
    assert package["summary"]["strategy_count"] == 2
    assert package["strategies"][0]["strategy_key"] == "momentum_alpha"
    assert package["recommendations"], "expected rebalance recommendations"
    print("QNT30442 smoke test passed")


if __name__ == "__main__":
    run()
