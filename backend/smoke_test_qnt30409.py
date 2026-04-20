from fastapi.testclient import TestClient
from unified_api_gateway_module_router import app

client = TestClient(app)

assert client.get("/api-gateway/status").status_code == 200
assert client.post("/api-gateway/module-health/update", json={
    "module": "broker_bridge",
    "status": "online",
    "health": "green",
    "details": {"mode": "paper"}
}).status_code == 200
assert client.post("/api-gateway/route/upsert", json={
    "module": "state_fabric",
    "path": "/state-fabric/status"
}).status_code == 200
assert client.post("/api-gateway/request/log?module=capital_orchestrator&method=POST").status_code == 200
assert client.post("/api-gateway/demo/run").status_code == 200
assert client.get("/api-gateway/request-log").status_code == 200
print("QNT30409 smoke test passed")
