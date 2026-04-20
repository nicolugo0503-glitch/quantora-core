from fastapi.testclient import TestClient
from autonomous_portfolio_manager import app

client = TestClient(app)

assert client.get("/portfolio-manager/status").status_code == 200

payload = {
    "strategies": [
        {"strategy_id":"alpha-1","realized_pnl":12000,"sharpe":1.8,"drawdown":4000,"win_rate":0.61,"trade_count":15,"execution_quality":0.88,"regime_score":0.72},
        {"strategy_id":"beta-2","realized_pnl":8000,"sharpe":1.3,"drawdown":2500,"win_rate":0.57,"trade_count":12,"execution_quality":0.79,"regime_score":0.66},
        {"strategy_id":"gamma-3","realized_pnl":-1500,"sharpe":-0.4,"drawdown":30000,"win_rate":0.40,"trade_count":9,"execution_quality":0.58,"regime_score":0.31},
    ]
}

r = client.post("/portfolio-manager/strategies/batch", json=payload)
assert r.status_code == 200
allocs = client.get("/portfolio-manager/allocations")
assert allocs.status_code == 200
assert "gamma-3" in allocs.json()["allocations"]
assert allocs.json()["allocations"]["gamma-3"]["status"] == "killed"

r = client.post("/portfolio-manager/rebalance")
assert r.status_code == 200

print("QNT30384 smoke test passed")
