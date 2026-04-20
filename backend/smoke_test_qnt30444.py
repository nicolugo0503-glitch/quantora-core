from backend.qnt30444_investor_operating_layer import build_investor_operating_package

pkg = build_investor_operating_package(
    investors=[{"id":"inv_1","investor_name":"Founding LP","status":"active","committed_capital":250000,"distributed_pnl":12000}],
    pools=[{"id":"pool_1","capital_balance":310000}],
    flows=[{"id":"flow_1","flow_type":"deposit","amount":250000}],
    reports=[{"id":"rep_1","investor_id":"inv_1","investor_name":"Founding LP","report_type":"capital_statement","delivery_status":"sent","generated_nav":262000,"generated_pnl":12000,"created_at":"2026-04-05T00:00:00Z"}],
)
assert pkg["summary"]["active_investors"] == 1
assert pkg["summary"]["reports_sent"] == 1
assert pkg["trust_center"]["trust_score"] >= 80
print("QNT30444 smoke test passed")
