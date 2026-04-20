
from fastapi.testclient import TestClient
from live_trading_hardening import app

client = TestClient(app)
assert client.get("/live-hardening-v2/status").status_code == 200
assert client.post("/live-hardening-v2/config", json={"live_enabled": True, "kill_switch": False}).status_code == 200
assert client.post("/live-hardening-v2/precheck", json={"symbol":"AAPL","side":"buy","qty":1,"price":100,"mode":"paper"}).status_code == 200
assert client.post("/live-hardening-v2/submit", json={"symbol":"AAPL","side":"buy","qty":1,"price":100,"mode":"paper"}).status_code == 200
assert client.get("/live-hardening-v2/executions").status_code == 200
print("QNT30412 smoke test passed")
