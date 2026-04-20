from backend.qnt30447_autonomous_capital_layer import build_autonomous_capital_package

pkg = build_autonomous_capital_package(
    strategies=[{"strategy_id":"s1","strategy_name":"Momentum Alpha","score":82,"allocated_capital":20000}],
    pools=[{"id":"p1","capital_balance":50000}],
    plans=[{"id":"plan_1","plan_name":"Increase Momentum","strategy_name":"Momentum Alpha","action_type":"rebalance","amount":5000,"status":"approved"}],
    executions=[{"id":"exec_1","plan_name":"Increase Momentum","broker_name":"alpaca","action_type":"rebalance","amount":5000,"status":"applied"}],
)
assert pkg["summary"]["tracked_strategies"] == 1
assert pkg["summary"]["approved_plans"] == 1
assert pkg["summary"]["executed_actions"] == 1
print("QNT30447 smoke test passed")
