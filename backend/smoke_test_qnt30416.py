from fastapi.testclient import TestClient
from revenue_layer_entitlements import app

client = TestClient(app)
assert client.get("/entitlements/status").status_code == 200
assert client.post("/entitlements/assign", json={"user_id":"u1","plan":"pro","status":"active"}).status_code == 200
assert client.get("/entitlements/user/u1").status_code == 200
assert client.post("/entitlements/check", json={"user_id":"u1","feature":"performance_engine"}).status_code == 200
print("QNT30416 smoke test passed")
