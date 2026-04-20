from fastapi.testclient import TestClient
from backend.app.main import app


def test_qnt30714_smoke():
    client = TestClient(app)
    r = client.get('/api/investor-transparency-engine/summary')
    assert r.status_code in (200, 401, 403, 422)
