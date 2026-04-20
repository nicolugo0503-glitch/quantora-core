from backend.qnt30452_treasury_cash_liquidity_control_tower import build_treasury_liquidity_package

pkg = build_treasury_liquidity_package(
    cash_accounts=[{"id":"a1","account_name":"Primary Treasury","institution_name":"Mercury","cash_balance":185000,"available_cash":160000,"restricted_cash":25000,"status":"active"}],
    liquidity_buckets=[{"id":"b1","bucket_name":"T0","bucket_amount":60000,"target_amount":50000,"status":"ok"}],
    treasury_flows=[{"id":"f1","flow_name":"Investor Subscription","flow_direction":"inflow","amount":40000,"source_ref":"inv_subscription_1","status":"scheduled"}],
    funding_forecasts=[{"id":"fc1","forecast_name":"7-Day Forecast","projected_cash":145000,"minimum_required":90000,"status":"ok"}],
)
assert pkg["summary"]["accounts_tracked"] == 1
assert pkg["summary"]["total_cash"] == 185000.0
assert pkg["summary"]["treasury_score"] >= 60
print("QNT30452 smoke test passed")
