from fastapi.testclient import TestClient
from persistent_data_layer import app

client = TestClient(app)

assert client.get("/data-layer/status").status_code == 200

assert client.post("/data-layer/tenant/upsert", json={
    "tenant_id": "tenant-001",
    "tenant_name": "Quantora Client One",
    "plan": "pro"
}).status_code == 200

assert client.post("/data-layer/user/upsert", json={
    "user_id": "user-001",
    "tenant_id": "tenant-001",
    "full_name": "Client Admin",
    "email": "admin@example.com",
    "role": "owner"
}).status_code == 200

assert client.post("/data-layer/strategy/upsert", json={
    "strategy_id": "alpha-1",
    "tenant_id": "tenant-001",
    "realized_pnl": 10000,
    "sharpe": 1.7,
    "drawdown": 2200,
    "win_rate": 0.61,
    "active": True
}).status_code == 200

assert client.post("/data-layer/trade/upsert", json={
    "trade_id": "trade-001",
    "tenant_id": "tenant-001",
    "strategy_id": "alpha-1",
    "symbol": "AAPL",
    "side": "buy",
    "qty": 10,
    "entry_price": 100,
    "exit_price": 103,
    "fees": 1.25
}).status_code == 200

assert client.post("/data-layer/allocation/upsert", json={
    "allocation_id": "alloc-001",
    "tenant_id": "tenant-001",
    "strategy_id": "alpha-1",
    "capital": 50000,
    "weight": 0.25,
    "status": "active"
}).status_code == 200

assert client.post("/data-layer/subscription/upsert", json={
    "subscription_id": "sub-001",
    "tenant_id": "tenant-001",
    "customer_name": "Quantora Client One",
    "plan": "pro",
    "monthly_price": 299,
    "status": "active"
}).status_code == 200

assert client.post("/data-layer/invoice/upsert", json={
    "invoice_id": "inv-001",
    "tenant_id": "tenant-001",
    "amount": 299,
    "currency": "USD",
    "status": "issued"
}).status_code == 200

assert client.post("/data-layer/backup/create").status_code == 200
assert client.get("/data-layer/export").status_code == 200
assert client.get("/data-layer/records/strategies").status_code == 200

print("QNT30389 smoke test passed")
