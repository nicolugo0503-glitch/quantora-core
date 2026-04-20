from qnt30443_real_fund_mode import build_real_fund_mode_package


def main():
    pkg = build_real_fund_mode_package(
        pools=[
            {"id": "pool_1", "name": "Primary Treasury", "pool_type": "operating", "capital_balance": 120000, "allocated_capital": 70000, "reserve_capital": 10000, "currency": "USD", "status": "active"},
            {"id": "pool_2", "name": "Investor Sleeve", "pool_type": "investor", "capital_balance": 80000, "allocated_capital": 40000, "reserve_capital": 5000, "currency": "USD", "status": "active"},
        ],
        investors=[
            {"id": "inv_1", "investor_name": "Alpha LP", "committed_capital": 75000, "distributed_pnl": 3000, "status": "active"},
            {"id": "inv_2", "investor_name": "Beta Family Office", "committed_capital": 45000, "distributed_pnl": -500, "status": "active"},
        ],
        flows=[
            {"id": "flow_1", "flow_type": "deposit", "amount": 50000, "created_at": "2026-04-05T10:00:00Z"},
            {"id": "flow_2", "flow_type": "withdrawal", "amount": 5000, "created_at": "2026-04-06T10:00:00Z"},
        ],
        allocations=[
            {"strategy_key": "momentum_alpha", "allocated_capital": 65000, "status": "active"},
            {"strategy_key": "mean_reversion", "allocated_capital": 45000, "status": "active"},
        ],
        positions=[
            {"strategy_key": "momentum_alpha", "realized_pnl": 1200, "unrealized_pnl": 800},
            {"strategy_key": "mean_reversion", "realized_pnl": -300, "unrealized_pnl": 200},
        ],
    )
    assert pkg["summary"]["module"] == "QNT30443"
    assert pkg["summary"]["pool_count"] == 2
    assert pkg["summary"]["investor_count"] == 2
    assert pkg["summary"]["top_strategy"] == "momentum_alpha"
    assert pkg["summary"]["fund_nav"] > 0
    print("QNT30443 smoke test passed")


if __name__ == "__main__":
    main()
