from fastapi.testclient import TestClient
from backend.app.main import app


def test_qnt30763_summary_endpoint_exists():
    client = TestClient(app)
    routes = {r.path for r in app.routes}
    assert "/api/regulatory-stress-testing-submission-supervisory-challenge-layer/summary" in routes
