from fastapi.testclient import TestClient
from autonomous_oversight_governance_control import app

client = TestClient(app)

assert client.get("/governance/status").status_code == 200

sig = client.post("/governance/signal/ingest", json={
    "source": "execution_drift_monitor",
    "metric": "execution_drift",
    "value": 0.22,
    "threshold": 0.15,
    "severity": "critical"
})
assert sig.status_code == 200
assert sig.json()["status"] == "breach_detected"

apr = client.post("/governance/approval/request", json={
    "action_type": "capital_override",
    "requested_by": "governance-admin",
    "summary": "Need review before allocation change"
})
assert apr.status_code == 200
approval_id = apr.json()["approval"]["approval_id"]

dec = client.post("/governance/approval/decide", json={
    "approval_id": approval_id,
    "decided_by": "oversight-lead",
    "decision": "approved",
    "note": "Approved for controlled test"
})
assert dec.status_code == 200

ovr = client.post("/governance/override/set", json={
    "key": "max_daily_loss",
    "value": 30000,
    "reason": "temporary controlled expansion",
    "operator_id": "oversight-lead"
})
assert ovr.status_code == 200

frz = client.post("/governance/freeze?enabled=false&reason=recovered")
assert frz.status_code == 200

print("QNT30398 smoke test passed")
