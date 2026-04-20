from fastapi.testclient import TestClient
from performance_engine import app

client = TestClient(app)

assert client.get("/performance/status").status_code == 200

payloads = [
    {"strategy_id":"alpha-1","symbol":"AAPL","side":"buy","qty":10,"entry_price":100,"exit_price":103,"fees":1},
    {"strategy_id":"alpha-1","symbol":"MSFT","side":"buy","qty":5,"entry_price":200,"exit_price":198,"fees":0.5},
    {"strategy_id":"beta-2","symbol":"BTCUSDT","side":"sell","qty":1,"entry_price":50000,"exit_price":49500,"fees":5},
]
for payload in payloads:
    r = client.post("/performance/trade/ingest", json=payload)
    assert r.status_code == 200

assert client.get("/performance/portfolio").status_code == 200
assert client.get("/performance/rankings").status_code == 200
assert client.get("/performance/strategy/alpha-1").status_code == 200

print("QNT30383 smoke test passed")
