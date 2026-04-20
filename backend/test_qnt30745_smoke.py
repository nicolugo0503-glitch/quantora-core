from fastapi.testclient import TestClient
from backend.app.main import app


def test_qnt30745_bootstrap_demo():
    client = TestClient(app)
    client.post('/api/auth/dev-login', json={'email':'qnt30745@example.com','name':'QNT30745'})
    r = client.post('/api/institutional-treasury-confirmation-layer/bootstrap-demo')
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert data['run']['band'] in {'TREASURY_CONFIRMED','TREASURY_CONTROLLED','TREASURY_WATCH','TREASURY_BLOCKED'}
