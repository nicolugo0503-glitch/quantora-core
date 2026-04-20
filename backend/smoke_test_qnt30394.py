from fastapi.testclient import TestClient
from postgres_production_persistence import app

client = TestClient(app)

assert client.get("/postgres/status").status_code == 200
assert client.post("/postgres/env/update", json={
    "database_url_present": True,
    "pool_size": 12,
    "ssl_mode": "require"
}).status_code == 200
assert client.post("/postgres/migrations/apply").status_code == 200
assert client.post("/postgres/tenants/create", json={
    "tenant_id": "tenant-001",
    "tenant_name": "Quantora Capital",
    "plan": "pro"
}).status_code == 200
assert client.post("/postgres/users/create", json={
    "user_id": "user-001",
    "tenant_id": "tenant-001",
    "email": "admin@example.com",
    "role": "owner"
}).status_code == 200
assert client.post("/postgres/strategies/create", json={
    "strategy_id": "strat-001",
    "tenant_id": "tenant-001",
    "name": "Execution Alpha",
    "status": "active"
}).status_code == 200
assert client.post("/postgres/orders/create", json={
    "order_id": "ord-001",
    "tenant_id": "tenant-001",
    "symbol": "AAPL",
    "side": "buy",
    "qty": 1,
    "status": "submitted"
}).status_code == 200
assert client.get("/postgres/table/tenants").status_code == 200

print("QNT30394 smoke test passed")
