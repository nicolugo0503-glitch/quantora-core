from backend.qnt30459_institutional_sales_partnership_engine import build_sales_partnership_package

pkg = build_sales_partnership_package(
    enterprise_leads=[{"id":"l1","account_name":"Northstar Capital","segment":"allocator","status":"qualified","owner":"founder"}],
    opportunities=[{"id":"o1","opportunity_name":"Allocator Pilot","account_name":"Northstar Capital","stage":"proposal","pipeline_value":250000}],
    partnerships=[{"id":"p1","partner_name":"Prime Brokerage Desk","partnership_type":"distribution","status":"active","estimated_value":500000}],
    partner_activities=[{"id":"a1","partner_name":"Prime Brokerage Desk","activity_name":"Co-Sell Intro","status":"planned"}],
)
assert pkg["summary"]["enterprise_leads"] == 1
assert pkg["summary"]["opportunities"] == 1
assert pkg["summary"]["engine_score"] >= 55
print("QNT30459 smoke test passed")
