from fastapi.testclient import TestClient
from user_product_layer import app

client = TestClient(app)

assert client.get("/product/status").status_code == 200
assert client.post("/product/user/register", json={
    "user_id": "client-001",
    "full_name": "Quantora Client",
    "email": "client@example.com",
    "plan": "pro",
    "risk_preset": "balanced"
}).status_code == 200

assert client.post("/product/portfolio/configure", json={
    "user_id": "client-001",
    "target_capital": 50000,
    "risk_preset": "balanced",
    "market_access": ["equities", "crypto"],
    "automation_enabled": True
}).status_code == 200

assert client.get("/product/dashboard/client-001").status_code == 200
assert client.post("/product/service/request", json={
    "user_id": "client-001",
    "action": "enable_ai_execution",
    "payload": {"mode": "paper"}
}).status_code == 200

print("QNT30385 smoke test passed")
