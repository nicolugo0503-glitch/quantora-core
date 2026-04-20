from backend.qnt30454_revenue_intelligence_unit_economics import build_revenue_intelligence_package

pkg = build_revenue_intelligence_package(
    customer_segments=[{"id":"s1","segment_name":"Independent Traders","customers":42,"mrr":12450,"churn_percent":3.2}],
    revenue_events=[{"id":"r1","revenue_name":"Monthly SaaS Billing","revenue_type":"subscription","amount":12450,"status":"recognized"}],
    cost_centers=[{"id":"c1","cost_name":"Infrastructure Spend","category":"infrastructure","monthly_cost":3400,"status":"active"}],
    unit_economics_snapshots=[{"id":"u1","period_label":"APR-2026","ltv":6800,"cac":850,"payback_months":4.2,"gross_margin_percent":78}],
)
assert pkg["summary"]["segments_tracked"] == 1
assert pkg["summary"]["gross_revenue"] == 12450.0
assert pkg["summary"]["economics_score"] >= 60
print("QNT30454 smoke test passed")
