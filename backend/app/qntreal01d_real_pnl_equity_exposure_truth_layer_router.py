import json
import time
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Body, HTTPException

router = APIRouter(prefix='/pnl-truth', tags=['real-pnl-equity-exposure-truth'])

ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = ROOT / 'backend' / 'app' / 'state'
ARTIFACTS_DIR = ROOT / 'backend' / 'artifacts'

EXECUTION_FILE = STATE_DIR / 'execution_state.json'
SYNC_FILE = STATE_DIR / 'real_position_fill_broker_sync_state.json'
RISK_FILE = STATE_DIR / 'risk_kill_switch_state.json'
LEDGER_FILE = ARTIFACTS_DIR / 'capital_ledger.json'
TRUTH_FILE = STATE_DIR / 'real_pnl_equity_exposure_truth_state.json'


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
    return _read_json(EXECUTION_FILE, {'mode': 'paper', 'safe_mode': True, 'active_broker': 'paper', 'fills': [], 'positions': []})


def _load_sync() -> Dict[str, Any]:
    return _read_json(SYNC_FILE, {'positions': [], 'fills': [], 'sync_status': 'idle', 'drift_detected': False})


def _load_risk() -> Dict[str, Any]:
    return _read_json(RISK_FILE, {'kill_switch_triggered': False, 'metrics': {'open_notional': 0.0}})


def _load_ledger() -> Dict[str, Any]:
    return _read_json(LEDGER_FILE, {'balance': 100000.0, 'available': 100000.0, 'allocated': 0.0, 'currency': 'USD'})


def _load_truth() -> Dict[str, Any]:
    return _read_json(TRUTH_FILE, {
        'baseline_equity': 100000.0,
        'current_equity': 100000.0,
        'cash_balance': 100000.0,
        'positions_market_value': 0.0,
        'gross_exposure': 0.0,
        'net_exposure': 0.0,
        'realized_pnl': 0.0,
        'unrealized_pnl': 0.0,
        'daily_pnl': 0.0,
        'net_return_pct': 0.0,
        'mark_prices': {},
        'position_snapshots': [],
        'last_mark_at': None,
        'last_recompute_at': None,
        'truth_status': 'idle',
        'blockers': [],
    })


def _save_truth(data: Dict[str, Any]) -> Dict[str, Any]:
    return _write_json(TRUTH_FILE, data)


def _normalize_positions(sync: Dict[str, Any], execution: Dict[str, Any]) -> List[Dict[str, Any]]:
    positions = sync.get('positions') or execution.get('positions') or []
    if not isinstance(positions, list):
        return []
    out = []
    for pos in positions[:100]:
        if not isinstance(pos, dict):
            continue
        qty = float(pos.get('qty') or pos.get('quantity') or 0.0)
        avg_price = float(pos.get('avg_price') or pos.get('average_price') or pos.get('fill_price') or 0.0)
        symbol = pos.get('symbol') or pos.get('asset') or 'UNKNOWN'
        out.append({
            'symbol': symbol,
            'qty': qty,
            'avg_price': avg_price,
            'source': pos.get('source') or execution.get('active_broker', 'paper'),
        })
    return out


def _recompute_core(state: Dict[str, Any]) -> Dict[str, Any]:
    execution = _load_execution()
    sync = _load_sync()
    risk = _load_risk()
    ledger = _load_ledger()
    positions = _normalize_positions(sync, execution)
    marks = state.get('mark_prices') or {}

    cash_balance = float(ledger.get('available', ledger.get('balance', 0.0)))
    baseline = float(state.get('baseline_equity') or ledger.get('balance', 0.0) or 0.0)
    positions_market_value = 0.0
    gross_exposure = 0.0
    net_exposure = 0.0
    unrealized_pnl = 0.0
    enriched = []

    for pos in positions:
        symbol = pos['symbol']
        qty = float(pos['qty'])
        avg = float(pos['avg_price'])
        mark = float(marks.get(symbol, avg))
        mv = qty * mark
        upl = qty * (mark - avg)
        positions_market_value += mv
        gross_exposure += abs(mv)
        net_exposure += mv
        unrealized_pnl += upl
        enriched.append({**pos, 'mark_price': round(mark, 8), 'market_value': round(mv, 8), 'unrealized_pnl': round(upl, 8)})

    current_equity = cash_balance + positions_market_value
    daily_pnl = current_equity - baseline
    net_return_pct = (daily_pnl / baseline * 100.0) if baseline else 0.0

    blockers = []
    if bool(sync.get('drift_detected', False)):
        blockers.append(sync.get('drift_reason') or 'broker sync drift detected')
    if bool(risk.get('kill_switch_triggered', False)):
        blockers.append('risk kill switch triggered')
    if sync.get('sync_status') in {None, 'idle'}:
        blockers.append('broker sync not refreshed')

    state.update({
        'baseline_equity': round(baseline, 2),
        'current_equity': round(current_equity, 2),
        'cash_balance': round(cash_balance, 2),
        'positions_market_value': round(positions_market_value, 2),
        'gross_exposure': round(gross_exposure, 2),
        'net_exposure': round(net_exposure, 2),
        'realized_pnl': round(float(state.get('realized_pnl', 0.0)), 2),
        'unrealized_pnl': round(unrealized_pnl, 2),
        'daily_pnl': round(daily_pnl, 2),
        'net_return_pct': round(net_return_pct, 4),
        'position_snapshots': enriched,
        'last_recompute_at': int(time.time()),
        'truth_status': 'ready' if not blockers else 'warning',
        'blockers': blockers,
        'currency': ledger.get('currency', 'USD'),
        'selected_broker': execution.get('active_broker', 'paper'),
        'execution_mode': execution.get('mode', 'paper'),
        'safe_mode': bool(execution.get('safe_mode', True)),
    })
    return state


@router.get('/health')
def pnl_truth_health() -> Dict[str, Any]:
    state = _recompute_core(_load_truth())
    _save_truth(state)
    return {
        'status': 'ok',
        'mission': 'QNT-REAL01D',
        'truth_status': state['truth_status'],
        'current_equity': state['current_equity'],
        'gross_exposure': state['gross_exposure'],
        'blockers': state['blockers'],
    }


@router.get('/summary')
def pnl_truth_summary() -> Dict[str, Any]:
    state = _recompute_core(_load_truth())
    _save_truth(state)
    state['mission'] = 'QNT-REAL01D'
    state['status'] = 'ok'
    return state


@router.post('/sync-context')
def pnl_truth_sync_context(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
    state = _load_truth()
    if 'baseline_equity' in payload:
        state['baseline_equity'] = float(payload['baseline_equity'])
    state = _recompute_core(state)
    _save_truth(state)
    state['mission'] = 'QNT-REAL01D'
    state['status'] = 'ok'
    return state


@router.post('/mark-snapshot')
def pnl_truth_mark_snapshot(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    marks = payload.get('mark_prices')
    if not isinstance(marks, dict) or not marks:
        raise HTTPException(status_code=400, detail='mark_prices must be a non-empty object')
    state = _load_truth()
    existing = state.get('mark_prices') or {}
    for symbol, value in marks.items():
        existing[str(symbol)] = float(value)
    state['mark_prices'] = existing
    state['last_mark_at'] = int(time.time())
    state = _recompute_core(state)
    _save_truth(state)
    state['mission'] = 'QNT-REAL01D'
    state['status'] = 'ok'
    return state


@router.post('/recompute')
def pnl_truth_recompute(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
    state = _load_truth()
    if 'realized_pnl' in payload:
        state['realized_pnl'] = float(payload['realized_pnl'])
    if 'baseline_equity' in payload:
        state['baseline_equity'] = float(payload['baseline_equity'])
    state = _recompute_core(state)
    _save_truth(state)
    state['mission'] = 'QNT-REAL01D'
    state['status'] = 'ok'
    return state


@router.post('/reset')
def pnl_truth_reset() -> Dict[str, Any]:
    state = {
        'baseline_equity': 100000.0,
        'current_equity': 100000.0,
        'cash_balance': 100000.0,
        'positions_market_value': 0.0,
        'gross_exposure': 0.0,
        'net_exposure': 0.0,
        'realized_pnl': 0.0,
        'unrealized_pnl': 0.0,
        'daily_pnl': 0.0,
        'net_return_pct': 0.0,
        'mark_prices': {},
        'position_snapshots': [],
        'last_mark_at': None,
        'last_recompute_at': None,
        'truth_status': 'idle',
        'blockers': [],
    }
    state = _recompute_core(state)
    _save_truth(state)
    state['mission'] = 'QNT-REAL01D'
    state['status'] = 'ok'
    return state
