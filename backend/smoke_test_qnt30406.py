from fastapi.testclient import TestClient
from real_broker_execution_bridge import app
import os

os.environ["ALPACA_API_KEY"] = "paper_key"
os.environ["ALPACA_SECRET_KEY"] = "paper_secret"
os.environ["ALPACA_BASE_URL"] = "https://paper-api.alpaca.markets"
os.environ["ALPACA_PAPER"] = "true"

client = TestClient(app)

assert client.get("/live-bridge/status").status_code == 200
assert client.post("/live-bridge/connect", json={"mode":"paper"}).status_code == 200
r = client.post("/live-bridge/order/submit", json={"symbol":"AAPL","side":"buy","qty":1})
assert r.status_code == 200
assert client.get("/live-bridge/orders").status_code == 200
assert client.get("/live-bridge/positions").status_code == 200
print("QNT30406 smoke test passed")
