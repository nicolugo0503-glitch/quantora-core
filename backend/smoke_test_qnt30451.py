from backend.qnt30451_portfolio_risk_nerve_center import build_portfolio_risk_package

pkg = build_portfolio_risk_package(
    exposures=[{"id":"e1","book_name":"Core","asset_class":"equities","gross_exposure":125000,"net_exposure":64000,"var_1d":7200}],
    limits=[{"id":"l1","limit_name":"Gross Cap","limit_type":"gross_exposure","threshold_value":150000,"current_value":125000,"status":"ok"}],
    alerts=[{"id":"a1","alert_name":"Sector Alert","severity":"medium","status":"open","target_ref":"core"}],
    stress_tests=[{"id":"s1","scenario_name":"Gap Down","loss_estimate":18000,"capital_impact":22000,"status":"pass"}],
)
assert pkg["summary"]["books_tracked"] == 1
assert pkg["summary"]["gross_exposure"] == 125000.0
assert pkg["summary"]["risk_score"] >= 60
print("QNT30451 smoke test passed")
