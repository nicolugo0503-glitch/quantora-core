from fastapi.testclient import TestClient
from backend.app.main import app


def test_qnt30744_bootstrap_demo():
    client = TestClient(app)
    client.post('/api/auth/dev-login', json={'email':'qnt30744@example.com','name':'QNT30744'})
    r = client.post('/api/institutional-cash-reconciliation-closure-layer/bootstrap-demo')
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert data['run']['band'] in {'CASH_CLOSED','CASH_CONTROLLED','CASH_WATCH','CASH_BLOCKED'}
