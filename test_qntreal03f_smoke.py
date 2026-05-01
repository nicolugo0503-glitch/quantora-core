import pytest
import json
import os

STATE_FILE = "position_limits_state.json"


def _cleanup():
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)


def test_qntreal03f_health():
    _cleanup()
    from backend.app.qntreal03f_position_limits_router import router
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    h = client.get("/position-limits/health")
    assert h.status_code == 200
    assert h.json()["mission"] == "QNT-REAL03F"
    _cleanup()


def test_qntreal03f_blocks_without_integrity():
    _cleanup()
    from backend.app.qntreal03f_position_limits_router import router
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    r = client.get("/position-limits/summary")
    assert r.status_code == 200
    data = r.json()
    assert data.get("hard_blocked") is True or data.get("status") == "idle"
    _cleanup()
