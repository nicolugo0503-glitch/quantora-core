
from scenario_engine import default_scenario_engine_state, scenario_engine_state_view, define_scenario, run_stress_test, scenario_engine_summary


def main():
    state = scenario_engine_state_view(default_scenario_engine_state())
    define = define_scenario(
        state,
        name="Cross-market liquidity shock",
        shock_type="liquidity_crunch",
        market="multi_market",
        severity=0.42,
        volatility_multiplier=1.9,
        liquidity_haircut=0.31,
        spread_multiplier=2.1,
        correlation_jump=0.22,
    )
    scenario = define["scenario"]
    portfolio_risk = {"summary": {"gross_exposure_usd": 185000, "net_exposure_usd": 94000, "leverage_proxy": 2.35}}
    allocator_state = {"treasury": {"deployable_capital": 60000, "reserve_floor": 25000}}
    autonomy_state = {"summary": {"mode": "delegated_autonomy"}}
    execution_state = {"execution_engine": {"execution_optimizer": {"avg_estimated_slippage_bps": 18.5}}}
    run = run_stress_test(
        state,
        scenario_id=scenario["scenario_id"],
        portfolio_risk=portfolio_risk,
        allocator_state=allocator_state,
        autonomy_state=autonomy_state,
        execution_state=execution_state,
    )
    assert run["verdict"] in ("warn", "fail", "pass")
    assert run["metrics"]["projected_drawdown_pct"] > 0
    assert "recommended_autonomy_mode" in run["governance_actions"]
    summary = scenario_engine_summary(state)
    assert summary["scenarios_defined"] == 1
    assert summary["runs_executed"] == 1
    print("QNT30359 smoke test passed")


if __name__ == "__main__":
    main()
