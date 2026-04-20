from fastapi.testclient import TestClient
from production_control_plane import app

client = TestClient(app)

assert client.get("/control-plane/health").status_code == 200
assert client.get("/control-plane/readiness").status_code == 200

r = client.post("/control-plane/controls/update", json={
    "global_trading_enabled": False,
    "maintenance_mode": False,
    "live_execution_mode": False,
    "paper_mode_only": True
})
assert r.status_code == 200

r = client.post("/control-plane/deployment/register", json={
    "actor": "quantora-ops",
    "release_version": "qnt30387-smoke",
    "environment": "staging"
})
assert r.status_code == 200

r = client.post("/control-plane/incident/create", json={
    "title": "Broker adapter latency spike",
    "severity": "P1",
    "service_name": "qnt30382_broker_integration"
})
assert r.status_code == 200
incident_id = r.json()["incident"]["incident_id"]

r = client.post("/control-plane/incident/resolve", json={
    "incident_id": incident_id,
    "resolution": "Recovered broker adapter and restored health"
})
assert r.status_code == 200

assert client.get("/control-plane/services").status_code == 200
assert client.get("/control-plane/observability").status_code == 200

print("QNT30387 smoke test passed")
