import json
import time
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException

from backend.app.execution.order_router import OrderRouter
from backend.app.execution.fill_handler import load_state as load_execution_state

router = APIRouter(prefix='/order-entry', tags=['real-order-entry-guarded-live-surface'])

ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = ROOT / 'backend' / 'app' / 'state'
ENTRY_FILE = STATE_DIR / 'real_order_entry_surface_state.json'
BROKER_TRUTH_FILE = STATE_DIR / 'live_broker_truth_state.json'
SYNC_FILE = STATE_DIR / 'real_position_fill_broker_sync_state.json'
PNL_FILE = STATE_DIR / 'real_pnl_equity_exposure_truth_state.json'
RISK_FILE = STATE_DIR / 'risk_kill_switch_state.json'
VAULT_FILE = STATE_DIR / 'live_broker_credential_vault_state.json'
SESSION_FILE = STATE_DIR / 'broker_session_handshake_state.json'


def _read_json(path: Path, fallback: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return fallback


def _write_json(path: Path, data: Dict[str, Any]) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding='utf-8')
    return data


def _load_state() -> Dict[str, Any]:
    return _read_json(ENTRY_FILE, {
        'selected_symbol': 'BTCUSDT',
        'selected_side': 'BUY',
        'selected_qty': 0.01,
        'selected_order_type': 'MARKET',
        'selected_price': None,
        'strategy_id': 'OPERATOR_MANUAL',
        'allocation_id': 'REAL01E_DEFAULT',
        'risk_tag': 'OPERATOR',
        'decision_id': None,
        'preview': None,
        'last_submission': None,
        'submission_count': 0,
        'blocked_count': 0,
        'last_error': None,
        'surface_status': 'idle',
    })


def _load_execution() -> Dict[str, Any]:
    return load_execution_state()


def _load_truth() -> Dict[str, Any]:
    return _read_json(PNL_FILE, {'current_equity': 0.0, 'gross_exposure': 0.0, 'truth_status': 'idle', 'blockers': []})


def _load_broker_truth() -> Dict[str, Any]:
    return _read_json(BROKER_TRUTH_FILE, {'selected_broker': 'paper', 'live_path_armed': False, 'validation': {'valid': False, 'blockers': ['broker truth not validated']}})


def _load_sync() -> Dict[str, Any]:
    return _read_json(SYNC_FILE, {'sync_status': 'idle', 'drift_detected': False, 'positions': [], 'fills': []})


def _load_risk() -> Dict[str, Any]:
    return _read_json(RISK_FILE, {'armed': True, 'kill_switch_triggered': False, 'trigger_reason': None})


def _load_vault() -> Dict[str, Any]:
    return _read_json(VAULT_FILE, {'execution_authorized': False, 'selected_broker': 'paper', 'providers': {}})


def _load_session() -> Dict[str, Any]:
    return _read_json(SESSION_FILE, {'handshake_valid': False, 'connectivity_verified': False, 'session_status': 'idle', 'connectivity_status': 'unknown'})


def _now() -> int:
    return int(time.time())


def _live_readiness() -> Dict[str, Any]:
    execution = _load_execution()
    broker_truth = _load_broker_truth()
    sync = _load_sync()
    pnl = _load_truth()
    risk = _load_risk()
    vault = _load_vault()
    session = _load_session()
    blockers = []
    if execution.get('mode', 'paper') != 'live':
        blockers.append('execution mode is not live')
    if bool(execution.get('safe_mode', True)):
        blockers.append('safe mode enabled')
    if bool(risk.get('kill_switch_triggered', False)):
        blockers.append('risk kill switch triggered')
    if not bool(broker_truth.get('live_path_armed', False)):
        blockers.append('live broker path not armed')
    if not bool(vault.get('execution_authorized', False)):
        blockers.append('execution authorization gate not approved')
    if not bool(session.get('handshake_valid', False)):
        blockers.append('broker session handshake not valid')
    if not bool(session.get('connectivity_verified', False)):
        blockers.append('broker connectivity not verified')
    validation = broker_truth.get('validation') or {}
    if not bool(validation.get('valid', False)):
        blockers.extend(validation.get('blockers') or ['broker truth validation failed'])
    if sync.get('sync_status') in {'idle', None}:
        blockers.append('broker sync not refreshed')
    if bool(sync.get('drift_detected', False)):
        blockers.append(sync.get('drift_reason') or 'broker sync drift detected')
    if pnl.get('truth_status') in {'idle', None}:
        blockers.append('pnl truth not ready')
    blockers = list(dict.fromkeys(blockers))
    return {'ready': not blockers, 'blockers': blockers}


def _build_envelope(payload: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
    symbol = str(payload.get('symbol') or state.get('selected_symbol') or '').upper()
    side = str(payload.get('side') or state.get('selected_side') or 'BUY').upper()
    order_type = str(payload.get('order_type') or state.get('selected_order_type') or 'MARKET').upper()
    qty = float(payload.get('qty') or state.get('selected_qty') or 0.0)
    price = payload.get('price', state.get('selected_price'))
    price = None if price in (None, '', 'null') else float(price)
    strategy_id = str(payload.get('strategy_id') or state.get('strategy_id') or 'OPERATOR_MANUAL')
    allocation_id = str(payload.get('allocation_id') or state.get('allocation_id') or 'REAL01E_DEFAULT')
    risk_tag = str(payload.get('risk_tag') or state.get('risk_tag') or 'OPERATOR')
    decision_id = str(payload.get('decision_id') or f'REAL01E_{_now()}')
    envelope = {
        'symbol': symbol,
        'side': side,
        'qty': qty,
        'order_type': order_type,
        'price': price,
        'strategy_id': strategy_id,
        'allocation_id': allocation_id,
        'risk_tag': risk_tag,
        'decision_id': decision_id,
    }
    pnl = _load_truth()
    if pnl.get('current_equity') is not None:
        envelope['portfolio_value_snapshot'] = float(pnl.get('current_equity') or 0.0)
    if order_type == 'LIMIT' and price:
        envelope['notional_estimate'] = round(qty * price, 8)
    return envelope


def _validate_envelope(envelope: Dict[str, Any]) -> None:
    if not envelope['symbol']:
        raise HTTPException(status_code=400, detail='symbol is required')
    if envelope['side'] not in {'BUY', 'SELL'}:
        raise HTTPException(status_code=400, detail='side must be BUY or SELL')
    if float(envelope['qty']) <= 0:
        raise HTTPException(status_code=400, detail='qty must be positive')
    if envelope['order_type'] not in {'MARKET', 'LIMIT'}:
        raise HTTPException(status_code=400, detail='order_type must be MARKET or LIMIT')
    if envelope['order_type'] == 'LIMIT' and not envelope.get('price'):
        raise HTTPException(status_code=400, detail='limit orders require price')


@router.get('/health')
def order_entry_health() -> Dict[str, Any]:
    readiness = _live_readiness()
    state = _load_state()
    return {
        'status': 'ok',
        'mission': 'QNT-REAL01E',
        'surface_status': state.get('surface_status', 'idle'),
        'live_ready': readiness['ready'],
        'blockers': readiness['blockers'],
        'submission_count': state.get('submission_count', 0),
        'blocked_count': state.get('blocked_count', 0),
    }


@router.get('/summary')
def order_entry_summary() -> Dict[str, Any]:
    state = _load_state()
    readiness = _live_readiness()
    execution = _load_execution()
    broker_truth = _load_broker_truth()
    pnl = _load_truth()
    return {
        'status': 'ok',
        'mission': 'QNT-REAL01E',
        'surface_state': state,
        'live_readiness': readiness,
        'execution': {
            'mode': execution.get('mode', 'paper'),
            'safe_mode': bool(execution.get('safe_mode', True)),
            'active_broker': execution.get('active_broker', 'paper'),
        },
        'broker_truth': {
            'selected_broker': broker_truth.get('selected_broker', execution.get('active_broker', 'paper')),
            'live_path_armed': bool(broker_truth.get('live_path_armed', False)),
        },
        'pnl_truth': {
            'current_equity': pnl.get('current_equity', 0.0),
            'gross_exposure': pnl.get('gross_exposure', 0.0),
            'truth_status': pnl.get('truth_status', 'idle'),
        },
    }


@router.post('/preview')
def order_entry_preview(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
    state = _load_state()
    envelope = _build_envelope(payload, state)
    _validate_envelope(envelope)
    readiness = _live_readiness()
    preview = {
        'symbol': envelope['symbol'],
        'side': envelope['side'],
        'qty': envelope['qty'],
        'order_type': envelope['order_type'],
        'price': envelope.get('price'),
        'notional_estimate': envelope.get('notional_estimate') or (round(float(envelope['qty']) * float(envelope.get('price') or 0.0), 8) if envelope['order_type'] == 'LIMIT' else None),
        'portfolio_value_snapshot': envelope.get('portfolio_value_snapshot'),
        'would_route_live': readiness['ready'],
        'blockers': readiness['blockers'],
        'decision_id': envelope['decision_id'],
    }
    state.update({
        'selected_symbol': envelope['symbol'],
        'selected_side': envelope['side'],
        'selected_qty': envelope['qty'],
        'selected_order_type': envelope['order_type'],
        'selected_price': envelope.get('price'),
        'strategy_id': envelope['strategy_id'],
        'allocation_id': envelope['allocation_id'],
        'risk_tag': envelope['risk_tag'],
        'decision_id': envelope['decision_id'],
        'preview': preview,
        'surface_status': 'previewed',
        'last_error': None,
    })
    _write_json(ENTRY_FILE, state)
    return {'status': 'ok', 'mission': 'QNT-REAL01E', 'preview': preview}


@router.post('/submit')
def order_entry_submit(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    state = _load_state()
    envelope = _build_envelope(payload, state)
    _validate_envelope(envelope)
    readiness = _live_readiness()
    if not readiness['ready']:
        state['blocked_count'] = int(state.get('blocked_count', 0)) + 1
        state['last_error'] = '; '.join(readiness['blockers'])
        state['surface_status'] = 'blocked'
        _write_json(ENTRY_FILE, state)
        raise HTTPException(status_code=403, detail={'message': 'live order entry blocked', 'blockers': readiness['blockers']})
    try:
        execution = OrderRouter().route(envelope)
    except PermissionError as exc:
        state['blocked_count'] = int(state.get('blocked_count', 0)) + 1
        state['last_error'] = str(exc)
        state['surface_status'] = 'blocked'
        _write_json(ENTRY_FILE, state)
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RuntimeError as exc:
        state['blocked_count'] = int(state.get('blocked_count', 0)) + 1
        state['last_error'] = str(exc)
        state['surface_status'] = 'blocked'
        _write_json(ENTRY_FILE, state)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    state.update({
        'selected_symbol': envelope['symbol'],
        'selected_side': envelope['side'],
        'selected_qty': envelope['qty'],
        'selected_order_type': envelope['order_type'],
        'selected_price': envelope.get('price'),
        'strategy_id': envelope['strategy_id'],
        'allocation_id': envelope['allocation_id'],
        'risk_tag': envelope['risk_tag'],
        'decision_id': envelope['decision_id'],
        'last_submission': {
            'submitted_at': _now(),
            'envelope': envelope,
            'execution': execution,
        },
        'submission_count': int(state.get('submission_count', 0)) + 1,
        'last_error': None,
        'surface_status': 'submitted',
    })
    _write_json(ENTRY_FILE, state)
    return {
        'status': 'ok',
        'mission': 'QNT-REAL01E',
        'envelope': envelope,
        'execution': execution,
        'surface_status': state['surface_status'],
        'submission_count': state['submission_count'],
    }


@router.post('/reset')
def order_entry_reset() -> Dict[str, Any]:
    state = {
        'selected_symbol': 'BTCUSDT',
        'selected_side': 'BUY',
        'selected_qty': 0.01,
        'selected_order_type': 'MARKET',
        'selected_price': None,
        'strategy_id': 'OPERATOR_MANUAL',
        'allocation_id': 'REAL01E_DEFAULT',
        'risk_tag': 'OPERATOR',
        'decision_id': None,
        'preview': None,
        'last_submission': None,
        'submission_count': 0,
        'blocked_count': 0,
        'last_error': None,
        'surface_status': 'idle',
    }
    _write_json(ENTRY_FILE, state)
    return {'status': 'ok', 'mission': 'QNT-REAL01E', 'surface_state': state}
