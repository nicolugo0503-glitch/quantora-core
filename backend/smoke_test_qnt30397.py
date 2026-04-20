from fastapi.testclient import TestClient
from investor_reporting_operator_intelligence import app

client = TestClient(app)

assert client.get("/reporting/status").status_code == 200

assert client.post("/reporting/portfolio/update", json={
    "aum": 1200000,
    "realized_pnl": 20000,
    "unrealized_pnl": 5000,
    "net_pnl": 25000,
    "sharpe": 1.95,
    "max_drawdown": 0.065,
    "win_rate": 0.63,
    "trade_count": 144
}).status_code == 200

assert client.post("/reporting/investor-report/generate", json={
    "period_label": "Monthly Review",
    "audience": "investor",
    "include_operator_notes": True
}).status_code == 200

assert client.post("/reporting/operator-brief/generate", json={
    "focus": "daily",
    "include_risk": True,
    "include_execution": True,
    "include_capital": True
}).status_code == 200

assert client.get("/reporting/investor-reports").status_code == 200
assert client.get("/reporting/operator-briefs").status_code == 200

print("QNT30397 smoke test passed")
