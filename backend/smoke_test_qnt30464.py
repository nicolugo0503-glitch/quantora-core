from backend.qnt30464_global_capital_network_multi_fund_orchestration import build_global_capital_network_package

pkg = build_global_capital_network_package(
    funds=[{"id":"f1","fund_name":"Quantora Global Alpha I","jurisdiction":"Cayman","capital_base":2500000,"status":"active"}],
    capital_transfers=[{"id":"t1","from_fund":"Quantora Global Alpha I","to_fund":"Quantora Tactical Fund","amount":250000,"status":"completed"}],
    allocation_links=[{"id":"l1","source_fund":"Quantora Global Alpha I","target_strategy":"Momentum Alpha","allocation_weight":0.32,"status":"active"}],
    orchestration_cycles=[{"id":"c1","cycle_name":"Weekly Global Rebalance","status":"completed","actions_count":8}],
)
assert pkg["summary"]["funds_total"] == 1
assert pkg["summary"]["network_capital"] == 2500000.0
assert pkg["summary"]["network_score"] >= 55
print("QNT30464 smoke test passed")
