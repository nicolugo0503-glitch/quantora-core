from fastapi.testclient import TestClient
from treasury_reserve_liquidity_command import app

client = TestClient(app)

assert client.get("/treasury/status").status_code == 200

assert client.post("/treasury/policy/update", json={
    "min_reserve_ratio": 0.18,
    "min_cash_ratio": 0.22,
    "max_deployable_ratio": 0.68,
    "liquidity_alert_ratio": 0.12
}).status_code == 200

assert client.post("/treasury/snapshot/update", json={
    "capital_base": 1000000,
    "cash_balance": 180000,
    "reserve_balance": 140000,
    "deployable_balance": 680000
}).status_code == 200

assert client.post("/treasury/auto-balance").status_code == 200

assert client.post("/treasury/sweep", json={
    "amount": 25000,
    "from_bucket": "deployable_balance",
    "to_bucket": "reserve_balance",
    "reason": "controlled reserve reinforcement",
    "operator_id": "treasury-admin"
}).status_code == 200

assert client.get("/treasury/actions").status_code == 200
assert client.get("/treasury/sweeps").status_code == 200

print("QNT30404 smoke test passed")
