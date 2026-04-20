import json
import time
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException

router = APIRouter(prefix='/post-trade-lock', tags=['live-position-reconciliation-post-trade-lock'])

ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = ROOT / 'backend' / 'app' / 'state'
LOCK_FILE = STATE_DIR / 'live_position_reconciliation_post_trade_lock_state.json'
SYNC_FILE = STATE_DIR / 'real_position_fill_broker_sync_state.json'
EXECUTION_FILE = STATE_DIR / 'execution_state.json'
SESSION_FILE = STATE_DIR / 'broker_session_handshake_state.json'
TRADE_CONFIRMATION_FILE = STATE_DIR / 'live_trade_confirmation_state.json'


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
        'reconciliation_status': 'idle',
        'lock_status': 'unlocked',
        'drift_detected': False,
        'drift_reason': None,
        'last_reconciled_at': None,
        'last_locked_at': None,
        'latest_fill_reference': None,
        'latest_position_snapshot': None,
        'lock_blockers': [],
        'history': [],
    }


def _load_state() -> Dict[str, Any]:
    return _read_json(LOCK_FILE, _default_state())


def _load_sync() -> Dict[str, Any]:
    return _read_json(SYNC_FILE, {'sync_status': 'idle', 'drift_detected': False, 'drift_reason': None, 'positions': [], 'fills': []})


def _load_execution() -> Dict[str, Any]:
    return _read_json(EXECUTION_FILE, {'mode': 'paper', 'safe_mode': True, 'active_broker': 'paper', 'fills': []})


def _load_session() -> Dict[str, Any]:
    return _read_json(SESSION_FILE, {'handshake_valid': False, 'connectivity_verified': False, 'selected_broker': 'paper'})


def _load_trade_confirmation() -> Dict[str, Any]:
    return _read_json(TRADE_CONFIRMATION_FILE, {'confirmation_status': 'unavailable', 'acknowledged': False, 'confirmed': False})


def _append_history(state: Dict[str, Any], event: Dict[str, Any]) -> None:
    history = list(state.get('history') or [])
    history.append(event)
    state['history'] = history[-20:]


def _latest_fill(sync: Dict[str, Any], execution: Dict[str, Any]) -> Dict[str, Any] | None:
    fills = list(sync.get('fills') or [])
    if fills:
        return fills[-1]
    exe_fills = list(execution.get('fills') or [])
    if exe_fills:
        return exe_fills[-1]
    return None


def _latest_position(sync: Dict[str, Any]) -> Dict[str, Any] | None:
    positions = list(sync.get('positions') or [])
    if positions:
        return positions[-1]
    return None


def _build_summary() -> Dict[str, Any]:
    state = _load_state()
    sync = _load_sync()
    execution = _load_execution()
    session = _load_session()
    confirmation = _load_trade_confirmation()
    latest_fill = _latest_fill(sync, execution)
    latest_position = _latest_position(sync)
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
    if bool(sync.get('drift_detected', False)) or bool(state.get('drift_detected', False)):
        blockers.append(sync.get('drift_reason') or state.get('drift_reason') or 'position drift detected')
    if latest_fill is None:
        blockers.append('no fill evidence available')
    confirmation_ready = bool(confirmation.get('acknowledged', False) or confirmation.get('confirmed', False) or latest_fill is not None)
    if not confirmation_ready:
        blockers.append('trade confirmation not available')
    lock_ready = not blockers
    return {
        'status': 'ok',
        'mission': 'QNT-REAL01I',
        'selected_broker': session.get('selected_broker', execution.get('active_broker', 'paper')),
        'execution_mode': execution.get('mode', 'paper'),
        'safe_mode': bool(execution.get('safe_mode', True)),
        'reconciliation_status': state.get('reconciliation_status', 'idle'),
        'lock_status': state.get('lock_status', 'unlocked'),
        'drift_detected': bool(state.get('drift_detected', False) or sync.get('drift_detected', False)),
        'drift_reason': sync.get('drift_reason') or state.get('drift_reason'),
        'handshake_valid': bool(session.get('handshake_valid', False)),
        'connectivity_verified': bool(session.get('connectivity_verified', False)),
        'sync_status': sync.get('sync_status', 'idle'),
        'latest_fill_reference': state.get('latest_fill_reference') or latest_fill,
        'latest_position_snapshot': state.get('latest_position_snapshot') or latest_position,
        'confirmation_ready': confirmation_ready,
        'post_trade_lock_ready': lock_ready,
        'blockers': blockers,
        'last_reconciled_at': state.get('last_reconciled_at'),
        'last_locked_at': state.get('last_locked_at'),
        'history': state.get('history', []),
        'generated_at': int(time.time()),
    }


@router.get('/health')
def post_trade_lock_health() -> Dict[str, Any]:
    summary = _build_summary()
    return {
        'status': 'ok',
        'mission': summary['mission'],
        'reconciliation_status': summary['reconciliation_status'],
        'lock_status': summary['lock_status'],
        'post_trade_lock_ready': summary['post_trade_lock_ready'],
        'blockers': summary['blockers'],
    }


@router.get('/summary')
def post_trade_lock_summary() -> Dict[str, Any]:
    return _build_summary()


@router.post('/reconcile-position')
def reconcile_position(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
    state = _load_state()
    sync = _load_sync()
    execution = _load_execution()
    latest_fill = _latest_fill(sync, execution)
    latest_position = payload.get('position_snapshot') or _latest_position(sync)
    force_drift = bool(payload.get('force_drift', False))

    drift_detected = bool(sync.get('drift_detected', False)) or force_drift
    drift_reason = sync.get('drift_reason')
    if latest_fill and latest_position and not drift_detected:
        fill_symbol = str(latest_fill.get('symbol') or latest_fill.get('order', {}).get('symbol') or '').upper()
        pos_symbol = str(latest_position.get('symbol') or latest_position.get('asset') or '').upper()
        if fill_symbol and pos_symbol and fill_symbol != pos_symbol:
            drift_detected = True
            drift_reason = f'latest fill {fill_symbol} does not match position snapshot {pos_symbol}'
    elif latest_fill and latest_position is None and not drift_detected:
        drift_detected = True
        drift_reason = 'fill exists but no position snapshot available'

    state['reconciliation_status'] = 'reconciled' if not drift_detected else 'drift'
    state['drift_detected'] = drift_detected
    state['drift_reason'] = drift_reason
    state['last_reconciled_at'] = int(time.time())
    state['latest_fill_reference'] = latest_fill
    state['latest_position_snapshot'] = latest_position
    state['lock_status'] = 'blocked' if drift_detected else state.get('lock_status', 'unlocked')
    state['lock_blockers'] = [drift_reason] if drift_detected and drift_reason else []
    _append_history(state, {
        'event': 'reconcile-position',
        'timestamp': state['last_reconciled_at'],
        'drift_detected': drift_detected,
        'drift_reason': drift_reason,
    })
    _write_json(LOCK_FILE, state)
    return _build_summary()


@router.post('/lock-trade-state')
def lock_trade_state(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
    state = _load_state()
    summary = _build_summary()
    if not summary.get('post_trade_lock_ready', False):
        state['lock_status'] = 'blocked'
        state['lock_blockers'] = summary.get('blockers', [])
        state['last_locked_at'] = int(time.time())
        _append_history(state, {
            'event': 'lock-trade-state-blocked',
            'timestamp': state['last_locked_at'],
            'blockers': summary.get('blockers', []),
        })
        _write_json(LOCK_FILE, state)
        raise HTTPException(status_code=400, detail={'message': 'post-trade state lock blocked', 'blockers': summary.get('blockers', [])})

    state['lock_status'] = 'locked'
    state['lock_blockers'] = []
    state['last_locked_at'] = int(time.time())
    if payload.get('position_snapshot') is not None:
        state['latest_position_snapshot'] = payload.get('position_snapshot')
    _append_history(state, {
        'event': 'lock-trade-state',
        'timestamp': state['last_locked_at'],
        'lock_reference': payload.get('lock_reference') or f'REAL01I_LOCK_{state["last_locked_at"]}',
    })
    _write_json(LOCK_FILE, state)
    return _build_summary()


@router.post('/reset')
def post_trade_lock_reset() -> Dict[str, Any]:
    state = _default_state()
    _append_history(state, {'event': 'reset', 'timestamp': int(time.time())})
    _write_json(LOCK_FILE, state)
    return _build_summary()
