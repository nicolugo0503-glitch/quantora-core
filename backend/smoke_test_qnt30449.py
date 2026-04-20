from backend.qnt30449_institutional_reporting_lp_statements import build_lp_reporting_package

pkg = build_lp_reporting_package(
    statements=[{"id":"s1","investor_name":"LP A","statement_type":"lp_statement","period_label":"MTD","nav_amount":100000,"pnl_amount":5400,"delivery_status":"sent"}],
    nav_snapshots=[{"id":"n1","as_of_date":"2026-04-05","fund_nav":250000,"gross_pnl":18000,"net_pnl":14500}],
    distributions=[{"id":"d1","investor_name":"LP A","distribution_type":"cash_distribution","amount":5000,"status":"scheduled"}],
    reporting_cycles=[{"id":"c1","cycle_name":"April Cycle","period_label":"APR-2026","status":"active","statements_expected":10,"statements_completed":4}],
)
assert pkg["summary"]["statements_total"] == 1
assert pkg["summary"]["current_fund_nav"] == 250000.0
assert pkg["summary"]["active_cycles"] == 1
print("QNT30449 smoke test passed")
