from fastapi.testclient import TestClient
from multi_strategy_competition_selection import app

client = TestClient(app)

assert client.get("/strategy-competition/status").status_code == 200

assert client.post("/strategy-competition/strategies/upsert", json={
    "strategies": [
        {"strategy_id":"alpha-exec-01","name":"Alpha Execution","regime_fit":0.92,"sharpe":2.1,"realized_pnl":12000,"drawdown":0.04,"win_rate":0.64,"execution_quality":0.91},
        {"strategy_id":"regime-alloc-02","name":"Regime Allocation","regime_fit":0.88,"sharpe":1.8,"realized_pnl":9300,"drawdown":0.05,"win_rate":0.61,"execution_quality":0.86},
        {"strategy_id":"meanrev-03","name":"Mean Reversion","regime_fit":0.71,"sharpe":1.2,"realized_pnl":4200,"drawdown":0.08,"win_rate":0.56,"execution_quality":0.79}
    ]
}).status_code == 200

run = client.post("/strategy-competition/run", json={
    "regime": "normal",
    "capital_budget": 100000,
    "max_selected": 3
})
assert run.status_code == 200
assert run.json()["match"]["champion"]["strategy_id"] == "alpha-exec-01"

assert client.get("/strategy-competition/champion").status_code == 200
assert client.get("/strategy-competition/capital-queue").status_code == 200

print("QNT30399 smoke test passed")
