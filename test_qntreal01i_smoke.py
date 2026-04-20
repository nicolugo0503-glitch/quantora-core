import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app

ROOT = Path(__file__).resolve().parent
STATE_DIR = ROOT / 'backend' / 'app' / 'state'


def _write(name, data):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    (STATE_DIR / name).write_text(json.dumps(data), encoding='utf-8')


def _seed_live_ok(symbol='BTCUSDT', position_symbol='BTCUSDT'):
    _write('execution_state.json', {
        'mode': 'live',
        'safe_mode': False,
        'active_broker': 'binance',
        'fills': [{'symbol': symbol, 'qty': 0.01, 'side': 'BUY', 'price': 50000}],
        'orders': [],
    })
    _write('broker_session_handshake_state.json', {
        'selected_broker': 'binance',
        'session_status': 'connected',
        'connectivity_status': 'verified',
        'handshake_valid': True,
        'connectivity_verified': True,
    })
    _write('real_position_fill_broker_sync_state.json', {
        'sync_status': 'synced',
        'drift_detected': False,
        'drift_reason': None,
        'positions': [{'symbol': position_symbol, 'qty': 0.01}],
        'fills': [{'symbol': symbol, 'qty': 0.01, 'side': 'BUY', 'price': 50000}],
    })


def test_qntreal01i_reconcile_and_lock_cycle():
    _seed_live_ok()
    client = TestClient(app)

    r = client.post('/post-trade-lock/reconcile-position')
    assert r.status_code == 200
    body = r.json()
    assert body['reconciliation_status'] == 'reconciled'

    r = client.post('/post-trade-lock/lock-trade-state')
    assert r.status_code == 200
    body = r.json()
    assert body['lock_status'] == 'locked'


def test_qntreal01i_blocks_lock_on_drift():
    _seed_live_ok(symbol='BTCUSDT', position_symbol='ETHUSDT')
    client = TestClient(app)

    r = client.post('/post-trade-lock/reconcile-position')
    assert r.status_code == 200
    assert r.json()['drift_detected'] is True

    r = client.post('/post-trade-lock/lock-trade-state')
    assert r.status_code == 400
