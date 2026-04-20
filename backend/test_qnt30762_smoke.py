from fastapi.testclient import TestClient
from backend.app.main import app


def test_qnt30762_summary_endpoint_exists():
    client = TestClient(app)
    routes = {r.path for r in app.routes}
    assert "/api/recovery-resolution-scenario-simulation-command-layer/summary" in routes
