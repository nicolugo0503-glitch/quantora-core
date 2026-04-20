from fastapi.testclient import TestClient

from backend.app.main import app


def test_qntreal01g_health_and_flow():
    client = TestClient(app)
    health = client.get('/broker-session/health')
    assert health.status_code == 200
    handshake = client.post('/broker-session/handshake', json={'broker': 'paper'})
    assert handshake.status_code == 200
    data = handshake.json()
    assert data['handshake_valid'] is True
    verify = client.post('/broker-session/verify-connectivity', json={'broker': 'paper'})
    assert verify.status_code == 200
    v = verify.json()
    assert v['connectivity_verified'] is True
    assert v['connectivity_status'] in {'simulated', 'verified'}
