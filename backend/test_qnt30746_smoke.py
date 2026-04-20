from fastapi.testclient import TestClient
from backend.app.main import app


def test_qnt30746_bootstrap_demo():
    client = TestClient(app)
    client.post('/api/auth/dev-login', json={'email':'qnt30746@example.com','name':'QNT30746'})
    r = client.post('/api/institutional-investor-capital-confirmation-layer/bootstrap-demo')
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert data['run']['band'] in {'FULLY_CONFIRMED','PARTIALLY_CONFIRMED','DISCREPANCY_DETECTED','BLOCKED'}
