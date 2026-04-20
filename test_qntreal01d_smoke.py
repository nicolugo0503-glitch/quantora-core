from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.qntreal01d_real_pnl_equity_exposure_truth_layer_router import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_health_ok():
    res = client.get('/pnl-truth/health')
    assert res.status_code == 200
    data = res.json()
    assert data['status'] == 'ok'
    assert 'current_equity' in data


def test_mark_and_recompute_cycle():
    res = client.post('/pnl-truth/mark-snapshot', json={'mark_prices': {'BTCUSDT': 61000}})
    assert res.status_code == 200
    data = res.json()
    assert data['status'] == 'ok'
    res = client.post('/pnl-truth/recompute', json={'baseline_equity': 100000})
    assert res.status_code == 200
    data = res.json()
    assert 'gross_exposure' in data
    assert 'net_return_pct' in data
