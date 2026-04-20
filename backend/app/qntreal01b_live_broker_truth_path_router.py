import json
import os
import time
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException

router = APIRouter(prefix='/broker-truth', tags=['live-broker-truth'])

ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = ROOT / 'backend' / 'app' / 'state'
EXECUTION_FILE = STATE_DIR / 'execution_state.json'
TRUTH_FILE = STATE_DIR / 'live_broker_truth_state.json'


def _read_json(path: Path, fallback: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return fallback


def _write_json(path: Path, data: Dict[str, Any]) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding='utf-8')
    return data


def _load_execution() -> Dict[str, Any]:
    return _read_json(EXECUTION_FILE, {'mode': 'paper', 'safe_mode': True, 'active_broker': 'paper', 'fills': [], 'orders': []})


def _load_truth() -> Dict[str, Any]:
    return _read_json(TRUTH_FILE, {
        'selected_broker': 'paper',
        'preferred_live_broker': 'binance',
        'live_path_armed': False,
        'last_validation': None,
        'last_error': None,
        'credentials': {},
    })


def _save_truth(data: Dict[str, Any]) -> Dict[str, Any]:
    return _write_json(TRUTH_FILE, data)


def _mask(v: str) -> str:
    if not v:
        return 'missing'
    if len(v) <= 6:
        return '*' * len(v)
    return f"{v[:3]}***{v[-3:]}"


def _env_presence() -> Dict[str, Dict[str, Any]]:
    return {
        'paper': {'ready': True, 'details': {'mode': 'simulated'}},
        'binance': {
            'ready': bool(os.getenv('BINANCE_API_KEY') and os.getenv('BINANCE_SECRET')),
            'details': {
                'api_key': _mask(os.getenv('BINANCE_API_KEY', '')),
                'secret': _mask(os.getenv('BINANCE_SECRET', '')),
            },
        },
        'alpaca': {
            'ready': bool(os.getenv('ALPACA_API_KEY') and os.getenv('ALPACA_SECRET_KEY')),
            'details': {
                'api_key': _mask(os.getenv('ALPACA_API_KEY', '')),
                'secret': _mask(os.getenv('ALPACA_SECRET_KEY', '')),
                'base_url': os.getenv('ALPACA_BASE_URL', 'missing'),
            },
        },
        'ibkr': {
            'ready': bool(os.getenv('IBKR_HOST') and os.getenv('IBKR_PORT')),
            'details': {
                'host': os.getenv('IBKR_HOST', 'missing'),
                'port': os.getenv('IBKR_PORT', 'missing'),
            },
        },
    }


def _build_summary() -> Dict[str, Any]:
    execution = _load_execution()
    truth = _load_truth()
    brokers = _env_presence()
    selected = truth.get('selected_broker') or execution.get('active_broker', 'paper') or 'paper'
    preferred_live = truth.get('preferred_live_broker', 'binance')
    current = brokers.get(selected, {'ready': False, 'details': {}})
    preferred = brokers.get(preferred_live, {'ready': False, 'details': {}})
    live_ready = (
        execution.get('mode') == 'live'
        and not execution.get('safe_mode', True)
        and selected != 'paper'
        and current.get('ready', False)
        and bool(truth.get('live_path_armed', False))
    )
    blockers = []
    if execution.get('mode') != 'live':
        blockers.append('execution mode is not live')
    if execution.get('safe_mode', True):
        blockers.append('safe mode is enabled')
    if selected == 'paper':
        blockers.append('selected broker is paper')
    if not current.get('ready', False):
        blockers.append(f'{selected} credentials are not ready')
    if not truth.get('live_path_armed', False):
        blockers.append('live broker path is not armed')
    return {
        'status': 'ok',
        'mission': 'QNT-REAL01B',
        'selected_broker': selected,
        'preferred_live_broker': preferred_live,
        'active_broker': execution.get('active_broker', 'paper'),
        'execution_mode': execution.get('mode', 'paper'),
        'safe_mode': bool(execution.get('safe_mode', True)),
        'live_path_armed': bool(truth.get('live_path_armed', False)),
        'live_ready': live_ready,
        'blockers': blockers,
        'brokers': brokers,
        'selected_broker_ready': bool(current.get('ready', False)),
        'preferred_live_ready': bool(preferred.get('ready', False)),
        'last_validation': truth.get('last_validation'),
        'last_error': truth.get('last_error'),
        'generated_at': int(time.time()),
    }


@router.get('/health')
def broker_truth_health() -> Dict[str, Any]:
    summary = _build_summary()
    return {
        'status': 'ok',
        'mission': summary['mission'],
        'selected_broker': summary['selected_broker'],
        'live_ready': summary['live_ready'],
        'blockers': summary['blockers'],
    }


@router.get('/summary')
def broker_truth_summary() -> Dict[str, Any]:
    return _build_summary()


@router.post('/validate')
def broker_truth_validate() -> Dict[str, Any]:
    truth = _load_truth()
    summary = _build_summary()
    truth['last_validation'] = int(time.time())
    truth['last_error'] = None if summary['selected_broker_ready'] else f"{summary['selected_broker']} credentials missing"
    truth['credentials'] = summary['brokers']
    _save_truth(truth)
    return _build_summary()


@router.post('/select-broker')
def broker_truth_select(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    broker = str(payload.get('broker', '')).lower().strip()
    if broker not in {'paper', 'binance', 'alpaca', 'ibkr'}:
        raise HTTPException(status_code=400, detail='broker must be one of paper, binance, alpaca, ibkr')
    execution = _load_execution()
    truth = _load_truth()
    truth['selected_broker'] = broker
    execution['active_broker'] = broker
    _write_json(EXECUTION_FILE, execution)
    _save_truth(truth)
    return _build_summary()


@router.post('/arm-live-path')
def broker_truth_arm(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    enabled = bool(payload.get('enabled', True))
    truth = _load_truth()
    truth['live_path_armed'] = enabled
    _save_truth(truth)
    return _build_summary()
