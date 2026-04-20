from fastapi.testclient import TestClient
from backend.app.main import app


def test_qnt30748_summary_endpoint_exists():
    client = TestClient(app)
    routes = {r.path for r in app.routes}
    assert "/api/institutional-external-auditor-interface-layer/summary" in routes
