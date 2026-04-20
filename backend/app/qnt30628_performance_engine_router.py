from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
from datetime import datetime, timezone, timedelta
import hashlib
import json
import math
import time

router = APIRouter(tags=["performance-engine"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
PERF_DIR = ARTIFACTS_DIR / "performance_engine_v2"


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _identity():
    from backend.app import qnt30617_identity_registry_router as identity
    return identity


def _ledger():
    from backend.app import qnt30624_capital_ledger_router as ledger
    return ledger


def _pnl():
    from backend.app import qnt30586_pnl_ledger_router as pnl
    return pnl


def _execution():
    from backend.app import qnt30629_strategy_execution_router as execution
    return execution


def _safe(v: str) -> str:
    return hashlib.sha256((v or '').strip().lower().encode('utf-8')).hexdigest()[:24]


def _path(email: str) -> Path:
    PERF_DIR.mkdir(parents=True, exist_ok=True)
    return PERF_DIR / f'{_safe(email)}.json'


def _require_user():
    return _mu()._require_session()


def _now_ts() -> int:
    return int(time.time())


def _today_utc() -> datetime:
    return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)


def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {
            'email': email,
            'snapshots': [],
            'strategy_history': [],
            'investor_history': [],
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


def _round_money(v) -> float:
    return round(float(v or 0.0), 2)


def _round_pct(v) -> float:
    return round(float(v or 0.0), 4)


def _ts_to_day(ts: int) -> str:
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime('%Y-%m-%d')


def _stddev(values):
    values = [float(v) for v in values]
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(max(variance, 0.0))


def _compute_drawdown(points):
    peak = None
    max_dd = 0.0
    for p in points:
        nav = float(p.get('ending_nav') or 0.0)
        if peak is None or nav > peak:
            peak = nav
        if peak and peak > 0:
            dd = (peak - nav) / peak
            if dd > max_dd:
                max_dd = dd
    return _round_pct(max_dd * 100.0)


def _compute_sharpe(return_series):
    vals = [float(v) for v in return_series]
    if len(vals) < 2:
        return 0.0
    mean = sum(vals) / len(vals)
    sd = _stddev(vals)
    if sd <= 1e-12:
        return 0.0
    return round((mean / sd) * (252 ** 0.5), 4)


def _compute_return(begin_nav: float, end_nav: float, net_flows: float) -> float:
    base = float(begin_nav or 0.0)
    if abs(base) <= 1e-12:
        return 0.0
    return _round_pct(((float(end_nav or 0.0) - float(net_flows or 0.0) - base) / base) * 100.0)


def _positions_rollup(email: str):
    pnl_data = _pnl()._load(email)
    positions = pnl_data.get('positions', []) or []
    rollup = {}
    for pos in positions:
        sleeve_id = str(pos.get('sleeve_id') or '').strip()
        if not sleeve_id:
            continue
        item = rollup.setdefault(sleeve_id, {
            'sleeve_id': sleeve_id,
            'realized_pnl': 0.0,
            'unrealized_pnl': 0.0,
            'position_count': 0,
            'symbols': [],
        })
        item['realized_pnl'] = _round_money(item['realized_pnl'] + float(pos.get('realized_pnl') or 0.0))
        item['unrealized_pnl'] = _round_money(item['unrealized_pnl'] + float(pos.get('unrealized_pnl') or 0.0))
        item['position_count'] += 1
        sym = str(pos.get('symbol') or '').upper()
        if sym and sym not in item['symbols']:
            item['symbols'].append(sym)
    for item in rollup.values():
        item['total_pnl'] = _round_money(item['realized_pnl'] + item['unrealized_pnl'])
    return rollup


def _capital_and_allocations(email: str):
    ledger_data = _ledger()._load(email)
    accounts = ledger_data.get('accounts', []) or []
    entries = ledger_data.get('entries', []) or []
    allocations = ledger_data.get('allocations', []) or []
    total_nav = _round_money(sum(float(a.get('nav') or 0.0) for a in accounts))
    total_funded = _round_money(sum(float(a.get('funded_capital') or 0.0) for a in accounts))
    net_flows = _round_money(sum(float(e.get('amount') or 0.0) for e in entries))
    return ledger_data, accounts, entries, allocations, total_nav, total_funded, net_flows


def _strategy_breakdown(email: str):
    ledger_data, accounts, entries, allocations, total_nav, total_funded, net_flows = _capital_and_allocations(email)
    execution_rows = []
    try:
        if _execution()._has_live_execution(email):
            execution_data = _execution()._strategy_outcomes(email)
            execution_rows = execution_data.get('rows', []) or []
    except Exception:
        execution_rows = []
    if execution_rows:
        out = []
        for row in execution_rows:
            invested = _round_money(row.get('allocated_capital') or 0.0)
            pnl_amount = _round_money(row.get('gross_pnl') or 0.0)
            out.append({
                'strategy': row.get('strategy_name') or row.get('strategy_id'),
                'invested_capital': invested,
                'pnl_amount': pnl_amount,
                'allocations': int(row.get('investor_count') or 0),
                'sleeves': row.get('sleeves') or [],
                'position_count': int(row.get('trade_count') or 0),
                'symbols': row.get('symbols') or [],
                'return_pct': _round_pct(row.get('return_pct') or 0.0),
                'exposure_pct': _round_pct(row.get('exposure_pct') or 0.0),
                'volatility_pct': _round_pct(abs(pnl_amount) / invested * 35.0) if invested > 0 else 0.0,
            })
        out.sort(key=lambda x: x.get('invested_capital') or 0.0, reverse=True)
        return {
            'rows': out,
            'total_nav': total_nav,
            'total_funded_capital': total_funded,
            'net_flows': net_flows,
            'account_count': len(accounts),
            'allocation_count': len(allocations),
        }

    sleeve_rollup = _positions_rollup(email)
    by_strategy = {}
    sleeve_totals = {}
    for alloc in allocations:
        sleeve = str(alloc.get('sleeve') or 'main')
        sleeve_totals[sleeve] = _round_money(sleeve_totals.get(sleeve, 0.0) + float(alloc.get('amount') or 0.0))
    for alloc in allocations:
        strategy = str(alloc.get('strategy') or 'core')
        sleeve = str(alloc.get('sleeve') or 'main')
        amount = _round_money(alloc.get('amount') or 0.0)
        sleeve_total = _round_money(sleeve_totals.get(sleeve, 0.0))
        sleeve_pnl = _round_money((sleeve_rollup.get(sleeve) or {}).get('total_pnl') or 0.0)
        alloc_pnl = _round_money(sleeve_pnl * (amount / sleeve_total)) if sleeve_total > 0 else 0.0
        item = by_strategy.setdefault(strategy, {
            'strategy': strategy,
            'invested_capital': 0.0,
            'pnl_amount': 0.0,
            'allocations': 0,
            'sleeves': set(),
            'position_count': 0,
            'symbols': set(),
        })
        item['invested_capital'] = _round_money(item['invested_capital'] + amount)
        item['pnl_amount'] = _round_money(item['pnl_amount'] + alloc_pnl)
        item['allocations'] += 1
        item['sleeves'].add(sleeve)
        item['position_count'] += int((sleeve_rollup.get(sleeve) or {}).get('position_count') or 0)
        for sym in (sleeve_rollup.get(sleeve) or {}).get('symbols', []):
            item['symbols'].add(sym)
    out = []
    for item in by_strategy.values():
        begin_nav = item['invested_capital']
        end_nav = _round_money(begin_nav + item['pnl_amount'])
        item['return_pct'] = _compute_return(begin_nav, end_nav, 0.0) if begin_nav > 0 else 0.0
        item['exposure_pct'] = _round_pct((item['invested_capital'] / total_nav) * 100.0) if total_nav > 0 else 0.0
        item['volatility_pct'] = _round_pct(abs(item['pnl_amount']) / begin_nav * 35.0) if begin_nav > 0 else 0.0
        item['sleeves'] = sorted(item['sleeves'])
        item['symbols'] = sorted(item['symbols'])
        out.append(item)
    out.sort(key=lambda x: x.get('invested_capital') or 0.0, reverse=True)
    return {
        'rows': out,
        'total_nav': total_nav,
        'total_funded_capital': total_funded,
        'net_flows': net_flows,
        'account_count': len(accounts),
        'allocation_count': len(allocations),
    }


def _investor_performance(email: str):
    try:
        if _execution()._has_live_execution(email):
            return _execution()._investor_attribution(email)
    except Exception:
        pass
    identity_data = _identity()._load(email)
    ledger_data, accounts, entries, allocations, total_nav, total_funded, net_flows = _capital_and_allocations(email)
    by_identity = {str(i.get('investor_id') or ''): i for i in identity_data.get('investors', []) or []}
    sleeve_rollup = _positions_rollup(email)
    sleeve_totals = {}
    for alloc in allocations:
        sleeve = str(alloc.get('sleeve') or 'main')
        sleeve_totals[sleeve] = _round_money(sleeve_totals.get(sleeve, 0.0) + float(alloc.get('amount') or 0.0))
    rows = []
    for account in accounts:
        investor_id = str(account.get('investor_id') or '')
        investor_entries = [e for e in entries if e.get('investor_id') == investor_id]
        inflows = _round_money(sum(float(e.get('amount') or 0.0) for e in investor_entries if float(e.get('amount') or 0.0) > 0))
        outflows = _round_money(abs(sum(float(e.get('amount') or 0.0) for e in investor_entries if float(e.get('amount') or 0.0) < 0)))
        allocs = [a for a in allocations if a.get('investor_id') == investor_id]
        pnl_amount = 0.0
        strategy_mix = {}
        for alloc in allocs:
            sleeve = str(alloc.get('sleeve') or 'main')
            amount = _round_money(alloc.get('amount') or 0.0)
            sleeve_total = _round_money(sleeve_totals.get(sleeve, 0.0))
            sleeve_pnl = _round_money((sleeve_rollup.get(sleeve) or {}).get('total_pnl') or 0.0)
            alloc_pnl = _round_money(sleeve_pnl * (amount / sleeve_total)) if sleeve_total > 0 else 0.0
            pnl_amount = _round_money(pnl_amount + alloc_pnl)
            strategy = str(alloc.get('strategy') or 'core')
            strategy_mix[strategy] = _round_money(strategy_mix.get(strategy, 0.0) + amount)
        beginning_nav = _round_money(float(account.get('funded_capital') or 0.0) - pnl_amount)
        ending_nav = _round_money(float(account.get('funded_capital') or 0.0))
        return_pct = _compute_return(beginning_nav, ending_nav, inflows - outflows) if beginning_nav > 0 else 0.0
        rows.append({
            'investor_id': investor_id,
            'investor_name': (by_identity.get(investor_id) or {}).get('legal_name') or account.get('investor_name') or investor_id,
            'committed_capital': _round_money(account.get('committed_capital') or 0.0),
            'funded_capital': _round_money(account.get('funded_capital') or 0.0),
            'ending_nav': ending_nav,
            'pnl_amount': pnl_amount,
            'return_pct': return_pct,
            'ownership_pct': _round_pct(account.get('ownership_pct') or 0.0),
            'net_flows': _round_money(inflows - outflows),
            'allocation_count': len(allocs),
            'strategies': [{'strategy': k, 'amount': v} for k, v in sorted(strategy_mix.items())],
        })
    rows.sort(key=lambda x: x.get('ending_nav') or 0.0, reverse=True)
    return rows


def _live_summary(email: str):
    strategy = _strategy_breakdown(email)
    perf_store = _load(email)
    series = perf_store.get('snapshots', []) or []
    investor_rows = _investor_performance(email)
    strategy_rows = strategy['rows']
    total_pnl = _round_money(sum(float(r.get('pnl_amount') or 0.0) for r in strategy_rows))
    current_nav = _round_money(strategy['total_nav'] + total_pnl)
    return_series = [float(p.get('return_pct') or 0.0) / 100.0 for p in series[-60:]]
    summary = {
        'as_of': _now_ts(),
        'total_nav': strategy['total_nav'],
        'current_nav': current_nav,
        'net_pnl': total_pnl,
        'portfolio_return_pct': _compute_return(strategy['total_nav'], current_nav, 0.0) if strategy['total_nav'] > 0 else 0.0,
        'max_drawdown_pct': _compute_drawdown(series[-252:]),
        'sharpe_ratio': _compute_sharpe(return_series),
        'strategy_count': len(strategy_rows),
        'investor_count': len(investor_rows),
        'account_count': strategy['account_count'],
        'allocation_count': strategy['allocation_count'],
        'snapshots': len(series),
    }
    return {
        'summary': summary,
        'strategy_breakdown': strategy_rows,
        'investor_breakdown': investor_rows,
        'series': series[-120:],
    }


def _append_snapshot(data: dict, snapshot: dict, strategy_rows: list, investor_rows: list) -> dict:
    day = snapshot.get('date')
    series = data.setdefault('snapshots', [])
    replaced = False
    for idx, row in enumerate(series):
        if row.get('date') == day:
            series[idx] = snapshot
            replaced = True
            break
    if not replaced:
        series.append(snapshot)
    series.sort(key=lambda x: x.get('date'))
    data['snapshots'] = series[-730:]

    sh = data.setdefault('strategy_history', [])
    sh = [r for r in sh if r.get('date') != day]
    sh.extend([{'date': day, **row} for row in strategy_rows])
    sh.sort(key=lambda x: (x.get('date'), x.get('strategy')))
    data['strategy_history'] = sh[-5000:]

    ih = data.setdefault('investor_history', [])
    ih = [r for r in ih if r.get('date') != day]
    ih.extend([{'date': day, **row} for row in investor_rows])
    ih.sort(key=lambda x: (x.get('date'), x.get('investor_id')))
    data['investor_history'] = ih[-10000:]
    return data


@router.get('/api/performance-engine/summary')
def performance_engine_summary():
    session = _require_user()
    email = session.get('email')
    return {'status': 'ok', **_live_summary(email)}


@router.get('/api/performance-engine/strategies')
def performance_engine_strategies():
    session = _require_user()
    email = session.get('email')
    strategy = _strategy_breakdown(email)
    return {'status': 'ok', **strategy}


@router.get('/api/performance-engine/investors')
def performance_engine_investors():
    session = _require_user()
    email = session.get('email')
    return {'status': 'ok', 'rows': _investor_performance(email)}


@router.get('/api/performance-engine/timeseries')
def performance_engine_timeseries():
    session = _require_user()
    email = session.get('email')
    data = _load(email)
    live = _live_summary(email)
    return {
        'status': 'ok',
        'series': data.get('snapshots', [])[-120:],
        'current': live.get('summary'),
        'strategy_history_points': len(data.get('strategy_history', [])),
        'investor_history_points': len(data.get('investor_history', [])),
    }


@router.post('/api/performance-engine/snapshot')
def performance_engine_snapshot(payload: dict = Body(None)):
    session = _require_user()
    email = session.get('email')
    data = _load(email)
    live = _live_summary(email)
    override_date = str((payload or {}).get('date') or '').strip()
    if override_date:
        try:
            datetime.strptime(override_date, '%Y-%m-%d')
        except Exception as exc:
            raise HTTPException(status_code=400, detail='date must be YYYY-MM-DD') from exc
        date_label = override_date
    else:
        date_label = _today_utc().strftime('%Y-%m-%d')
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
    data = _append_snapshot(data, snapshot, live['strategy_breakdown'], live['investor_breakdown'])
    _save(email, data)
    return {'status': 'ok', 'snapshot': snapshot, 'series_points': len(data.get('snapshots', []))}


@router.post('/api/performance-engine/bootstrap-demo')
def performance_engine_bootstrap_demo(payload: dict = Body(None)):
    session = _require_user()
    email = session.get('email')
    months = int((payload or {}).get('months') or 6)
    months = max(3, min(months, 24))
    data = _load(email)
    live = _live_summary(email)
    current_nav = float(live['summary']['current_nav'] or 0.0)
    if current_nav <= 0:
        raise HTTPException(status_code=400, detail='bootstrap requires funded capital and/or pnl data')
    base_returns = [0.018, -0.006, 0.011, 0.024, -0.004, 0.016, 0.009, -0.003, 0.013, 0.007, 0.019, -0.002]
    today = _today_utc()
    start_idx = max(0, months)
    nav = current_nav
    staged = []
    for i in range(months - 1, -1, -1):
        r = base_returns[(months - 1 - i) % len(base_returns)]
        ending_nav = nav if i == 0 else nav / (1.0 + r)
        pnl_amount = ending_nav * r
        beginning_nav = ending_nav - pnl_amount
        date_label = (today - timedelta(days=i * 30)).strftime('%Y-%m-%d')
        staged.append({
            'date': date_label,
            'captured_at': _now_ts(),
            'beginning_nav': _round_money(beginning_nav),
            'ending_nav': _round_money(ending_nav),
            'net_flows': 0.0,
            'pnl_amount': _round_money(pnl_amount),
            'return_pct': _round_pct(r * 100.0),
            'strategy_count': live['summary']['strategy_count'],
            'investor_count': live['summary']['investor_count'],
            'source': 'demo_bootstrap',
        })
        nav = beginning_nav
    data['snapshots'] = staged
    data['strategy_history'] = []
    data['investor_history'] = []
    for snap in staged:
        ratio = (snap['ending_nav'] / current_nav) if current_nav > 0 else 1.0
        strategy_rows = []
        for row in live['strategy_breakdown']:
            cloned = dict(row)
            cloned['invested_capital'] = _round_money(float(row.get('invested_capital') or 0.0) * ratio)
            cloned['pnl_amount'] = _round_money(float(row.get('pnl_amount') or 0.0) * ratio)
            cloned['exposure_pct'] = _round_pct(row.get('exposure_pct') or 0.0)
            cloned['return_pct'] = _compute_return(cloned['invested_capital'], cloned['invested_capital'] + cloned['pnl_amount'], 0.0) if cloned['invested_capital'] > 0 else 0.0
            strategy_rows.append(cloned)
        investor_rows = []
        for row in live['investor_breakdown']:
            cloned = dict(row)
            cloned['funded_capital'] = _round_money(float(row.get('funded_capital') or 0.0) * ratio)
            cloned['ending_nav'] = _round_money(float(row.get('ending_nav') or 0.0) * ratio)
            cloned['pnl_amount'] = _round_money(float(row.get('pnl_amount') or 0.0) * ratio)
            investor_rows.append(cloned)
        data = _append_snapshot(data, snap, strategy_rows, investor_rows)
    _save(email, data)
    return {'status': 'ok', 'series_points': len(data.get('snapshots', [])), 'months': months}
