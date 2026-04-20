from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.qntreal01e_real_order_entry_guarded_live_trade_execution_surface_router import router
from backend.app.execution.fill_handler import save_state

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_health_ok():
    res = client.get('/order-entry/health')
    assert res.status_code == 200
    assert res.json()['status'] == 'ok'


def test_preview_and_blocked_submit_cycle():
    save_state({'locked': False, 'generated_by': 'QNT50001', 'mode': 'paper', 'safe_mode': True, 'active_broker': 'paper', 'decision_memory': [], 'orders': [], 'fills': [], 'audit_log': []})
    res = client.post('/order-entry/preview', json={'symbol': 'BTCUSDT', 'side': 'BUY', 'qty': 0.01, 'order_type': 'MARKET'})
    assert res.status_code == 200
    assert res.json()['preview']['symbol'] == 'BTCUSDT'
    res = client.post('/order-entry/submit', json={'symbol': 'BTCUSDT', 'side': 'BUY', 'qty': 0.01, 'order_type': 'MARKET'})
    assert res.status_code == 403
