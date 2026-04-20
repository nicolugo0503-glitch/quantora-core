from fastapi.testclient import TestClient
from backend.app.main import app


def test_qnt30718_smoke():
    client = TestClient(app)
    r = client.get("/api/executive-ai-command-layer/summary")
    assert r.status_code in (200, 401, 403, 422)
