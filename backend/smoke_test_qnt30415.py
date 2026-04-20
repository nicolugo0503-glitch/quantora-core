from fastapi.testclient import TestClient
from full_system_wiring import app

client = TestClient(app)

r = client.post("/platform/register", json={"display_name":"nico","email":"test@quantora.com","password":"123456"})
assert r.status_code in (200, 400)
r = client.post("/platform/login", json={"email":"test@quantora.com","password":"123456"})
assert r.status_code == 200
token = r.json()["token"]
assert client.post("/platform/session/bind", json={"token": token}).status_code == 200
assert client.get("/platform/runtime/status").status_code == 200
assert client.post("/platform/trade/record", json={"token": token, "symbol":"AAPL", "side":"buy", "qty":1, "price":100, "pnl":25}).status_code == 200
print("QNT30415 smoke test passed")
