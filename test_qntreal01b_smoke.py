from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.qntreal01b_live_broker_truth_path_router import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_broker_truth_health():
    res = client.get('/broker-truth/health')
    assert res.status_code == 200
    data = res.json()
    assert data['status'] == 'ok'
    assert 'selected_broker' in data


def test_select_and_arm_path():
    res = client.post('/broker-truth/select-broker', json={'broker': 'paper'})
    assert res.status_code == 200
    res = client.post('/broker-truth/arm-live-path', json={'enabled': True})
    assert res.status_code == 200
    assert res.json()['live_path_armed'] is True
