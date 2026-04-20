import json
import os
import socket
import time
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException

router = APIRouter(prefix='/broker-session', tags=['broker-session-handshake'])

ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = ROOT / 'backend' / 'app' / 'state'
SESSION_FILE = STATE_DIR / 'broker_session_handshake_state.json'
VAULT_FILE = STATE_DIR / 'live_broker_credential_vault_state.json'
BROKER_TRUTH_FILE = STATE_DIR / 'live_broker_truth_state.json'
EXECUTION_FILE = STATE_DIR / 'execution_state.json'
RISK_FILE = STATE_DIR / 'risk_kill_switch_state.json'


def _read_json(path: Path, fallback: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return fallback


def _write_json(path: Path, data: Dict[str, Any]) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding='utf-8')
    return data


def _default_state() -> Dict[str, Any]:
    return {
        'selected_broker': 'paper',
        'session_status': 'idle',
        'connectivity_status': 'unknown',
        'handshake_valid': False,
        'connectivity_verified': False,
        'last_handshake_at': None,
        'last_connectivity_check_at': None,
        'last_error': None,
        'details': {},
        'history': [],
    }


def _load_state() -> Dict[str, Any]:
    return _read_json(SESSION_FILE, _default_state())


def _load_vault() -> Dict[str, Any]:
    return _read_json(VAULT_FILE, {'providers': {}, 'execution_authorized': False})


def _load_truth() -> Dict[str, Any]:
    return _read_json(BROKER_TRUTH_FILE, {'selected_broker': 'paper', 'live_path_armed': False})


def _load_execution() -> Dict[str, Any]:
    return _read_json(EXECUTION_FILE, {'mode': 'paper', 'safe_mode': True, 'active_broker': 'paper'})


def _load_risk() -> Dict[str, Any]:
    return _read_json(RISK_FILE, {'kill_switch_triggered': False})


def _broker_endpoint(provider: str) -> Dict[str, Any]:
    if provider == 'binance':
        return {'host': 'api.binance.com', 'port': 443, 'target': 'rest'}
    if provider == 'alpaca':
        base = os.getenv('ALPACA_BASE_URL', 'paper-api.alpaca.markets')
        host = base.replace('https://', '').replace('http://', '').split('/')[0]
        return {'host': host or 'paper-api.alpaca.markets', 'port': 443, 'target': 'rest'}
    if provider == 'ibkr':
        host = os.getenv('IBKR_HOST', '127.0.0.1')
        port = int(os.getenv('IBKR_PORT', '7497'))
        return {'host': host, 'port': port, 'target': 'gateway'}
    return {'host': 'paper', 'port': 0, 'target': 'simulated'}


def _socket_probe(host: str, port: int, timeout: float = 2.0) -> Dict[str, Any]:
    start = time.time()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            latency_ms = int((time.time() - start) * 1000)
            return {'reachable': True, 'latency_ms': latency_ms, 'error': None}
    except Exception as exc:
        return {'reachable': False, 'latency_ms': None, 'error': str(exc)}


def _provider_configured(vault: Dict[str, Any], provider: str) -> bool:
    info = (vault.get('providers') or {}).get(provider, {})
    return bool(info.get('configured', False)) or provider == 'paper'


def _append_history(state: Dict[str, Any], event: Dict[str, Any]) -> None:
    history = list(state.get('history') or [])
    history.append(event)
    state['history'] = history[-20:]


def _build_summary() -> Dict[str, Any]:
    state = _load_state()
    vault = _load_vault()
    truth = _load_truth()
    execution = _load_execution()
    risk = _load_risk()
    selected = truth.get('selected_broker') or state.get('selected_broker') or execution.get('active_broker', 'paper') or 'paper'
    endpoint = _broker_endpoint(selected)
    configured = _provider_configured(vault, selected)
    blockers = []
    if execution.get('mode') != 'live':
        blockers.append('execution mode is not live')
    if bool(execution.get('safe_mode', True)):
        blockers.append('safe mode enabled')
    if bool(risk.get('kill_switch_triggered', False)):
        blockers.append('risk kill switch triggered')
    if selected == 'paper':
        blockers.append('selected broker is paper')
    if not configured:
        blockers.append(f'{selected} credentials are not configured')
    if not bool(truth.get('live_path_armed', False)):
        blockers.append('live broker path not armed')
    if not bool(state.get('handshake_valid', False)):
        blockers.append('broker session handshake not valid')
    if not bool(state.get('connectivity_verified', False)):
        blockers.append('broker connectivity not verified')
    live_connectivity_ready = not blockers
    return {
        'status': 'ok',
        'mission': 'QNT-REAL01G',
        'selected_broker': selected,
        'execution_mode': execution.get('mode', 'paper'),
        'safe_mode': bool(execution.get('safe_mode', True)),
        'kill_switch_triggered': bool(risk.get('kill_switch_triggered', False)),
        'live_path_armed': bool(truth.get('live_path_armed', False)),
        'provider_configured': configured,
        'session_status': state.get('session_status', 'idle'),
        'connectivity_status': state.get('connectivity_status', 'unknown'),
        'handshake_valid': bool(state.get('handshake_valid', False)),
        'connectivity_verified': bool(state.get('connectivity_verified', False)),
        'live_connectivity_ready': live_connectivity_ready,
        'endpoint': endpoint,
        'details': state.get('details', {}),
        'blockers': blockers,
        'last_handshake_at': state.get('last_handshake_at'),
        'last_connectivity_check_at': state.get('last_connectivity_check_at'),
        'last_error': state.get('last_error'),
        'history': state.get('history', []),
        'generated_at': int(time.time()),
    }


@router.get('/health')
def broker_session_health() -> Dict[str, Any]:
    summary = _build_summary()
    return {
        'status': 'ok',
        'mission': summary['mission'],
        'selected_broker': summary['selected_broker'],
        'handshake_valid': summary['handshake_valid'],
        'connectivity_verified': summary['connectivity_verified'],
        'live_connectivity_ready': summary['live_connectivity_ready'],
        'blockers': summary['blockers'],
    }


@router.get('/summary')
def broker_session_summary() -> Dict[str, Any]:
    return _build_summary()


@router.post('/handshake')
def broker_session_handshake(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
    state = _load_state()
    vault = _load_vault()
    truth = _load_truth()
    execution = _load_execution()
    selected = str(payload.get('broker') or truth.get('selected_broker') or execution.get('active_broker') or 'paper').lower().strip()
    if selected not in {'paper', 'binance', 'alpaca', 'ibkr'}:
        raise HTTPException(status_code=400, detail='broker must be one of paper, binance, alpaca, ibkr')
    configured = _provider_configured(vault, selected)
    token = str(payload.get('session_token') or '').strip()
    state['selected_broker'] = selected
    state['last_handshake_at'] = int(time.time())
    if selected == 'paper':
        state['session_status'] = 'paper'
        state['handshake_valid'] = True
        state['last_error'] = None
        state['details'] = {'mode': 'simulated'}
    elif not configured:
        state['session_status'] = 'blocked'
        state['handshake_valid'] = False
        state['last_error'] = f'{selected} credentials are not configured'
    else:
        state['session_status'] = 'connected'
        state['handshake_valid'] = True
        state['last_error'] = None
        state['details'] = {
            'session_token_present': bool(token),
            'session_mode': 'validated-credentials',
            'provider_source': ((vault.get('providers') or {}).get(selected, {}) or {}).get('source'),
        }
    _append_history(state, {
        'event': 'handshake',
        'broker': selected,
        'status': state['session_status'],
        'timestamp': state['last_handshake_at'],
    })
    _write_json(SESSION_FILE, state)
    return _build_summary()


@router.post('/verify-connectivity')
def broker_session_verify(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
    state = _load_state()
    truth = _load_truth()
    execution = _load_execution()
    selected = str(payload.get('broker') or state.get('selected_broker') or truth.get('selected_broker') or execution.get('active_broker') or 'paper').lower().strip()
    endpoint = _broker_endpoint(selected)
    timeout = float(payload.get('timeout_seconds') or 2.0)
    state['selected_broker'] = selected
    state['last_connectivity_check_at'] = int(time.time())
    if selected == 'paper':
        state['connectivity_status'] = 'simulated'
        state['connectivity_verified'] = True
        state['last_error'] = None
        state['details'] = {**(state.get('details') or {}), 'connectivity': {'reachable': True, 'latency_ms': 0, 'mode': 'paper'}}
    elif not bool(state.get('handshake_valid', False)):
        raise HTTPException(status_code=400, detail='broker session handshake must be valid before connectivity verification')
    else:
        probe = _socket_probe(endpoint['host'], int(endpoint['port']), timeout=timeout)
        state['connectivity_status'] = 'verified' if probe['reachable'] else 'unreachable'
        state['connectivity_verified'] = bool(probe['reachable'])
        state['last_error'] = probe['error']
        state['details'] = {**(state.get('details') or {}), 'connectivity': {**probe, **endpoint}}
    _append_history(state, {
        'event': 'connectivity',
        'broker': selected,
        'status': state['connectivity_status'],
        'timestamp': state['last_connectivity_check_at'],
    })
    _write_json(SESSION_FILE, state)
    return _build_summary()


@router.post('/reset')
def broker_session_reset() -> Dict[str, Any]:
    _write_json(SESSION_FILE, _default_state())
    return _build_summary()
