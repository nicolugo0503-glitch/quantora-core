from fastapi.testclient import TestClient
from backend.app.main import app


def test_qnt30751_summary_endpoint_exists():
    client = TestClient(app)
    routes = {r.path for r in app.routes}
    assert "/api/multi-jurisdiction-governance-layer/summary" in routes
