from fastapi.testclient import TestClient
from backend.app.main import app


def test_qnt30754_summary_endpoint_exists():
    client = TestClient(app)
    routes = {r.path for r in app.routes}
    assert "/api/institutional-supervisory-examination-command-layer/summary" in routes
