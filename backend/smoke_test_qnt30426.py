from fastapi.testclient import TestClient
from backend.app.main import app


def test_qnt30426_routes_exist():
    client = TestClient(app)
    # auth is required in live usage; route existence is sufficient here
    assert any(r.path == '/workspace/risk/status' for r in app.routes)
    assert any(r.path == '/workspace/risk/update' for r in app.routes)
    assert any(r.path == '/workspace/risk/kill-switch' for r in app.routes)
