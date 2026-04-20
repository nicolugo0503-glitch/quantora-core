from backend.qnt30446_distribution_engine import build_distribution_package

pkg = build_distribution_package(
    leads=[{"lead_name":"Prospect A","channel":"organic","status":"qualified","pipeline_value":12000,"owner":"founder"}],
    referrals=[{"referrer_name":"User A","referred_name":"User B","reward_amount":300,"status":"pending"}],
    campaigns=[{"campaign_name":"Campaign A","channel":"x","status":"active","budget":1500,"leads_generated":24}],
    onboarding_flows=[{"flow_name":"Flow A","target_segment":"funds","status":"active","completion_rate":42}],
)
assert pkg["summary"]["total_leads"] == 1
assert pkg["summary"]["active_campaigns"] == 1
assert pkg["engine_health"]["distribution_score"] >= 50
print("QNT30446 smoke test passed")
