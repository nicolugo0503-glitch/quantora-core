import pytest
import json
import os

STATE_FILE = "regulatory_capital_state.json"


def _cleanup():
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)


def test_qntreal03e_health():
    _cleanup()
    from backend.app.qntreal03e_regulatory_capital_router import router
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    h = client.get("/regulatory-capital/health")
    assert h.status_code == 200
    assert h.json()["mission"] == "QNT-REAL03E"
    _cleanup()


def test_qntreal03e_blocks_without_integrity():
    _cleanup()
    from backend.app.qntreal03e_regulatory_capital_router import router
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    r = client.get("/regulatory-capital/summary")
    assert r.status_code == 200
    data = r.json()
    assert data.get("hard_blocked") is True or data.get("status") == "idle"
    _cleanup()
