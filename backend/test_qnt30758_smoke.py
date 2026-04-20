from fastapi.testclient import TestClient
from backend.app.main import app


def test_qnt30758_summary_endpoint_exists():
    client = TestClient(app)
    routes = {r.path for r in app.routes}
    assert "/api/regulatory-enforcement-response-consent-order-command-layer/summary" in routes
