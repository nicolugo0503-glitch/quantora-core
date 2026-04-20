from fastapi.testclient import TestClient
from backend.app.main import app


def test_qnt30759_summary_endpoint_exists():
    client = TestClient(app)
    routes = {r.path for r in app.routes}
    assert "/api/regulatory-capital-adequacy-surveillance-early-warning-layer/summary" in routes
