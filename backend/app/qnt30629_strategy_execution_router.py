from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["strategy-execution-engine"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
EXEC_DIR = ARTIFACTS_DIR / "strategy_execution_engine"


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _identity():
    from backend.app import qnt30617_identity_registry_router as identity
    return identity


def _ledger():
    from backend.app import qnt30624_capital_ledger_router as ledger
    return ledger


def _statement():
    from backend.app import qnt30627_statement_batch_router as statement
    return statement


def _safe(v: str) -> str:
    return hashlib.sha256((v or '').strip().lower().encode('utf-8')).hexdigest()[:24]


def _slug(v: str) -> str:
    raw = ''.join(ch.lower() if ch.isalnum() else '_' for ch in str(v or '').strip())
    while '__' in raw:
        raw = raw.replace('__', '_')
    return raw.strip('_') or 'core'


def _path(email: str) -> Path:
    EXEC_DIR.mkdir(parents=True, exist_ok=True)
    return EXEC_DIR / f'{_safe(email)}.json'


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


def _parse_period(period: str):
    raw = (period or '').strip()
    if len(raw) != 7 or raw[4] != '-':
        raise HTTPException(status_code=400, detail='period must be YYYY-MM')
    try:
        year = int(raw[:4])
        month = int(raw[5:7])
        start = datetime(year, month, 1, tzinfo=timezone.utc)
    except Exception as exc:
        raise HTTPException(status_code=400, detail='invalid period') from exc
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(year, month + 1, 1, tzinfo=timezone.utc)
    return raw, int(start.timestamp()), int(end.timestamp())


def _in_period(ts, period: str | None) -> bool:
    if not period:
        return True
    if ts in (None, ''):
        return False
    try:
        value = int(ts)
    except Exception:
        return False
    _p, start, end = _parse_period(period)
    return start <= value < end


def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {
            'email': email,
            'strategy_allocations': [],
            'trades': [],
            'strategy_registry': [],
            'history': [],
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


def _ledger_context(email: str):
    ledger_data = _ledger()._load(email)
    identity_data = _identity()._load(email)
    by_identity = {str(i.get('investor_id') or ''): i for i in (identity_data.get('investors', []) or [])}
    accounts = ledger_data.get('accounts', []) or []
    allocations = ledger_data.get('allocations', []) or []
    total_nav = _round_money(sum(float(a.get('nav') or 0.0) for a in accounts))
    return ledger_data, by_identity, accounts, allocations, total_nav


def _sync_allocations_from_ledger(email: str, data: dict | None = None) -> dict:
    if data is None:
        data = _load(email)
    ledger_data, by_identity, accounts, allocations, total_nav = _ledger_context(email)
    existing_manual = [row for row in (data.get('strategy_allocations', []) or []) if row.get('source') == 'manual']
    synced = []
    for row in allocations:
        investor_id = str(row.get('investor_id') or '').strip()
        if not investor_id:
            continue
        identity = by_identity.get(investor_id) or {}
        strategy_name = str(row.get('strategy') or 'Core Strategy')
        sleeve_id = str(row.get('sleeve') or 'main')
        synced.append({
            'allocation_map_id': f'map_{row.get("allocation_id") or _slug(investor_id + strategy_name + sleeve_id)}',
            'source_allocation_id': row.get('allocation_id'),
            'investor_id': investor_id,
            'investor_name': identity.get('legal_name') or row.get('investor_name') or investor_id,
            'strategy_id': _slug(strategy_name),
            'strategy_name': strategy_name,
            'sleeve_id': sleeve_id,
            'allocated_capital': _round_money(row.get('amount') or 0.0),
            'status': row.get('status') or 'active',
            'source': 'capital_ledger',
            'created_at': int(row.get('created_at') or _now_ts()),
        })
    data['strategy_allocations'] = synced + existing_manual
    _refresh_registry(data)
    data.setdefault('history', []).insert(0, {
        'event_id': f'hist_sync_{time.time_ns()}',
        'type': 'allocation_sync',
        'synced_rows': len(synced),
        'manual_rows': len(existing_manual),
        'timestamp': _now_ts(),
    })
    data['history'] = data.get('history', [])[:500]
    return _save(email, data)


def _refresh_registry(data: dict) -> dict:
    registry = {}
    for row in data.get('strategy_allocations', []) or []:
        strategy_id = str(row.get('strategy_id') or _slug(row.get('strategy_name') or 'core'))
        item = registry.setdefault(strategy_id, {
            'strategy_id': strategy_id,
            'strategy_name': row.get('strategy_name') or strategy_id,
            'sleeves': set(),
            'investor_ids': set(),
        })
        item['sleeves'].add(str(row.get('sleeve_id') or 'main'))
        item['investor_ids'].add(str(row.get('investor_id') or ''))
    for trade in data.get('trades', []) or []:
        strategy_id = str(trade.get('strategy_id') or _slug(trade.get('strategy_name') or 'core'))
        item = registry.setdefault(strategy_id, {
            'strategy_id': strategy_id,
            'strategy_name': trade.get('strategy_name') or strategy_id,
            'sleeves': set(),
            'investor_ids': set(),
        })
        item['sleeves'].add(str(trade.get('sleeve_id') or 'main'))
    data['strategy_registry'] = sorted([
        {
            'strategy_id': sid,
            'strategy_name': payload['strategy_name'],
            'sleeve_count': len(payload['sleeves']),
            'investor_count': len([x for x in payload['investor_ids'] if x]),
            'sleeves': sorted(payload['sleeves']),
        }
        for sid, payload in registry.items()
    ], key=lambda x: x.get('strategy_name') or x.get('strategy_id'))
    return data


def _trade_pnl(side: str, qty: float, entry_price: float, exit_price: float | None = None, mark_price: float | None = None, pnl: float | None = None):
    if pnl not in (None, ''):
        realized = _round_money(pnl)
        return realized, 0.0, _round_money(realized)
    direction = 1.0 if str(side or '').lower() in {'buy', 'long'} else -1.0
    basis = float(entry_price or 0.0)
    if basis <= 0 or float(qty or 0.0) <= 0:
        return 0.0, 0.0, 0.0
    if exit_price not in (None, '') and float(exit_price or 0.0) > 0:
        realized = _round_money((float(exit_price) - basis) * float(qty) * direction)
        return realized, 0.0, realized
    if mark_price not in (None, '') and float(mark_price or 0.0) > 0:
        unrealized = _round_money((float(mark_price) - basis) * float(qty) * direction)
        return 0.0, unrealized, unrealized
    return 0.0, 0.0, 0.0


def _normalize_trade(payload: dict) -> dict:
    strategy_name = str(payload.get('strategy_name') or payload.get('strategy_id') or 'Core Strategy')
    strategy_id = str(payload.get('strategy_id') or _slug(strategy_name))
    sleeve_id = str(payload.get('sleeve_id') or payload.get('sleeve') or 'main')
    symbol = str(payload.get('symbol') or '').upper().strip()
    side = str(payload.get('side') or 'buy').lower().strip()
    qty = _round_qty(payload.get('qty') or payload.get('quantity') or 0.0)
    entry_price = round(float(payload.get('entry_price') or payload.get('price') or 0.0), 6)
    exit_price = None if payload.get('exit_price') in (None, '') else round(float(payload.get('exit_price') or 0.0), 6)
    mark_price = None if payload.get('mark_price') in (None, '') else round(float(payload.get('mark_price') or 0.0), 6)
    status = str(payload.get('status') or ('closed' if exit_price not in (None, '') else 'open')).lower().strip()
    if not symbol or qty <= 0 or entry_price <= 0 or side not in {'buy', 'sell', 'long', 'short'}:
        raise HTTPException(status_code=400, detail='strategy, sleeve, symbol, side, qty, entry_price required')
    realized_pnl, unrealized_pnl, gross_pnl = _trade_pnl(side, qty, entry_price, exit_price, mark_price, payload.get('pnl'))
    executed_at = int(payload.get('executed_at') or _now_ts())
    return {
        'trade_id': f'trd_{time.time_ns()}',
        'strategy_id': strategy_id,
        'strategy_name': strategy_name,
        'sleeve_id': sleeve_id,
        'symbol': symbol,
        'side': 'buy' if side in {'buy', 'long'} else 'sell',
        'qty': qty,
        'entry_price': entry_price,
        'exit_price': exit_price,
        'mark_price': mark_price,
        'status': status,
        'notional': _round_money(qty * entry_price),
        'realized_pnl': realized_pnl,
        'unrealized_pnl': unrealized_pnl,
        'gross_pnl': gross_pnl,
        'outcome': 'win' if gross_pnl > 0 else ('loss' if gross_pnl < 0 else 'flat'),
        'executed_at': executed_at,
        'created_at': _now_ts(),
    }


def _filtered_trades(data: dict, period: str | None = None) -> list:
    trades = data.get('trades', []) or []
    rows = [row for row in trades if _in_period(row.get('executed_at'), period)]
    rows.sort(key=lambda x: int(x.get('executed_at') or 0), reverse=True)
    return rows


def _has_live_execution(email: str) -> bool:
    data = _load(email)
    if data.get('trades'):
        return True
    return bool(data.get('strategy_allocations'))


def _strategy_outcomes(email: str, period: str | None = None) -> dict:
    data = _load(email)
    if not data.get('strategy_allocations'):
        data = _sync_allocations_from_ledger(email, data)
    ledger_data, by_identity, accounts, allocations, total_nav = _ledger_context(email)
    trades = _filtered_trades(data, period)
    alloc_rows = data.get('strategy_allocations', []) or []
    grouped = {}

    for alloc in alloc_rows:
        strategy_id = str(alloc.get('strategy_id') or _slug(alloc.get('strategy_name') or 'core'))
        item = grouped.setdefault(strategy_id, {
            'strategy_id': strategy_id,
            'strategy_name': alloc.get('strategy_name') or strategy_id,
            'allocated_capital': 0.0,
            'deployed_notional': 0.0,
            'gross_pnl': 0.0,
            'realized_pnl': 0.0,
            'unrealized_pnl': 0.0,
            'trade_count': 0,
            'winning_trades': 0,
            'investor_ids': set(),
            'sleeves': set(),
            'symbols': set(),
            'last_trade_at': None,
        })
        item['allocated_capital'] = _round_money(item['allocated_capital'] + float(alloc.get('allocated_capital') or 0.0))
        item['investor_ids'].add(str(alloc.get('investor_id') or ''))
        item['sleeves'].add(str(alloc.get('sleeve_id') or 'main'))

    for trade in trades:
        strategy_id = str(trade.get('strategy_id') or _slug(trade.get('strategy_name') or 'core'))
        item = grouped.setdefault(strategy_id, {
            'strategy_id': strategy_id,
            'strategy_name': trade.get('strategy_name') or strategy_id,
            'allocated_capital': 0.0,
            'deployed_notional': 0.0,
            'gross_pnl': 0.0,
            'realized_pnl': 0.0,
            'unrealized_pnl': 0.0,
            'trade_count': 0,
            'winning_trades': 0,
            'investor_ids': set(),
            'sleeves': set(),
            'symbols': set(),
            'last_trade_at': None,
        })
        item['deployed_notional'] = _round_money(item['deployed_notional'] + float(trade.get('notional') or 0.0))
        item['gross_pnl'] = _round_money(item['gross_pnl'] + float(trade.get('gross_pnl') or 0.0))
        item['realized_pnl'] = _round_money(item['realized_pnl'] + float(trade.get('realized_pnl') or 0.0))
        item['unrealized_pnl'] = _round_money(item['unrealized_pnl'] + float(trade.get('unrealized_pnl') or 0.0))
        item['trade_count'] += 1
        if float(trade.get('gross_pnl') or 0.0) > 0:
            item['winning_trades'] += 1
        item['sleeves'].add(str(trade.get('sleeve_id') or 'main'))
        sym = str(trade.get('symbol') or '').upper()
        if sym:
            item['symbols'].add(sym)
        last_trade_at = int(trade.get('executed_at') or 0)
        if not item['last_trade_at'] or last_trade_at > item['last_trade_at']:
            item['last_trade_at'] = last_trade_at

    rows = []
    for row in grouped.values():
        allocated_capital = _round_money(row['allocated_capital'])
        gross_pnl = _round_money(row['gross_pnl'])
        rows.append({
            'strategy_id': row['strategy_id'],
            'strategy_name': row['strategy_name'],
            'allocated_capital': allocated_capital,
            'deployed_notional': _round_money(row['deployed_notional']),
            'gross_pnl': gross_pnl,
            'realized_pnl': _round_money(row['realized_pnl']),
            'unrealized_pnl': _round_money(row['unrealized_pnl']),
            'return_pct': _round_pct((gross_pnl / allocated_capital) * 100.0) if allocated_capital > 0 else 0.0,
            'trade_count': row['trade_count'],
            'win_rate_pct': _round_pct((row['winning_trades'] / row['trade_count']) * 100.0) if row['trade_count'] > 0 else 0.0,
            'investor_count': len([x for x in row['investor_ids'] if x]),
            'sleeve_count': len(row['sleeves']),
            'sleeves': sorted(row['sleeves']),
            'symbols': sorted(row['symbols']),
            'last_trade_at': row['last_trade_at'],
            'exposure_pct': _round_pct((allocated_capital / total_nav) * 100.0) if total_nav > 0 else 0.0,
        })
    rows.sort(key=lambda x: x.get('allocated_capital') or 0.0, reverse=True)
    return {
        'rows': rows,
        'trade_count': len(trades),
        'strategy_count': len(rows),
        'allocation_count': len(alloc_rows),
        'account_count': len(accounts),
        'total_nav': total_nav,
        'total_allocated_capital': _round_money(sum(float(r.get('allocated_capital') or 0.0) for r in rows)),
        'total_deployed_notional': _round_money(sum(float(r.get('deployed_notional') or 0.0) for r in rows)),
        'total_pnl': _round_money(sum(float(r.get('gross_pnl') or 0.0) for r in rows)),
    }


def _investor_strategy_attribution(email: str, period: str | None = None) -> list:
    data = _load(email)
    if not data.get('strategy_allocations'):
        data = _sync_allocations_from_ledger(email, data)
    strategy_outcomes = _strategy_outcomes(email, period)
    by_strategy = {r.get('strategy_id'): r for r in strategy_outcomes.get('rows', [])}
    alloc_rows = data.get('strategy_allocations', []) or []
    totals_by_strategy = {}
    for alloc in alloc_rows:
        sid = str(alloc.get('strategy_id') or _slug(alloc.get('strategy_name') or 'core'))
        totals_by_strategy[sid] = _round_money(totals_by_strategy.get(sid, 0.0) + float(alloc.get('allocated_capital') or 0.0))

    detailed = []
    for alloc in alloc_rows:
        sid = str(alloc.get('strategy_id') or _slug(alloc.get('strategy_name') or 'core'))
        total_strategy_capital = _round_money(totals_by_strategy.get(sid, 0.0))
        strategy_row = by_strategy.get(sid) or {}
        allocated_capital = _round_money(alloc.get('allocated_capital') or 0.0)
        ownership = (allocated_capital / total_strategy_capital) if total_strategy_capital > 0 else 0.0
        pnl_amount = _round_money(float(strategy_row.get('gross_pnl') or 0.0) * ownership)
        detailed.append({
            'allocation_map_id': alloc.get('allocation_map_id'),
            'investor_id': alloc.get('investor_id'),
            'investor_name': alloc.get('investor_name'),
            'strategy_id': sid,
            'strategy_name': alloc.get('strategy_name') or strategy_row.get('strategy_name') or sid,
            'sleeve': alloc.get('sleeve_id') or 'main',
            'amount': allocated_capital,
            'status': alloc.get('status') or 'active',
            'strategy_total_capital': total_strategy_capital,
            'investor_share_ratio': round(ownership, 8),
            'pnl_amount': pnl_amount,
            'return_pct': _round_pct((pnl_amount / allocated_capital) * 100.0) if allocated_capital > 0 else 0.0,
            'data_quality': 'live_trade_attribution' if strategy_row.get('trade_count') else 'allocation_only',
            'trade_count': int(strategy_row.get('trade_count') or 0),
            'created_at': alloc.get('created_at'),
        })
    detailed.sort(key=lambda x: ((x.get('investor_name') or ''), -(x.get('amount') or 0.0), (x.get('strategy_name') or '')))
    return detailed


def _investor_attribution(email: str, period: str | None = None) -> list:
    ledger_data, by_identity, accounts, allocations, total_nav = _ledger_context(email)
    detailed = _investor_strategy_attribution(email, period)
    by_investor = {}
    for account in accounts:
        investor_id = str(account.get('investor_id') or '')
        identity = by_identity.get(investor_id) or {}
        by_investor[investor_id] = {
            'investor_id': investor_id,
            'investor_name': identity.get('legal_name') or account.get('investor_name') or investor_id,
            'committed_capital': _round_money(account.get('committed_capital') or 0.0),
            'funded_capital': _round_money(account.get('funded_capital') or 0.0),
            'ending_nav': _round_money(account.get('nav') or 0.0),
            'pnl_amount': 0.0,
            'return_pct': 0.0,
            'ownership_pct': _round_pct(account.get('ownership_pct') or 0.0),
            'net_flows': _round_money(account.get('funded_capital') or 0.0),
            'allocation_count': 0,
            'strategies': [],
        }
    for row in detailed:
        investor_id = str(row.get('investor_id') or '')
        item = by_investor.setdefault(investor_id, {
            'investor_id': investor_id,
            'investor_name': row.get('investor_name') or investor_id,
            'committed_capital': 0.0,
            'funded_capital': 0.0,
            'ending_nav': 0.0,
            'pnl_amount': 0.0,
            'return_pct': 0.0,
            'ownership_pct': 0.0,
            'net_flows': 0.0,
            'allocation_count': 0,
            'strategies': [],
        })
        item['pnl_amount'] = _round_money(item['pnl_amount'] + float(row.get('pnl_amount') or 0.0))
        item['allocation_count'] += 1
        item['strategies'].append({
            'strategy': row.get('strategy_name') or row.get('strategy_id'),
            'amount': _round_money(row.get('amount') or 0.0),
            'pnl_amount': _round_money(row.get('pnl_amount') or 0.0),
        })
    rows = []
    for item in by_investor.values():
        funded = _round_money(item.get('funded_capital') or 0.0)
        ending_nav = _round_money(float(item.get('ending_nav') or funded) + float(item.get('pnl_amount') or 0.0))
        item['ending_nav'] = ending_nav
        item['return_pct'] = _round_pct((float(item.get('pnl_amount') or 0.0) / funded) * 100.0) if funded > 0 else 0.0
        item['strategies'].sort(key=lambda x: x.get('amount') or 0.0, reverse=True)
        rows.append(item)
    rows.sort(key=lambda x: x.get('ending_nav') or 0.0, reverse=True)
    return rows


def _summary(email: str, period: str | None = None) -> dict:
    strategy = _strategy_outcomes(email, period)
    investor_rows = _investor_attribution(email, period)
    trades = _filtered_trades(_load(email), period)
    positive = sum(1 for row in strategy.get('rows', []) if float(row.get('gross_pnl') or 0.0) > 0)
    return {
        'period': period or 'all_time',
        'as_of': _now_ts(),
        'strategy_count': strategy.get('strategy_count', 0),
        'trade_count': strategy.get('trade_count', 0),
        'allocation_count': strategy.get('allocation_count', 0),
        'investor_count': len(investor_rows),
        'total_nav': strategy.get('total_nav', 0.0),
        'total_allocated_capital': strategy.get('total_allocated_capital', 0.0),
        'total_deployed_notional': strategy.get('total_deployed_notional', 0.0),
        'total_pnl': strategy.get('total_pnl', 0.0),
        'portfolio_return_pct': _round_pct((float(strategy.get('total_pnl') or 0.0) / float(strategy.get('total_allocated_capital') or 1.0)) * 100.0) if float(strategy.get('total_allocated_capital') or 0.0) > 0 else 0.0,
        'profitable_strategy_count': positive,
        'last_trade_at': max([int(t.get('executed_at') or 0) for t in trades], default=None),
    }


def _bootstrap_demo(email: str, period: str | None = None) -> dict:
    use_period = period or _current_period()
    _statement()._seed_demo(email, use_period)
    data = _load(email)
    data['strategy_allocations'] = []
    data['trades'] = []
    data['strategy_registry'] = []
    data['history'] = []
    data = _sync_allocations_from_ledger(email, data)

    templates = {
        'alpha_core': [
            {'symbol': 'SPY', 'side': 'buy', 'qty': 450.0, 'entry_price': 520.0, 'exit_price': 560.0, 'status': 'closed'},
            {'symbol': 'QQQ', 'side': 'buy', 'qty': 280.0, 'entry_price': 430.0, 'mark_price': 522.857143, 'status': 'open'},
            {'symbol': 'IWM', 'side': 'buy', 'qty': 500.0, 'entry_price': 200.0, 'exit_price': 192.0, 'status': 'closed'},
        ],
        'macro_fx': [
            {'symbol': 'DX1', 'side': 'buy', 'qty': 4000.0, 'entry_price': 105.0, 'exit_price': 108.0, 'status': 'closed'},
            {'symbol': '6E1', 'side': 'sell', 'qty': 5000.0, 'entry_price': 1.0820, 'mark_price': 1.0796, 'status': 'open'},
            {'symbol': '6J1', 'side': 'buy', 'qty': 3000.0, 'entry_price': 0.0069, 'exit_price': 0.0059, 'status': 'closed'},
        ],
        'credit_income': [
            {'symbol': 'LQD', 'side': 'buy', 'qty': 3000.0, 'entry_price': 108.0, 'exit_price': 110.0, 'status': 'closed'},
            {'symbol': 'HYG', 'side': 'buy', 'qty': 1500.0, 'entry_price': 76.0, 'mark_price': 79.666667, 'status': 'open'},
            {'symbol': 'SJNK', 'side': 'buy', 'qty': 1000.0, 'entry_price': 25.0, 'exit_price': 23.5, 'status': 'closed'},
        ],
        'treasury_arb': [
            {'symbol': 'IEF', 'side': 'buy', 'qty': 1000.0, 'entry_price': 94.0, 'exit_price': 97.0, 'status': 'closed'},
            {'symbol': 'SHY', 'side': 'buy', 'qty': 1000.0, 'entry_price': 81.0, 'mark_price': 83.5, 'status': 'open'},
            {'symbol': 'TLT', 'side': 'sell', 'qty': 100.0, 'entry_price': 95.0, 'exit_price': 105.0, 'status': 'closed'},
        ],
    }

    seen = set()
    for alloc in data.get('strategy_allocations', []):
        sleeve_id = str(alloc.get('sleeve_id') or 'main')
        key = (alloc.get('strategy_id'), sleeve_id)
        if key in seen:
            continue
        seen.add(key)
        strategy_name = alloc.get('strategy_name') or alloc.get('strategy_id')
        for payload in templates.get(sleeve_id, [
            {'symbol': 'SPY', 'side': 'buy', 'qty': 100.0, 'entry_price': 500.0, 'exit_price': 510.0, 'status': 'closed'}
        ]):
            trade = _normalize_trade({
                **payload,
                'strategy_id': alloc.get('strategy_id'),
                'strategy_name': strategy_name,
                'sleeve_id': sleeve_id,
            })
            data.setdefault('trades', []).append(trade)
    _refresh_registry(data)
    data.setdefault('history', []).insert(0, {
        'event_id': f'hist_bootstrap_{time.time_ns()}',
        'type': 'bootstrap_demo',
        'period': use_period,
        'trade_count': len(data.get('trades', [])),
        'allocation_count': len(data.get('strategy_allocations', [])),
        'timestamp': _now_ts(),
    })
    data['history'] = data.get('history', [])[:500]
    _save(email, data)
    return {
        'period': use_period,
        'trade_count': len(data.get('trades', [])),
        'allocation_count': len(data.get('strategy_allocations', [])),
        'strategy_count': len(data.get('strategy_registry', [])),
    }


@router.get('/api/strategy-execution')
def strategy_execution_store():
    session = _require_user()
    return _load(session.get('email'))


@router.get('/api/strategy-execution/summary')
def strategy_execution_summary(period: str | None = None):
    session = _require_user()
    email = session.get('email')
    use_period = str(period).strip() if period else None
    if use_period:
        _parse_period(use_period)
    return {
        'status': 'ok',
        'summary': _summary(email, use_period),
        'strategy_outcomes': _strategy_outcomes(email, use_period).get('rows', []),
        'investor_attribution': _investor_attribution(email, use_period),
        'trade_tape': _filtered_trades(_load(email), use_period)[:200],
        'registry': _load(email).get('strategy_registry', []),
    }


@router.get('/api/strategy-execution/strategies')
def strategy_execution_strategies(period: str | None = None):
    session = _require_user()
    email = session.get('email')
    use_period = str(period).strip() if period else None
    if use_period:
        _parse_period(use_period)
    return {'status': 'ok', **_strategy_outcomes(email, use_period)}


@router.get('/api/strategy-execution/investors')
def strategy_execution_investors(period: str | None = None):
    session = _require_user()
    email = session.get('email')
    use_period = str(period).strip() if period else None
    if use_period:
        _parse_period(use_period)
    return {
        'status': 'ok',
        'rows': _investor_attribution(email, use_period),
        'strategy_rows': _investor_strategy_attribution(email, use_period),
    }


@router.get('/api/strategy-execution/trades')
def strategy_execution_trades(period: str | None = None):
    session = _require_user()
    email = session.get('email')
    use_period = str(period).strip() if period else None
    if use_period:
        _parse_period(use_period)
    data = _load(email)
    return {'status': 'ok', 'trades': _filtered_trades(data, use_period), 'count': len(_filtered_trades(data, use_period))}


@router.post('/api/strategy-execution/sync')
def strategy_execution_sync(payload: dict = Body(None)):
    session = _require_user()
    email = session.get('email')
    data = _sync_allocations_from_ledger(email)
    return {
        'status': 'synced',
        'allocation_count': len(data.get('strategy_allocations', [])),
        'strategy_count': len(data.get('strategy_registry', [])),
    }


@router.post('/api/strategy-execution/allocation')
def strategy_execution_add_allocation(payload: dict = Body(...)):
    session = _require_user()
    email = session.get('email')
    investor_id = str(payload.get('investor_id') or '').strip()
    strategy_name = str(payload.get('strategy_name') or payload.get('strategy_id') or '').strip()
    if not investor_id or not strategy_name:
        raise HTTPException(status_code=400, detail='investor_id and strategy_name required')
    data = _load(email)
    _, by_identity, accounts, allocations, total_nav = _ledger_context(email)
    item = {
        'allocation_map_id': f'map_{time.time_ns()}',
        'source_allocation_id': None,
        'investor_id': investor_id,
        'investor_name': (by_identity.get(investor_id) or {}).get('legal_name') or investor_id,
        'strategy_id': str(payload.get('strategy_id') or _slug(strategy_name)),
        'strategy_name': strategy_name,
        'sleeve_id': str(payload.get('sleeve_id') or payload.get('sleeve') or 'main'),
        'allocated_capital': _round_money(payload.get('allocated_capital') or payload.get('amount') or 0.0),
        'status': str(payload.get('status') or 'active'),
        'source': 'manual',
        'created_at': _now_ts(),
    }
    if item['allocated_capital'] <= 0:
        raise HTTPException(status_code=400, detail='allocated_capital must be positive')
    data.setdefault('strategy_allocations', []).insert(0, item)
    _refresh_registry(data)
    data.setdefault('history', []).insert(0, {'event_id': f'hist_alloc_{time.time_ns()}', 'type': 'manual_allocation', 'allocation_map_id': item['allocation_map_id'], 'timestamp': _now_ts()})
    data['history'] = data.get('history', [])[:500]
    _save(email, data)
    return {'status': 'allocated', 'allocation': item}


@router.post('/api/strategy-execution/trade')
def strategy_execution_add_trade(payload: dict = Body(...)):
    session = _require_user()
    email = session.get('email')
    data = _load(email)
    if not data.get('strategy_allocations'):
        data = _sync_allocations_from_ledger(email, data)
    trade = _normalize_trade(payload)
    data.setdefault('trades', []).insert(0, trade)
    data['trades'] = data.get('trades', [])[:5000]
    _refresh_registry(data)
    data.setdefault('history', []).insert(0, {
        'event_id': f'hist_trade_{time.time_ns()}',
        'type': 'trade_recorded',
        'trade_id': trade['trade_id'],
        'strategy_id': trade['strategy_id'],
        'timestamp': _now_ts(),
    })
    data['history'] = data.get('history', [])[:500]
    _save(email, data)
    return {'status': 'recorded', 'trade': trade, 'summary': _summary(email)}


@router.post('/api/strategy-execution/bootstrap-demo')
def strategy_execution_bootstrap_demo(payload: dict = Body(None)):
    session = _require_user()
    email = session.get('email')
    period = str((payload or {}).get('period') or _current_period())
    _parse_period(period)
    demo = _bootstrap_demo(email, period)
    return {'status': 'seeded', 'demo': demo, 'summary': _summary(email, period)}
