from fastapi.testclient import TestClient
from broker_integration_layer import app

client = TestClient(app)

assert client.get("/broker-integration/status").status_code == 200
assert client.post("/broker-integration/order/validate", json={
    "broker": "alpaca",
    "symbol": "AAPL",
    "side": "buy",
    "qty": 5,
    "execution_policy": {"mode": "adaptive"}
}).status_code == 200

assert client.post("/broker-integration/order/submit", json={
    "broker": "binance",
    "symbol": "BTCUSDT",
    "side": "buy",
    "qty": 0.25,
    "metadata": {"test": True}
}).status_code == 200

assert client.post("/broker-integration/dispatch", json={
    "orders": [
        {"broker": "alpaca", "symbol": "MSFT", "side": "buy", "qty": 2},
        {"broker": "ibkr", "symbol": "SPY", "side": "sell", "qty": 1}
    ]
}).status_code == 200

print("QNT30382 smoke test passed")
