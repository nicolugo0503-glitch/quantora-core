from backend.qnt30456_institutional_compliance_diligence_vault import build_compliance_vault_package

pkg = build_compliance_vault_package(
    policies=[{"id":"p1","policy_name":"Best Execution Policy","policy_type":"trading_governance","owner":"compliance","status":"active"}],
    diligence_requests=[{"id":"d1","request_name":"Allocator DDQ Packet","requester":"allocator_ops","status":"open","priority":"high"}],
    certifications=[{"id":"c1","certification_name":"Internal Control Review","issuing_body":"internal_audit","status":"valid","expires_at":"2027-04-05"}],
    disclosures=[{"id":"x1","disclosure_name":"Quarterly Risk Disclosure","audience":"investors","status":"draft","due_at":"2026-06-30"}],
)
assert pkg["summary"]["policies_total"] == 1
assert pkg["summary"]["certifications_valid"] == 1
assert pkg["summary"]["compliance_score"] >= 55
print("QNT30456 smoke test passed")
