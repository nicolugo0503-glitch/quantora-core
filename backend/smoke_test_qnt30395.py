from fastapi.testclient import TestClient
from live_execution_hardening import app

client = TestClient(app)

assert client.get("/live-hardening/status").status_code == 200

assert client.post("/live-hardening/controls/update", json={
    "live_enabled": True,
    "kill_switch": False,
    "require_dual_confirmation": True,
    "max_order_notional": 5000,
    "max_daily_notional": 25000,
    "max_position_qty": 100
}).status_code == 200

req = client.post("/live-hardening/request", json={
    "symbol": "AAPL",
    "side": "buy",
    "qty": 1,
    "price": 100,
    "operator_id": "ops-1"
})
assert req.status_code == 200
confirmation_id = req.json()["request"]["confirmation_id"]

conf = client.post("/live-hardening/confirm", json={
    "confirmation_id": confirmation_id,
    "approver_id": "ops-2"
})
assert conf.status_code == 200

exe = client.post(f"/live-hardening/execute/{confirmation_id}")
assert exe.status_code == 200

kill = client.post("/live-hardening/kill-switch?enabled=true")
assert kill.status_code == 200

print("QNT30395 smoke test passed")
