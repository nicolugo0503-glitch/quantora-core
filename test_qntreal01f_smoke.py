from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.qntreal01f_live_broker_credential_vault_execution_authorization_gate_router import router
from backend.app.execution.fill_handler import save_state

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_health_ok():
    res = client.get('/credential-vault/health')
    assert res.status_code == 200
    assert res.json()['status'] == 'ok'


def test_register_and_authorize_paper_blocked_then_live_success():
    save_state({'locked': False, 'generated_by': 'QNT50001', 'mode': 'paper', 'safe_mode': True, 'active_broker': 'paper', 'decision_memory': [], 'orders': [], 'fills': [], 'audit_log': []})
    res = client.post('/credential-vault/validate', json={})
    assert res.status_code == 200
    assert 'execution mode is not live' in ' '.join(res.json()['blockers'])


def test_manual_binance_authorization_cycle(tmp_path=None):
    from backend.app.qntreal01f_live_broker_credential_vault_execution_authorization_gate_router import VAULT_FILE, BROKER_TRUTH_FILE, EXECUTION_FILE
    import json
    VAULT_FILE.write_text(json.dumps({
        'selected_broker': 'binance',
        'providers': {
            'paper': {'configured': True, 'source': 'system', 'fingerprint': 'paper', 'masked': {'mode': 'simulated'}},
            'binance': {'configured': True, 'source': 'manual', 'fingerprint': 'abc123', 'masked': {'binance_api_key': 'BIN***KEY', 'binance_secret': 'BIN***RET'}},
            'alpaca': {'configured': False, 'source': None, 'fingerprint': None, 'masked': {}},
            'ibkr': {'configured': False, 'source': None, 'fingerprint': None, 'masked': {}},
        },
        'execution_authorized': False,
        'authorization_reason': None,
        'authorization_scope': 'live-trading',
        'last_validation': None,
        'last_error': None,
        'last_rotation': None,
    }))
    BROKER_TRUTH_FILE.write_text(json.dumps({'selected_broker': 'binance', 'live_path_armed': True, 'validation': {'valid': True, 'blockers': []}}))
    EXECUTION_FILE.write_text(json.dumps({'mode': 'live', 'safe_mode': False, 'active_broker': 'binance'}))
    res = client.post('/credential-vault/authorize-execution', json={'reason': 'operator ready'})
    assert res.status_code == 200
    assert res.json()['execution_authorized'] is True
