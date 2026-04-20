from backend.qnt30453_investor_crm_capital_raise_pipeline import build_investor_crm_package

pkg = build_investor_crm_package(
    prospects=[{"id":"p1","prospect_name":"Northstar FO","investor_type":"family_office","stage":"qualified","target_commitment":250000,"owner":"founder"}],
    meetings=[{"id":"m1","prospect_name":"Northstar FO","meeting_type":"dd_call","status":"scheduled","scheduled_at":"2026-04-10T15:00:00Z"}],
    raise_rounds=[{"id":"r1","round_name":"Strategic LP Round","target_amount":2000000,"soft_commit_amount":450000,"funded_amount":150000,"status":"active"}],
    outreach_events=[{"id":"o1","prospect_name":"Northstar FO","channel":"email","outreach_type":"follow_up","status":"sent"}],
)
assert pkg["summary"]["prospects_total"] == 1
assert pkg["summary"]["live_rounds"] == 1
assert pkg["summary"]["crm_score"] >= 60
print("QNT30453 smoke test passed")
