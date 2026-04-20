from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["broker-integration-layer"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
BROKER_DIR = ARTIFACTS_DIR / "broker_integration_layer"

DEFAULT_SETTINGS = {
    "mode": "paper",
    "paper_slippage_bps": 8.0,
    "max_order_notional": 250000.0,
    "max_strategy_exposure_pct": 45.0,
    "kill_switch": False,
    "allow_live_execution": False,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _execution():
    from backend.app import qnt30629_strategy_execution_router as execution
    return execution


def _performance():
    from backend.app import qnt30628_performance_engine_router as performance
    return performance


def _statement():
    from backend.app import qnt30627_statement_batch_router as statement
    return statement


def _allocation():
    from backend.app import qnt30630_allocation_engine_router as allocation
    return allocation


def _safe(v: str) -> str:
    return hashlib.sha256((v or '').strip().lower().encode('utf-8')).hexdigest()[:24]


def _path(email: str) -> Path:
    BROKER_DIR.mkdir(parents=True, exist_ok=True)
    return BROKER_DIR / f'{_safe(email)}.json'


def _require_user():
    return _mu()._require_session()


def _now_ts() -> int:
    return int(time.time())


def _round_money(v) -> float:
    return round(float(v or 0.0), 2)


def _round_qty(v) -> float:
    return round(float(v or 0.0), 6)


def _round_pct(v) -> float:
    return round(float(v or 0.0), 4)


def _current_period() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m')


def _today_label() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%d')


def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {
            'email': email,
            'settings': dict(DEFAULT_SETTINGS),
            'orders': [],
            'fills': [],
            'positions': {},
            'audit_log': [],
            'created_at': _now_ts(),
            'updated_at': _now_ts(),
        }
        path.write_text(json.dumps(data, indent=2), encoding='utf-8')
        return data
    return json.loads(path.read_text(encoding='utf-8'))


def _save(email: str, data: dict) -> dict:
    data['updated_at'] = _now_ts()
    _path(email).write_text(json.dumps(data, indent=2), encoding='utf-8')
    return data


def _log(data: dict, event_type: str, payload: dict):
    data.setdefault('audit_log', []).insert(0, {
        'event_id': f'audit_{time.time_ns()}',
        'type': event_type,
        'timestamp': _now_ts(),
        **payload,
    })
    data['audit_log'] = data.get('audit_log', [])[:500]


def _order_status(order: dict, filled_qty: float) -> str:
    qty = float(order.get('qty') or 0.0)
    if qty <= 0:
        return 'rejected'
    if filled_qty >= qty:
        return 'filled'
    if filled_qty > 0:
        return 'partial_fill'
    return 'submitted'


def _position_key(strategy_id: str, symbol: str) -> str:
    return f'{strategy_id}::{symbol.upper()}'


def _strategy_exposure(data: dict, strategy_id: str) -> float:
    total = 0.0
    for pos in (data.get('positions') or {}).values():
        if pos.get('strategy_id') == strategy_id:
            total += float(pos.get('market_value') or 0.0)
    return _round_money(total)


def _validate_order(email: str, data: dict, order: dict) -> list:
    settings = data.get('settings') or {}
    if settings.get('kill_switch'):
        raise HTTPException(status_code=423, detail='broker kill switch is enabled')
    mode = str(settings.get('mode') or 'paper')
    if mode == 'live' and not settings.get('allow_live_execution'):
        raise HTTPException(status_code=403, detail='live execution is locked')
    side = str(order.get('side') or '').lower()
    if side not in {'buy', 'sell'}:
        raise HTTPException(status_code=400, detail='side must be buy or sell')
    qty = float(order.get('qty') or 0.0)
    px = float(order.get('price') or 0.0)
    if qty <= 0 or px <= 0:
        raise HTTPException(status_code=400, detail='qty and price must be positive')
    symbol = str(order.get('symbol') or '').upper().strip()
    strategy_id = str(order.get('strategy_id') or '').strip()
    if not symbol or not strategy_id:
        raise HTTPException(status_code=400, detail='strategy_id and symbol required')

    plan = _allocation()._build_plan(email)
    total_nav = float(plan.get('total_nav') or 0.0)
    notional = qty * px
    if notional > float(settings.get('max_order_notional') or DEFAULT_SETTINGS['max_order_notional']):
        raise HTTPException(status_code=400, detail='order notional exceeds execution limit')

    current_exposure = _strategy_exposure(data, strategy_id)
    max_pct = float(settings.get('max_strategy_exposure_pct') or DEFAULT_SETTINGS['max_strategy_exposure_pct'])
    if total_nav > 0 and ((current_exposure + notional) / total_nav) * 100.0 > max_pct + 0.0001:
        raise HTTPException(status_code=400, detail='strategy exposure limit breached')

    warnings = []
    for existing in data.get('orders', []) or []:
        if existing.get('status') in {'filled', 'partial_fill', 'submitted'} and existing.get('strategy_id') == strategy_id and existing.get('symbol') == symbol and existing.get('side') == side:
            if abs(float(existing.get('qty') or 0.0) - qty) < 1e-6 and abs(float(existing.get('price') or 0.0) - px) < 1e-6:
                warnings.append('duplicate order fingerprint detected')
                break
    return warnings


def _deterministic_fill_price(price: float, side: str, settings: dict) -> float:
    slip = float(settings.get('paper_slippage_bps') or DEFAULT_SETTINGS['paper_slippage_bps']) / 10000.0
    if str(side).lower() == 'buy':
        return round(price * (1.0 + slip), 6)
    return round(price * (1.0 - slip), 6)


def _sync_trade_pipeline(email: str, fill: dict, period: str | None = None) -> dict:
    execution = _execution()
    perf = _performance()
    statements = _statement()
    exec_data = execution._load(email)
    if not exec_data.get('strategy_allocations'):
        exec_data = execution._sync_allocations_from_ledger(email, exec_data)
    trade = execution._normalize_trade({
        'strategy_id': fill.get('strategy_id'),
        'strategy_name': fill.get('strategy_name'),
        'sleeve_id': fill.get('sleeve_id') or 'main',
        'symbol': fill.get('symbol'),
        'side': fill.get('side'),
        'qty': fill.get('filled_qty'),
        'entry_price': fill.get('fill_price'),
        'mark_price': fill.get('fill_price'),
        'status': 'open',
        'executed_at': fill.get('filled_at') or _now_ts(),
    })
    exec_data.setdefault('trades', []).insert(0, trade)
    exec_data['trades'] = exec_data.get('trades', [])[:5000]
    execution._refresh_registry(exec_data)
    exec_data.setdefault('history', []).insert(0, {
        'event_id': f'hist_broker_sync_{time.time_ns()}',
        'type': 'broker_fill_sync',
        'trade_id': trade['trade_id'],
        'timestamp': _now_ts(),
    })
    exec_data['history'] = exec_data.get('history', [])[:500]
    execution._save(email, exec_data)

    perf_data = perf._load(email)
    live = perf._live_summary(email)
    date_label = _today_label()
    summary = live['summary']
    snapshot = {
        'date': date_label,
        'captured_at': _now_ts(),
        'beginning_nav': summary['total_nav'],
        'ending_nav': summary['current_nav'],
        'net_flows': 0.0,
        'pnl_amount': summary['net_pnl'],
        'return_pct': summary['portfolio_return_pct'],
        'strategy_count': summary['strategy_count'],
        'investor_count': summary['investor_count'],
    }
    perf_data = perf._append_snapshot(perf_data, snapshot, live['strategy_breakdown'], live['investor_breakdown'])
    perf._save(email, perf_data)

    use_period = str(period or _current_period())
    stmt_data = statements._load(email)
    stmt_snapshot = statements._build_period_snapshot(email, use_period)
    stmt_data.setdefault('periods', {})[use_period] = stmt_snapshot
    stmt_data.setdefault('batch_runs', []).insert(0, {
        'batch_id': stmt_snapshot.get('batch_id'),
        'period': use_period,
        'generated_at': stmt_snapshot.get('generated_at'),
        'status': stmt_snapshot.get('status'),
        'statement_count': stmt_snapshot.get('summary', {}).get('statement_count', 0),
        'reconciliation_status': stmt_snapshot.get('reconciliation', {}).get('status'),
    })
    stmt_data['batch_runs'] = stmt_data.get('batch_runs', [])[:200]
    statements._save(email, stmt_data)
    return {'trade': trade, 'snapshot_date': date_label, 'statement_period': use_period}


def _update_position_book(data: dict, fill: dict) -> dict:
    key = _position_key(fill.get('strategy_id'), fill.get('symbol'))
    book = data.setdefault('positions', {})
    existing = book.get(key) or {
        'strategy_id': fill.get('strategy_id'),
        'strategy_name': fill.get('strategy_name'),
        'sleeve_id': fill.get('sleeve_id') or 'main',
        'symbol': fill.get('symbol'),
        'side': fill.get('side'),
        'qty': 0.0,
        'avg_price': 0.0,
        'market_value': 0.0,
        'fills': 0,
        'opened_at': fill.get('filled_at'),
        'updated_at': fill.get('filled_at'),
    }
    old_qty = float(existing.get('qty') or 0.0)
    old_avg = float(existing.get('avg_price') or 0.0)
    new_qty = old_qty + float(fill.get('filled_qty') or 0.0)
    if new_qty <= 0:
        new_qty = 0.0
        new_avg = 0.0
        market_value = 0.0
    else:
        new_avg = ((old_qty * old_avg) + (float(fill.get('filled_qty') or 0.0) * float(fill.get('fill_price') or 0.0))) / new_qty if old_qty > 0 else float(fill.get('fill_price') or 0.0)
        market_value = new_qty * float(fill.get('fill_price') or 0.0)
    existing.update({
        'qty': _round_qty(new_qty),
        'avg_price': round(new_avg, 6),
        'market_value': _round_money(market_value),
        'fills': int(existing.get('fills') or 0) + 1,
        'updated_at': fill.get('filled_at'),
        'side': fill.get('side'),
    })
    book[key] = existing
    return existing


def _submit_order(email: str, order_payload: dict, period: str | None = None) -> dict:
    data = _load(email)
    settings = data.get('settings') or {}
    side = str(order_payload.get('side') or 'buy').lower().strip()
    order = {
        'order_id': f'ord_{time.time_ns()}',
        'strategy_id': str(order_payload.get('strategy_id') or '').strip(),
        'strategy_name': str(order_payload.get('strategy_name') or order_payload.get('strategy_id') or '').strip(),
        'sleeve_id': str(order_payload.get('sleeve_id') or order_payload.get('sleeve') or 'main').strip(),
        'symbol': str(order_payload.get('symbol') or '').upper().strip(),
        'side': 'buy' if side in {'buy', 'long'} else 'sell',
        'qty': _round_qty(order_payload.get('qty') or order_payload.get('quantity') or 0.0),
        'price': round(float(order_payload.get('price') or 0.0), 6),
        'type': str(order_payload.get('type') or 'market').lower(),
        'mode': str(settings.get('mode') or 'paper'),
        'status': 'submitted',
        'warnings': [],
        'created_at': _now_ts(),
        'submitted_at': _now_ts(),
    }
    order['warnings'] = _validate_order(email, data, order)

    fill_qty = order['qty']
    fill_price = _deterministic_fill_price(order['price'], order['side'], settings)
    filled_notional = _round_money(fill_qty * fill_price)
    order['status'] = _order_status(order, fill_qty)
    order['filled_qty'] = fill_qty
    order['fill_price'] = fill_price
    order['filled_notional'] = filled_notional
    order['filled_at'] = _now_ts()

    fill = {
        'fill_id': f'fill_{time.time_ns()}',
        'order_id': order['order_id'],
        'strategy_id': order['strategy_id'],
        'strategy_name': order['strategy_name'],
        'sleeve_id': order['sleeve_id'],
        'symbol': order['symbol'],
        'side': order['side'],
        'filled_qty': fill_qty,
        'fill_price': fill_price,
        'filled_notional': filled_notional,
        'mode': order['mode'],
        'filled_at': order['filled_at'],
    }

    data.setdefault('orders', []).insert(0, order)
    data.setdefault('fills', []).insert(0, fill)
    data['orders'] = data.get('orders', [])[:2000]
    data['fills'] = data.get('fills', [])[:2000]
    position = _update_position_book(data, fill)
    pipeline = _sync_trade_pipeline(email, fill, period=period)
    _log(data, 'order_filled', {
        'order_id': order['order_id'],
        'fill_id': fill['fill_id'],
        'strategy_id': order['strategy_id'],
        'symbol': order['symbol'],
        'filled_notional': filled_notional,
        'warnings': order.get('warnings') or [],
    })
    _save(email, data)
    return {
        'order': order,
        'fill': fill,
        'position': position,
        'pipeline': pipeline,
    }


def _current_positions(email: str) -> list:
    data = _load(email)
    rows = list((data.get('positions') or {}).values())
    rows.sort(key=lambda x: float(x.get('market_value') or 0.0), reverse=True)
    return rows


def _summary(email: str) -> dict:
    data = _load(email)
    positions = _current_positions(email)
    performance = _performance()._live_summary(email)
    return {
        'as_of': _now_ts(),
        'mode': (data.get('settings') or {}).get('mode') or 'paper',
        'kill_switch': bool((data.get('settings') or {}).get('kill_switch')),
        'order_count': len(data.get('orders') or []),
        'fill_count': len(data.get('fills') or []),
        'position_count': len(positions),
        'gross_exposure': _round_money(sum(float(p.get('market_value') or 0.0) for p in positions)),
        'strategy_positions': len({p.get('strategy_id') for p in positions if p.get('strategy_id')}),
        'portfolio_return_pct': performance.get('summary', {}).get('portfolio_return_pct', 0.0),
        'net_pnl': performance.get('summary', {}).get('net_pnl', 0.0),
    }


def _apply_allocation_plan(email: str, plan: dict, period: str | None = None) -> dict:
    execution = _execution()
    outcomes = execution._strategy_outcomes(email).get('rows', [])
    current = {row.get('strategy_id'): row for row in outcomes}
    orders = []
    blocked = []
    for row in plan.get('strategies', []) or []:
        if row.get('status') != 'eligible':
            blocked.append({'strategy_id': row.get('strategy_id'), 'strategy_name': row.get('strategy_name'), 'reason': (row.get('blocked_reasons') or ['blocked'])[0]})
            continue
        delta = float(row.get('rebalance_delta') or 0.0)
        if delta <= 0:
            continue
        capital = float(row.get('target_capital') or 0.0)
        price = max(capital / 1000.0, 25.0)
        qty = max(delta / price, 1.0)
        sym = (row.get('symbols') or [row.get('strategy_id', 'QNT').upper()[:6]])[0]
        orders.append(_submit_order(email, {
            'strategy_id': row.get('strategy_id'),
            'strategy_name': row.get('strategy_name'),
            'sleeve_id': row.get('strategy_id'),
            'symbol': sym,
            'side': 'buy',
            'qty': qty,
            'price': price,
            'type': 'market',
        }, period=period))
    return {
        'executed_orders': len(orders),
        'blocked_strategies': blocked,
        'fills': [o['fill'] for o in orders],
        'orders': [o['order'] for o in orders],
    }


def _bootstrap_demo(email: str, period: str | None = None) -> dict:
    use_period = period or _current_period()
    _statement()._seed_demo(email, use_period)
    _execution()._bootstrap_demo(email, use_period)
    _performance()._load(email)
    data = _load(email)
    data['orders'] = []
    data['fills'] = []
    data['positions'] = {}
    data['audit_log'] = []
    _save(email, data)
    plan = _allocation()._build_plan(email, use_period)
    result = _apply_allocation_plan(email, plan, use_period)
    return {
        'period': use_period,
        'executed_orders': result['executed_orders'],
        'fill_count': len(result['fills']),
        'blocked_strategies': len(result['blocked_strategies']),
    }


@router.get('/api/broker-integration/summary')
def broker_integration_summary():
    session = _require_user()
    email = session.get('email')
    data = _load(email)
    return {
        'status': 'ok',
        'summary': _summary(email),
        'settings': data.get('settings') or {},
        'orders': (data.get('orders') or [])[:50],
        'fills': (data.get('fills') or [])[:50],
        'positions': _current_positions(email),
        'audit_log': (data.get('audit_log') or [])[:50],
    }


@router.get('/api/broker-integration/orders')
def broker_integration_orders():
    session = _require_user()
    email = session.get('email')
    data = _load(email)
    return {'status': 'ok', 'orders': data.get('orders') or [], 'fills': data.get('fills') or []}


@router.get('/api/broker-integration/positions')
def broker_integration_positions():
    session = _require_user()
    email = session.get('email')
    return {'status': 'ok', 'positions': _current_positions(email)}


@router.post('/api/broker-integration/settings')
def broker_integration_settings(payload: dict = Body(...)):
    session = _require_user()
    email = session.get('email')
    data = _load(email)
    settings = data.setdefault('settings', dict(DEFAULT_SETTINGS))
    if 'mode' in payload:
        mode = str(payload.get('mode') or 'paper').lower()
        if mode not in {'paper', 'live'}:
            raise HTTPException(status_code=400, detail='mode must be paper or live')
        if mode == 'live' and not settings.get('allow_live_execution') and not payload.get('allow_live_execution'):
            raise HTTPException(status_code=403, detail='live mode remains locked')
        settings['mode'] = mode
    for field in ['paper_slippage_bps', 'max_order_notional', 'max_strategy_exposure_pct']:
        if field in payload:
            settings[field] = float(payload.get(field) or settings.get(field) or DEFAULT_SETTINGS[field])
    for field in ['kill_switch', 'allow_live_execution']:
        if field in payload:
            settings[field] = bool(payload.get(field))
    _log(data, 'settings_updated', {'settings': settings})
    _save(email, data)
    return {'status': 'updated', 'settings': settings}


@router.post('/api/broker-integration/place-order')
def broker_integration_place_order(payload: dict = Body(...)):
    session = _require_user()
    email = session.get('email')
    period = str((payload or {}).get('period') or _current_period())
    result = _submit_order(email, payload, period=period)
    return {'status': 'filled', **result, 'summary': _summary(email)}


@router.post('/api/broker-integration/execute-plan')
def broker_integration_execute_plan(payload: dict = Body(None)):
    session = _require_user()
    email = session.get('email')
    period = str((payload or {}).get('period') or _current_period())
    plan = _allocation()._build_plan(email, period)
    result = _apply_allocation_plan(email, plan, period)
    return {'status': 'executed', 'plan': plan, **result, 'summary': _summary(email)}


@router.post('/api/broker-integration/bootstrap-demo')
def broker_integration_bootstrap_demo(payload: dict = Body(None)):
    session = _require_user()
    email = session.get('email')
    period = str((payload or {}).get('period') or _current_period())
    demo = _bootstrap_demo(email, period)
    return {'status': 'seeded', 'demo': demo, 'summary': _summary(email)}
