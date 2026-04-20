from fastapi.testclient import TestClient
from backend.app.main import app


def test_qnt30767_summary_endpoint_exists():
    client = TestClient(app)
    routes = {r.path for r in app.routes}
    assert "/api/regulatory-surveillance-market-abuse-detection-trade-conduct-enforcement-layer/summary" in routes
