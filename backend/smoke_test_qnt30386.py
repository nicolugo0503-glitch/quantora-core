from fastapi.testclient import TestClient
from monetization_layer import app

client = TestClient(app)

assert client.get("/monetization/status").status_code == 200
assert client.post("/monetization/customer/register", json={
    "customer_id": "client-001",
    "full_name": "Quantora Client",
    "email": "client@example.com",
    "plan": "pro"
}).status_code == 200

assert client.post("/monetization/subscription/create", json={
    "customer_id": "client-001",
    "plan": "pro",
    "billing_cycle": "monthly",
    "autopay": True
}).status_code == 200

assert client.post("/monetization/invoice/create", json={
    "customer_id": "client-001",
    "amount": 299,
    "currency": "USD",
    "kind": "subscription"
}).status_code == 200

assert client.post("/monetization/performance-fee/accrue", json={
    "customer_id": "client-001",
    "gross_profit": 10000,
    "high_water_mark": 50000
}).status_code == 200

assert client.post("/monetization/api-access/provision", json={
    "customer_id": "client-001",
    "tier": "pro",
    "scopes": ["signals.read", "dashboard.read"]
}).status_code == 200

assert client.get("/monetization/dashboard/client-001").status_code == 200

print("QNT30386 smoke test passed")
