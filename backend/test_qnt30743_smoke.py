from fastapi.testclient import TestClient
from backend.app.main import app


def test_qnt30743_bootstrap_demo():
    client = TestClient(app)
    client.post('/api/auth/dev-login', json={'email':'qnt30743@example.com','name':'QNT30743'})
    r = client.post('/api/institutional-settlement-finalization-authority-layer/bootstrap-demo')
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert data['run']['band'] in {'FINALIZATION_AUTHORIZED','FINALIZATION_CONTROLLED','FINALIZATION_WATCH','FINALIZATION_BLOCKED'}
