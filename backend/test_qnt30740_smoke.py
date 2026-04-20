from fastapi.testclient import TestClient
from backend.app.main import app


def test_qnt30740_summary_endpoint_exists():
    client = TestClient(app)
    response = client.get('/api/institutional-settlement-integrity-command-layer/summary')
    assert response.status_code in (200, 401, 403)
