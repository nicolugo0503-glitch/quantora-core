from backend.qnt30448_execution_governance_audit import build_execution_governance_package

pkg = build_execution_governance_package(
    rules=[{"id":"r1","rule_name":"Max Drift","rule_type":"allocation_limit","threshold_value":10000,"status":"active"}],
    approvals=[{"id":"a1","plan_id":"p1","plan_name":"Increase Momentum","decision":"approved","reviewer":"operator","created_at":"2026-04-05T00:00:00Z"}],
    audit_events=[{"id":"e1","event_type":"plan_executed","actor":"system","target_ref":"p1","status":"logged","created_at":"2026-04-05T00:00:00Z"}],
    execution_failures=[{"id":"f1","execution_id":"x1","failure_type":"broker_reject","severity":"high","status":"open","created_at":"2026-04-05T00:00:00Z"}],
)
assert pkg["summary"]["active_rules"] == 1
assert pkg["summary"]["approvals_logged"] == 1
assert pkg["summary"]["audit_events"] == 1
print("QNT30448 smoke test passed")
