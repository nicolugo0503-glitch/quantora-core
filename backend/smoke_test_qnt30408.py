from fastapi.testclient import TestClient
from unified_state_fabric_event_ledger import app

client = TestClient(app)

assert client.get("/state-fabric/status").status_code == 200
assert client.post("/state-fabric/global/update", json={
    "runtime_mode": "active",
    "risk_state": "safe",
    "capital_state": "deployable",
    "broker_state": "paper_connected",
    "governance_state": "active"
}).status_code == 200
assert client.post("/state-fabric/module/update", json={
    "module": "execution",
    "status": "online",
    "health": "green"
}).status_code == 200
assert client.post("/state-fabric/event/publish", json={
    "topic": "test.topic",
    "payload": {"message": "hello"}
}).status_code == 200
assert client.post("/state-fabric/snapshot").status_code == 200
assert client.get("/state-fabric/ledger").status_code == 200
print("QNT30408 smoke test passed")
