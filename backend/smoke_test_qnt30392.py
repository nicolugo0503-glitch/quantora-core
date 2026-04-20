from fastapi.testclient import TestClient
from paper_trade_execution_validation import app

client = TestClient(app)

assert client.get("/execution-validation/status").status_code == 200

r = client.post("/execution-validation/validate", json={
    "symbol": "AAPL",
    "side": "buy",
    "qty": 1,
    "price": 100
})
assert r.status_code == 200
assert r.json()["status"] == "approved"

r = client.post("/execution-validation/submit", json={
    "symbol": "AAPL",
    "side": "buy",
    "qty": 1,
    "price": 100
})
assert r.status_code == 200

r = client.post("/execution-validation/test-suite", json={})
assert r.status_code == 200
assert r.json()["failed"] == 0

print("QNT30392 smoke test passed")
