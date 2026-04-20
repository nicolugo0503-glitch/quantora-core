import json
import time
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Body, HTTPException

router = APIRouter(prefix='/broker-sync', tags=['real-position-fill-broker-sync'])

ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = ROOT / 'backend' / 'app' / 'state'
EXECUTION_FILE = STATE_DIR / 'execution_state.json'
TRUTH_FILE = STATE_DIR / 'live_broker_truth_state.json'
SYNC_FILE = STATE_DIR / 'real_position_fill_broker_sync_state.json'


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
    return _read_json(EXECUTION_FILE, {'mode': 'paper', 'safe_mode': True, 'active_broker': 'paper', 'fills': [], 'orders': [], 'positions': []})


def _load_truth() -> Dict[str, Any]:
    return _read_json(TRUTH_FILE, {'selected_broker': 'paper', 'live_path_armed': False})


def _load_sync() -> Dict[str, Any]:
    return _read_json(SYNC_FILE, {
        'authority_mode': 'execution-ledger',
        'last_sync_at': None,
        'last_reconcile_at': None,
        'sync_status': 'idle',
        'broker_connected': False,
        'drift_detected': False,
        'drift_reason': None,
        'positions': [],
        'fills': [],
        'latest_snapshot_source': None,
    })


def _save_sync(data: Dict[str, Any]) -> Dict[str, Any]:
    return _write_json(SYNC_FILE, data)


def _normalize_fills(execution: Dict[str, Any]) -> List[Dict[str, Any]]:
    fills = execution.get('fills') or execution.get('recent_fills') or []
    if isinstance(fills, dict):
        fills = [fills]
    if not isinstance(fills, list):
        return []
    out = []
    for idx, fill in enumerate(fills[-25:]):
        if not isinstance(fill, dict):
            continue
        out.append({
            'fill_id': fill.get('fill_id') or fill.get('id') or f'fill-{idx}',
            'symbol': fill.get('symbol') or fill.get('asset') or 'UNKNOWN',
            'side': str(fill.get('side') or fill.get('action') or 'BUY').upper(),
            'qty': float(fill.get('qty') or fill.get('quantity') or 0),
            'price': float(fill.get('price') or fill.get('avg_price') or 0),
            'status': fill.get('status') or 'FILLED',
            'timestamp': fill.get('timestamp') or fill.get('filled_at') or int(time.time()),
            'source': fill.get('source') or execution.get('active_broker') or 'paper',
        })
    return out


def _derive_positions(execution: Dict[str, Any], fills: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    positions = execution.get('positions')
    if isinstance(positions, list) and positions:
        norm = []
        for pos in positions[:25]:
            if not isinstance(pos, dict):
                continue
            qty = float(pos.get('qty') or pos.get('quantity') or 0)
            avg = float(pos.get('avg_price') or pos.get('average_price') or pos.get('cost_basis') or 0)
            norm.append({
                'symbol': pos.get('symbol') or pos.get('asset') or 'UNKNOWN',
                'qty': qty,
                'avg_price': avg,
                'market_value': float(pos.get('market_value') or qty * avg),
                'source': pos.get('source') or execution.get('active_broker') or 'paper',
            })
        if norm:
            return norm
    book = {}
    cost = {}
    for fill in fills:
        sym = fill['symbol']
        signed_qty = fill['qty'] if fill['side'] == 'BUY' else -fill['qty']
        book[sym] = book.get(sym, 0.0) + signed_qty
        if fill['side'] == 'BUY':
            cost[sym] = cost.get(sym, 0.0) + (fill['qty'] * fill['price'])
    derived = []
    for sym, qty in book.items():
        if abs(qty) < 1e-9:
            continue
        avg = (cost.get(sym, 0.0) / qty) if qty > 0 else 0.0
        derived.append({
            'symbol': sym,
            'qty': round(qty, 8),
            'avg_price': round(avg, 8),
            'market_value': round(qty * avg, 8),
            'source': execution.get('active_broker') or 'paper',
        })
    return derived


def _build_summary() -> Dict[str, Any]:
    execution = _load_execution()
    truth = _load_truth()
    sync = _load_sync()
    fills = _normalize_fills(execution)
    positions = sync.get('positions') or _derive_positions(execution, fills)
    selected_broker = truth.get('selected_broker', execution.get('active_broker', 'paper'))
    broker_connected = selected_broker == 'paper' or bool(truth.get('live_path_armed', False))
    drift_detected = bool(sync.get('drift_detected', False))
    blockers = []
    if execution.get('safe_mode', True):
        blockers.append('safe mode enabled')
    if execution.get('mode') != 'live':
        blockers.append('execution mode is not live')
    if selected_broker == 'paper':
        blockers.append('selected broker is paper')
    if not truth.get('live_path_armed', False):
        blockers.append('live path not armed')
    if drift_detected:
        blockers.append(sync.get('drift_reason') or 'position drift detected')
    synced = bool(sync.get('last_sync_at')) and not drift_detected
    return {
        'status': 'ok',
        'mission': 'QNT-REAL01C',
        'authority_mode': sync.get('authority_mode', 'execution-ledger'),
        'selected_broker': selected_broker,
        'broker_connected': broker_connected,
        'execution_mode': execution.get('mode', 'paper'),
        'safe_mode': bool(execution.get('safe_mode', True)),
        'live_path_armed': bool(truth.get('live_path_armed', False)),
        'sync_status': sync.get('sync_status', 'idle'),
        'last_sync_at': sync.get('last_sync_at'),
        'last_reconcile_at': sync.get('last_reconcile_at'),
        'drift_detected': drift_detected,
        'drift_reason': sync.get('drift_reason'),
        'synced': synced,
        'positions': positions,
        'position_count': len(positions),
        'fills': fills[-10:],
        'fill_count': len(fills),
        'blockers': blockers,
        'generated_at': int(time.time()),
    }


@router.get('/health')
def broker_sync_health() -> Dict[str, Any]:
    summary = _build_summary()
    return {
        'status': 'ok',
        'mission': summary['mission'],
        'selected_broker': summary['selected_broker'],
        'synced': summary['synced'],
        'position_count': summary['position_count'],
        'fill_count': summary['fill_count'],
        'blockers': summary['blockers'],
    }


@router.get('/summary')
def broker_sync_summary() -> Dict[str, Any]:
    return _build_summary()


@router.post('/sync-context')
def broker_sync_context() -> Dict[str, Any]:
    execution = _load_execution()
    sync = _load_sync()
    fills = _normalize_fills(execution)
    positions = _derive_positions(execution, fills)
    sync['positions'] = positions
    sync['fills'] = fills[-10:]
    sync['last_sync_at'] = int(time.time())
    sync['sync_status'] = 'synced'
    sync['latest_snapshot_source'] = execution.get('active_broker', 'paper')
    sync['broker_connected'] = execution.get('active_broker', 'paper') == 'paper' or True
    sync['drift_detected'] = False
    sync['drift_reason'] = None
    _save_sync(sync)
    return _build_summary()


@router.post('/ingest-position-snapshot')
def broker_sync_ingest_snapshot(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    positions = payload.get('positions')
    if not isinstance(positions, list):
        raise HTTPException(status_code=400, detail='positions must be a list')
    sync = _load_sync()
    sync['positions'] = positions[:25]
    sync['latest_snapshot_source'] = payload.get('source') or 'external-snapshot'
    sync['last_sync_at'] = int(time.time())
    sync['sync_status'] = 'snapshot-ingested'
    _save_sync(sync)
    return _build_summary()


@router.post('/reconcile')
def broker_sync_reconcile(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
    sync = _load_sync()
    expected = payload.get('expected_position_count')
    actual = len(sync.get('positions', []))
    sync['last_reconcile_at'] = int(time.time())
    sync['sync_status'] = 'reconciled'
    if expected is not None and int(expected) != actual:
        sync['drift_detected'] = True
        sync['drift_reason'] = f'expected {int(expected)} positions but found {actual}'
    else:
        sync['drift_detected'] = False
        sync['drift_reason'] = None
    _save_sync(sync)
    return _build_summary()


@router.post('/reset')
def broker_sync_reset() -> Dict[str, Any]:
    state = {
        'authority_mode': 'execution-ledger',
        'last_sync_at': None,
        'last_reconcile_at': None,
        'sync_status': 'idle',
        'broker_connected': False,
        'drift_detected': False,
        'drift_reason': None,
        'positions': [],
        'fills': [],
        'latest_snapshot_source': None,
    }
    _save_sync(state)
    return _build_summary()
