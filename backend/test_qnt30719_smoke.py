from fastapi.testclient import TestClient
from backend.app.main import app


def test_qnt30719_smoke():
    client = TestClient(app)
    r = client.get('/api/executive-decision-memory-layer/summary')
    assert r.status_code in (200, 401, 403, 422)
