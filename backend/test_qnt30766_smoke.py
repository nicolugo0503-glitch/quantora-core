from fastapi.testclient import TestClient
from backend.app.main import app


def test_qnt30766_summary_endpoint_exists():
    client = TestClient(app)
    routes = {r.path for r in app.routes}
    assert "/api/regulatory-records-retention-legal-hold-supervisory-retrieval-command-layer/summary" in routes
