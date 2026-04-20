from backend.qnt30457_fund_admin_nav_reconciliation_engine import build_fund_admin_package

pkg = build_fund_admin_package(
    nav_entries=[{"id":"n1","as_of_date":"2026-04-05","fund_nav":275000,"nav_per_unit":11.24,"status":"published"}],
    reconciliation_breaks=[{"id":"b1","break_name":"Broker vs Internal NAV Delta","break_type":"position_recon","variance_amount":1850,"status":"open"}],
    subscriptions_redemptions=[{"id":"f1","investor_name":"Founding LP","flow_type":"subscription","amount":50000,"status":"pending"}],
    admin_closes=[{"id":"c1","close_name":"April Month-End Close","period_label":"APR-2026","status":"completed","completed_steps":12,"total_steps":12}],
)
assert pkg["summary"]["nav_entries"] == 1
assert pkg["summary"]["current_fund_nav"] == 275000.0
assert pkg["summary"]["admin_score"] >= 55
print("QNT30457 smoke test passed")
