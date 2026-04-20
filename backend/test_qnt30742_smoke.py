from fastapi.testclient import TestClient
from backend.app.main import app


def test_qnt30742_bootstrap_demo():
    client = TestClient(app)
    client.post('/api/auth/dev-login', json={'email':'qnt30742@example.com','name':'QNT30742'})
    r = client.post('/api/institutional-settlement-recovery-resolution-layer/bootstrap-demo')
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert data['run']['band'] in {'RECOVERY_RESOLVED','RECOVERY_CONTROLLED','RECOVERY_WATCH','RECOVERY_ESCALATE'}
