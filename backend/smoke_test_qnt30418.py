import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

checks = []

for path in [
    "/health",
    "/billing/subscription-status",
    "/billing/metrics",
    "/performance/attribution",
    "/performance/strategies",
    "/performance/execution",
    "/performance/portfolio",
]:
    r = client.get(path)
    checks.append((path, r.status_code))
    assert r.status_code == 200, (path, r.text)

# Manual simulated plan update to create attribution/billing transitions.
resp = client.post(
    "/allocator/operator-capital/set",
    json={"allocated_capital": 1000},
)
assert resp.status_code == 200, resp.text

resp = client.post(
    "/billing/webhook",
    json={"event_type": "manual.promote", "operator_id": "operator_F5E2C5BA", "plan": "institutional", "subscription_status": "active"},
)
assert resp.status_code == 200, resp.text

order = client.post(
    "/orders/submit",
    json={"symbol": "AAPL", "side": "buy", "qty": 0.05, "execution_mode": "paper"},
)
assert order.status_code == 200, order.text

snap = client.get("/performance/attribution")
assert snap.status_code == 200, snap.text
payload = snap.json()
assert payload.get("mission") == "QNT30418"
assert "summary" in payload and "strategy_attribution" in payload

print({"status": "ok", "checks": checks, "orders_analyzed": payload.get("summary", {}).get("orders_analyzed")})
