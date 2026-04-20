from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.qntreal01c_real_position_fill_broker_sync_authority_router import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_broker_sync_health():
    res = client.get('/broker-sync/health')
    assert res.status_code == 200
    data = res.json()
    assert data['status'] == 'ok'
    assert 'position_count' in data


def test_sync_and_reconcile_cycle():
    res = client.post('/broker-sync/sync-context')
    assert res.status_code == 200
    res = client.post('/broker-sync/reconcile', json={'expected_position_count': res.json()['position_count']})
    assert res.status_code == 200
    assert res.json()['drift_detected'] is False
