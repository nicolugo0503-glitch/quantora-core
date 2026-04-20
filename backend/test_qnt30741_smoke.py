from fastapi.testclient import TestClient
from backend.app.main import app


def test_qnt30741_bootstrap_demo():
    client = TestClient(app)
    client.post('/api/auth/dev-login', json={'email':'qnt30741@example.com','name':'QNT30741'})
    r = client.post('/api/institutional-settlement-exception-command-layer/bootstrap-demo')
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert data['run']['band'] in {'EXCEPTION_CLEARED','CONTROLLED_EXCEPTION','EXCEPTION_WATCH','ESCALATE_EXCEPTION'}
