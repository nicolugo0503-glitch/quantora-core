import json
import time
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Body

router = APIRouter(prefix='/cash-truth', tags=['real-broker-cash-buying-power-margin-truth'])

ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = ROOT / 'backend' / 'app' / 'state'
ARTIFACTS_DIR = ROOT / 'backend' / 'artifacts'

CASH_FILE = STATE_DIR / 'real_broker_cash_buying_power_margin_truth_state.json'
EXECUTION_FILE = STATE_DIR / 'execution_state.json'
SYNC_FILE = STATE_DIR / 'real_position_fill_broker_sync_state.json'
PNL_FILE = STATE_DIR / 'real_pnl_equity_exposure_truth_state.json'
SESSION_FILE = STATE_DIR / 'broker_session_handshake_state.json'
LEDGER_FILE = ARTIFACTS_DIR / 'capital_ledger.json'


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
        'truth_status': 'idle',
        'selected_broker': 'paper',
        'currency': 'USD',
        'cash_balance': 100000.0,
        'settled_cash': 100000.0,
        'unsettled_cash': 0.0,
        'buying_power': 100000.0,
        'available_buying_power': 100000.0,
        'initial_margin_used': 0.0,
        'maintenance_margin_used': 0.0,
        'margin_excess': 100000.0,
        'margin_ratio': 0.0,
        'blockers': [],
        'source': 'ledger',
        'last_synced_at': None,
        'history': [],
    }


def _load_state() -> Dict[str, Any]:
    return _read_json(CASH_FILE, _default_state())


def _load_execution() -> Dict[str, Any]:
    return _read_json(EXECUTION_FILE, {'mode': 'paper', 'safe_mode': True, 'active_broker': 'paper'})


def _load_sync() -> Dict[str, Any]:
    return _read_json(SYNC_FILE, {'positions': [], 'sync_status': 'idle', 'drift_detected': False})


def _load_pnl() -> Dict[str, Any]:
    return _read_json(PNL_FILE, {'current_equity': 100000.0, 'gross_exposure': 0.0, 'positions_market_value': 0.0, 'truth_status': 'idle'})


def _load_session() -> Dict[str, Any]:
    return _read_json(SESSION_FILE, {'handshake_valid': False, 'connectivity_verified': False, 'selected_broker': 'paper'})


def _load_ledger() -> Dict[str, Any]:
    return _read_json(LEDGER_FILE, {'balance': 100000.0, 'available': 100000.0, 'allocated': 0.0, 'currency': 'USD'})


def _append_history(state: Dict[str, Any], event: Dict[str, Any]) -> None:
    history = list(state.get('history') or [])
    history.append(event)
    state['history'] = history[-20:]


def _recompute(state: Dict[str, Any]) -> Dict[str, Any]:
    execution = _load_execution()
    sync = _load_sync()
    pnl = _load_pnl()
    session = _load_session()
    ledger = _load_ledger()

    selected_broker = session.get('selected_broker') or execution.get('active_broker', 'paper')
    currency = ledger.get('currency', 'USD')
    gross_exposure = float(pnl.get('gross_exposure', 0.0) or 0.0)
    equity = float(pnl.get('current_equity', ledger.get('balance', 100000.0)) or 0.0)
    settled_cash = float(ledger.get('available', ledger.get('balance', 0.0)) or 0.0)
    allocated = float(ledger.get('allocated', 0.0) or 0.0)
    unsettled_cash = max(0.0, allocated)
    initial_margin_used = round(gross_exposure * 0.5, 2)
    maintenance_margin_used = round(gross_exposure * 0.3, 2)
    buying_power = round(max(0.0, equity * 2.0 - initial_margin_used), 2)
    available_buying_power = round(max(0.0, buying_power - gross_exposure), 2)
    margin_excess = round(max(0.0, equity - maintenance_margin_used), 2)
    margin_ratio = round((maintenance_margin_used / equity), 6) if equity > 0 else 0.0

    blockers = []
    if execution.get('mode', 'paper') != 'live':
        blockers.append('execution mode is not live')
    if bool(execution.get('safe_mode', True)):
        blockers.append('safe mode enabled')
    if not bool(session.get('handshake_valid', False)):
        blockers.append('broker session handshake not valid')
    if not bool(session.get('connectivity_verified', False)):
        blockers.append('broker connectivity not verified')
    if sync.get('sync_status') in {'idle', None}:
        blockers.append('broker sync not refreshed')
    if bool(sync.get('drift_detected', False)):
        blockers.append(sync.get('drift_reason') or 'broker sync drift detected')

    state.update({
        'truth_status': 'ready' if not blockers else 'warning',
        'selected_broker': selected_broker,
        'currency': currency,
        'cash_balance': round(settled_cash + unsettled_cash, 2),
        'settled_cash': round(settled_cash, 2),
        'unsettled_cash': round(unsettled_cash, 2),
        'buying_power': buying_power,
        'available_buying_power': available_buying_power,
        'initial_margin_used': initial_margin_used,
        'maintenance_margin_used': maintenance_margin_used,
        'margin_excess': margin_excess,
        'margin_ratio': margin_ratio,
        'blockers': blockers,
        'source': 'ledger+pnl+sync',
        'last_synced_at': int(time.time()),
        'execution_mode': execution.get('mode', 'paper'),
        'safe_mode': bool(execution.get('safe_mode', True)),
    })
    return state


@router.get('/health')
def cash_truth_health() -> Dict[str, Any]:
    state = _recompute(_load_state())
    _write_json(CASH_FILE, state)
    return {
        'status': 'ok',
        'mission': 'QNT-REAL01J',
        'truth_status': state['truth_status'],
        'selected_broker': state['selected_broker'],
        'cash_balance': state['cash_balance'],
        'buying_power': state['buying_power'],
        'blockers': state['blockers'],
    }


@router.get('/summary')
def cash_truth_summary() -> Dict[str, Any]:
    state = _recompute(_load_state())
    _write_json(CASH_FILE, state)
    state['status'] = 'ok'
    state['mission'] = 'QNT-REAL01J'
    return state


@router.post('/sync-context')
def cash_truth_sync_context(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
    state = _load_state()
    if 'settled_cash' in payload:
        state['settled_cash'] = float(payload['settled_cash'])
    if 'unsettled_cash' in payload:
        state['unsettled_cash'] = float(payload['unsettled_cash'])
    if 'buying_power' in payload:
        state['buying_power'] = float(payload['buying_power'])
    if 'available_buying_power' in payload:
        state['available_buying_power'] = float(payload['available_buying_power'])
    _append_history(state, {'event': 'sync-context', 'timestamp': int(time.time())})
    state = _recompute(state)
    _write_json(CASH_FILE, state)
    state['status'] = 'ok'
    state['mission'] = 'QNT-REAL01J'
    return state


@router.post('/recompute')
def cash_truth_recompute(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
    state = _load_state()
    if 'buying_power_multiplier' in payload:
        # reserved for future override, kept for compatibility
        state['buying_power_multiplier'] = float(payload['buying_power_multiplier'])
    _append_history(state, {'event': 'recompute', 'timestamp': int(time.time())})
    state = _recompute(state)
    _write_json(CASH_FILE, state)
    state['status'] = 'ok'
    state['mission'] = 'QNT-REAL01J'
    return state


@router.post('/reset')
def cash_truth_reset() -> Dict[str, Any]:
    state = _default_state()
    _append_history(state, {'event': 'reset', 'timestamp': int(time.time())})
    state = _recompute(state)
    _write_json(CASH_FILE, state)
    state['status'] = 'ok'
    state['mission'] = 'QNT-REAL01J'
    return state
