from backend.qnt30455_operator_command_ai_layer import build_operator_ai_package

pkg = build_operator_ai_package(
    commands=[{"id":"c1","command_name":"Rebalance Top Strategies","command_type":"capital_action","target_system":"capital_intelligence","status":"executed"}],
    copilots=[{"id":"cp1","copilot_name":"Allocation Copilot","specialty":"capital_allocation","status":"active","confidence_score":87.5}],
    recommendations=[{"id":"r1","recommendation_name":"Shift To Momentum","priority":"high","status":"approved","target_ref":"momentum_alpha"}],
    decision_logs=[{"id":"d1","decision_name":"Approved Rebalance","operator_action":"approved","outcome":"capital_shift_executed"}],
)
assert pkg["summary"]["commands_total"] == 1
assert pkg["summary"]["copilots_active"] == 1
assert pkg["summary"]["ai_score"] >= 60
print("QNT30455 smoke test passed")
