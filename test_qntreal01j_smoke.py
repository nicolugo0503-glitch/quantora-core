from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_qntreal01j_health_and_summary():
    health = client.get('/cash-truth/health')
    assert health.status_code == 200
    data = health.json()
    assert data['mission'] == 'QNT-REAL01J'
    summary = client.get('/cash-truth/summary')
    assert summary.status_code == 200
    s = summary.json()
    assert 'cash_balance' in s
    assert 'buying_power' in s


def test_qntreal01j_recompute_and_reset():
    r = client.post('/cash-truth/recompute', json={})
    assert r.status_code == 200
    d = r.json()
    assert d['mission'] == 'QNT-REAL01J'
    rr = client.post('/cash-truth/reset', json={})
    assert rr.status_code == 200
    assert rr.json()['mission'] == 'QNT-REAL01J'
