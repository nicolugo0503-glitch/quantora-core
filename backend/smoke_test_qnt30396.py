from fastapi.testclient import TestClient
from trade_lifecycle_integration import app

client = TestClient(app)

assert client.get("/trade-lifecycle/status").status_code == 200

trade = client.post("/trade-lifecycle/idea", json={
    "strategy_id": "alpha-exec-01",
    "symbol": "AAPL",
    "side": "buy",
    "conviction": 0.82,
    "signal_strength": 0.76,
    "requested_qty": 10,
    "reference_price": 100.0
})
assert trade.status_code == 200
trade_id = trade.json()["trade"]["trade_id"]

assert client.post("/trade-lifecycle/allocation", json={
    "trade_id": trade_id,
    "capital_allocated": 1000,
    "approved_qty": 10,
    "regime": "normal",
    "execution_policy": {"mode": "adaptive"}
}).status_code == 200

assert client.post("/trade-lifecycle/execution-request", json={
    "trade_id": trade_id,
    "broker": "alpaca",
    "order_type": "market",
    "time_in_force": "day"
}).status_code == 200

assert client.post(f"/trade-lifecycle/order-submit/{trade_id}").status_code == 200

assert client.post("/trade-lifecycle/fill", json={
    "trade_id": trade_id,
    "filled_qty": 10,
    "fill_price": 100.2,
    "venue": "alpaca_paper",
    "fees": 1.25
}).status_code == 200

assert client.get(f"/trade-lifecycle/trade/{trade_id}").status_code == 200
assert client.get("/trade-lifecycle/positions").status_code == 200

print("QNT30396 smoke test passed")
