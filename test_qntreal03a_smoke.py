import pytest
import json
import os

STATE_FILE = "real03a_portfolio_stress_test_state.json"


def _write(data):
    with open(STATE_FILE, "w") as f:
        json.dump(data, f)


def _cleanup():
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)


def test_qntreal03a_full_lifecycle():
    _cleanup()
    from backend.app.qntreal03a_portfolio_stress_test_router import router
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    h = client.get("/portfolio-stress-test/health")
    assert h.status_code == 200
    assert h.json()["mission"] == "QNT-REAL03A"

    # Load scenarios
    r1 = client.post("/portfolio-stress-test/load-scenarios", json={
        "scenarios": [
            {"scenario_id": "S1", "name": "2008 GFC Replay", "equity_shock": -0.45, "credit_spread_shock": 0.03},
            {"scenario_id": "S2", "name": "COVID Crash", "equity_shock": -0.35, "credit_spread_shock": 0.015},
        ],
        "actor": "test"
    })
    assert r1.status_code == 200
    assert r1.json()["loaded"] is True
    assert r1.json()["scenario_count"] == 2

    # Apply shocks
    run_id = r1.json()["run_id"]
    r2 = client.post("/portfolio-stress-test/apply-shocks", json={"run_id": run_id, "actor": "test"})
    assert r2.status_code == 200
    assert r2.json()["shocks_applied"] is True

    # Compute VaR
    r3 = client.post("/portfolio-stress-test/compute-var", json={"run_id": run_id, "confidence": 0.99, "actor": "test"})
    assert r3.status_code == 200
    assert r3.json()["var_computed"] is True
    assert "var_99" in r3.json()

    # Assess capital
    r4 = client.post("/portfolio-stress-test/assess-capital", json={"run_id": run_id, "actor": "test"})
    assert r4.status_code == 200
    assert r4.json()["assessed"] is True

    # Summary
    s = client.get("/portfolio-stress-test/summary")
    assert s.status_code == 200
    assert s.json()["stress_test_status"] == "assessed"

    _cleanup()


def test_qntreal03a_blocks_without_integrity():
    _cleanup()
    from backend.app.qntreal03a_portfolio_stress_test_router import router
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    r = client.get("/portfolio-stress-test/summary")
    assert r.status_code == 200
    data = r.json()
    assert data.get("hard_blocked") is True or data.get("stress_test_status") == "idle"

    _cleanup()
