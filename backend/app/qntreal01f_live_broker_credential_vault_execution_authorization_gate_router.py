
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException

router = APIRouter(prefix='/credential-vault', tags=['live-broker-credential-vault'])

ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = ROOT / 'backend' / 'app' / 'state'
VAULT_FILE = STATE_DIR / 'live_broker_credential_vault_state.json'
BROKER_TRUTH_FILE = STATE_DIR / 'live_broker_truth_state.json'
EXECUTION_FILE = STATE_DIR / 'execution_state.json'
RISK_FILE = STATE_DIR / 'risk_kill_switch_state.json'


ENV_MAP = {
    'paper': [],
    'binance': ['BINANCE_API_KEY', 'BINANCE_SECRET'],
    'alpaca': ['ALPACA_API_KEY', 'ALPACA_SECRET_KEY'],
    'ibkr': ['IBKR_HOST', 'IBKR_PORT'],
}


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
        'providers': {
            'paper': {'configured': True, 'source': 'system', 'fingerprint': 'paper', 'masked': {'mode': 'simulated'}},
            'binance': {'configured': False, 'source': None, 'fingerprint': None, 'masked': {}},
            'alpaca': {'configured': False, 'source': None, 'fingerprint': None, 'masked': {}},
            'ibkr': {'configured': False, 'source': None, 'fingerprint': None, 'masked': {}},
        },
        'execution_authorized': False,
        'authorization_reason': None,
        'authorization_scope': 'live-trading',
        'last_validation': None,
        'last_error': None,
        'last_rotation': None,
    }


def _load_state() -> Dict[str, Any]:
    state = _read_json(VAULT_FILE, _default_state())
    state.setdefault('providers', _default_state()['providers'])
    return state


def _load_broker_truth() -> Dict[str, Any]:
    return _read_json(BROKER_TRUTH_FILE, {'selected_broker': 'paper', 'live_path_armed': False, 'validation': {'valid': False, 'blockers': ['broker truth not validated']}})


def _load_execution() -> Dict[str, Any]:
    return _read_json(EXECUTION_FILE, {'mode': 'paper', 'safe_mode': True, 'active_broker': 'paper'})


def _load_risk() -> Dict[str, Any]:
    return _read_json(RISK_FILE, {'kill_switch_triggered': False})


def _mask(value: str) -> str:
    if not value:
        return 'missing'
    if len(value) <= 6:
        return '*' * len(value)
    return f"{value[:3]}***{value[-3:]}"


def _fingerprint(payload: Dict[str, str]) -> str:
    raw = '|'.join(f"{k}={payload.get(k,'')}" for k in sorted(payload))
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]


def _env_provider(provider: str) -> Dict[str, Any]:
    keys = ENV_MAP[provider]
    if provider == 'paper':
        return {'configured': True, 'source': 'system', 'fingerprint': 'paper', 'masked': {'mode': 'simulated'}}
    values = {k: os.getenv(k, '') for k in keys}
    configured = all(values.values())
    masked = {k.lower(): _mask(v) for k, v in values.items()}
    return {
        'configured': configured,
        'source': 'env' if configured else None,
        'fingerprint': _fingerprint(values) if configured else None,
        'masked': masked,
    }


def _merged_provider(state: Dict[str, Any], provider: str) -> Dict[str, Any]:
    stored = (state.get('providers') or {}).get(provider, {})
    env = _env_provider(provider)
    if env.get('configured'):
        return env
    return {
        'configured': bool(stored.get('configured', False)),
        'source': stored.get('source'),
        'fingerprint': stored.get('fingerprint'),
        'masked': stored.get('masked', {}),
    }


def _build_summary() -> Dict[str, Any]:
    state = _load_state()
    broker_truth = _load_broker_truth()
    execution = _load_execution()
    risk = _load_risk()
    selected = broker_truth.get('selected_broker') or state.get('selected_broker') or execution.get('active_broker', 'paper') or 'paper'
    providers = {name: _merged_provider(state, name) for name in ENV_MAP}
    selected_info = providers.get(selected, {'configured': False, 'source': None, 'fingerprint': None, 'masked': {}})
    blockers = []
    if execution.get('mode') != 'live':
        blockers.append('execution mode is not live')
    if bool(execution.get('safe_mode', True)):
        blockers.append('safe mode enabled')
    if bool(risk.get('kill_switch_triggered', False)):
        blockers.append('risk kill switch triggered')
    if selected == 'paper':
        blockers.append('selected broker is paper')
    if not selected_info.get('configured', False):
        blockers.append(f'{selected} credentials are not configured')
    if not bool(broker_truth.get('live_path_armed', False)):
        blockers.append('live broker path not armed')
    authorization_ready = not blockers
    execution_authorized = bool(state.get('execution_authorized', False)) and authorization_ready
    return {
        'status': 'ok',
        'mission': 'QNT-REAL01F',
        'selected_broker': selected,
        'execution_mode': execution.get('mode', 'paper'),
        'safe_mode': bool(execution.get('safe_mode', True)),
        'kill_switch_triggered': bool(risk.get('kill_switch_triggered', False)),
        'live_path_armed': bool(broker_truth.get('live_path_armed', False)),
        'providers': providers,
        'selected_provider': selected_info,
        'authorization_ready': authorization_ready,
        'execution_authorized': execution_authorized,
        'authorization_scope': state.get('authorization_scope', 'live-trading'),
        'authorization_reason': state.get('authorization_reason'),
        'blockers': blockers,
        'last_validation': state.get('last_validation'),
        'last_error': state.get('last_error'),
        'last_rotation': state.get('last_rotation'),
        'generated_at': int(time.time()),
    }


@router.get('/health')
def credential_vault_health() -> Dict[str, Any]:
    summary = _build_summary()
    return {
        'status': 'ok',
        'mission': summary['mission'],
        'selected_broker': summary['selected_broker'],
        'authorization_ready': summary['authorization_ready'],
        'execution_authorized': summary['execution_authorized'],
        'blockers': summary['blockers'],
    }


@router.get('/summary')
def credential_vault_summary() -> Dict[str, Any]:
    return _build_summary()


@router.post('/register')
def credential_vault_register(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    provider = str(payload.get('provider', '')).lower().strip()
    credentials = payload.get('credentials') or {}
    if provider not in ENV_MAP:
        raise HTTPException(status_code=400, detail='provider must be one of paper, binance, alpaca, ibkr')
    state = _load_state()
    if provider == 'paper':
        state['providers']['paper'] = {'configured': True, 'source': 'system', 'fingerprint': 'paper', 'masked': {'mode': 'simulated'}}
    else:
        required = ENV_MAP[provider]
        missing = [k for k in required if not str(credentials.get(k, '')).strip()]
        if missing:
            raise HTTPException(status_code=400, detail=f'missing credentials: {", ".join(missing)}')
        normalized = {k: str(credentials.get(k, '')).strip() for k in required}
        state['providers'][provider] = {
            'configured': True,
            'source': 'manual',
            'fingerprint': _fingerprint(normalized),
            'masked': {k.lower(): _mask(v) for k, v in normalized.items()},
        }
        state['last_rotation'] = int(time.time())
    state['selected_broker'] = provider
    state['last_error'] = None
    _write_json(VAULT_FILE, state)
    return _build_summary()


@router.post('/validate')
def credential_vault_validate() -> Dict[str, Any]:
    state = _load_state()
    summary = _build_summary()
    state['last_validation'] = int(time.time())
    state['last_error'] = None if summary['authorization_ready'] else '; '.join(summary['blockers'])
    _write_json(VAULT_FILE, state)
    return _build_summary()


@router.post('/authorize-execution')
def credential_vault_authorize(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
    state = _load_state()
    reason = str(payload.get('reason', 'operator authorization')).strip()
    summary = _build_summary()
    if not summary['authorization_ready']:
        raise HTTPException(status_code=403, detail='; '.join(summary['blockers']))
    state['execution_authorized'] = True
    state['authorization_reason'] = reason
    state['last_error'] = None
    _write_json(VAULT_FILE, state)
    return _build_summary()


@router.post('/revoke-execution')
def credential_vault_revoke(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
    state = _load_state()
    reason = str(payload.get('reason', 'authorization revoked')).strip()
    state['execution_authorized'] = False
    state['authorization_reason'] = reason
    _write_json(VAULT_FILE, state)
    return _build_summary()


@router.post('/reset')
def credential_vault_reset() -> Dict[str, Any]:
    _write_json(VAULT_FILE, _default_state())
    return _build_summary()
