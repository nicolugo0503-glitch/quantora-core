from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["allocation-engine"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ALLOC_DIR = ARTIFACTS_DIR / "allocation_engine"

MAX_STRATEGY_WEIGHT = 0.40
CASH_RESERVE_FLOOR = 0.10
MAX_DRAWDOWN_PCT = 25.0
MAX_VOLATILITY_PCT = 35.0
MIN_TRADE_COUNT = 2
MIN_SCORE_TO_ALLOCATE = 20.0


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _ledger():
    from backend.app import qnt30624_capital_ledger_router as ledger
    return ledger


def _performance():
    from backend.app import qnt30628_performance_engine_router as performance
    return performance


def _execution():
    from backend.app import qnt30629_strategy_execution_router as execution
    return execution


def _statement():
    from backend.app import qnt30627_statement_batch_router as statement
    return statement


def _safe(v: str) -> str:
    return hashlib.sha256((v or '').strip().lower().encode('utf-8')).hexdigest()[:24]


def _path(email: str) -> Path:
    ALLOC_DIR.mkdir(parents=True, exist_ok=True)
    return ALLOC_DIR / f'{_safe(email)}.json'


def _require_user():
    return _mu()._require_session()


def _now_ts() -> int:
    return int(time.time())


def _current_period() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m')


def _round_money(v) -> float:
    return round(float(v or 0.0), 2)


def _round_pct(v) -> float:
    return round(float(v or 0.0), 4)


def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {
            'email': email,
            'policy': {
                'max_strategy_weight': MAX_STRATEGY_WEIGHT,
                'cash_reserve_floor': CASH_RESERVE_FLOOR,
                'max_drawdown_pct': MAX_DRAWDOWN_PCT,
                'max_volatility_pct': MAX_VOLATILITY_PCT,
                'min_trade_count': MIN_TRADE_COUNT,
                'min_score_to_allocate': MIN_SCORE_TO_ALLOCATE,
            },
            'decisions': [],
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


def _deployable_capital(email: str):
    ledger_data = _ledger()._load(email)
    accounts = ledger_data.get('accounts', []) or []
    total_nav = _round_money(sum(float(a.get('nav') or 0.0) for a in accounts))
    reserve = _round_money(total_nav * CASH_RESERVE_FLOOR)
    deployable = _round_money(max(total_nav - reserve, 0.0))
    return ledger_data, total_nav, reserve, deployable


def _latest_strategy_metrics(email: str):
    live = _performance()._live_summary(email)
    strategy_rows = live.get('strategy_breakdown', []) or []
    execution_rows = {row.get('strategy_id'): row for row in (_execution()._strategy_outcomes(email).get('rows', []) or [])}
    perf_store = _performance()._load(email)
    hist = perf_store.get('strategy_history', []) or []
    by_strategy = {}
    for row in hist:
        name = str(row.get('strategy') or row.get('strategy_name') or '').strip()
        if name:
            by_strategy.setdefault(name, []).append(row)
    metrics = []
    for row in strategy_rows:
        strategy_name = str(row.get('strategy') or row.get('strategy_name') or '').strip()
        strategy_id = None
        for sid, ex in execution_rows.items():
            if (ex.get('strategy_name') or '').strip() == strategy_name:
                strategy_id = sid
                break
        if strategy_id is None:
            strategy_id = (strategy_name or 'core').lower().replace(' ', '_')
        history = sorted(by_strategy.get(strategy_name, []), key=lambda x: x.get('date') or '')
        recent = history[-3:]
        trend = 0.0
        if len(recent) >= 2:
            trend = _round_pct(float(recent[-1].get('return_pct') or 0.0) - float(recent[0].get('return_pct') or 0.0))
        trade_count = int((execution_rows.get(strategy_id) or {}).get('trade_count') or row.get('position_count') or 0)
        metrics.append({
            'strategy_id': strategy_id,
            'strategy_name': strategy_name,
            'invested_capital': _round_money(row.get('invested_capital') or 0.0),
            'pnl_amount': _round_money(row.get('pnl_amount') or 0.0),
            'return_pct': _round_pct(row.get('return_pct') or 0.0),
            'exposure_pct': _round_pct(row.get('exposure_pct') or 0.0),
            'volatility_pct': _round_pct(row.get('volatility_pct') or 0.0),
            'trade_count': trade_count,
            'drawdown_proxy_pct': _round_pct(min(abs(float(row.get('pnl_amount') or 0.0)) / max(float(row.get('invested_capital') or 1.0), 1.0) * 100.0 * 0.8, 99.0)),
            'trend_pct': trend,
            'history_points': len(history),
            'symbols': row.get('symbols') or [],
        })
    return metrics, live


def _score_strategy(metric: dict, policy: dict) -> dict:
    reasons = []
    blocked_reasons = []
    return_score = max(min(float(metric.get('return_pct') or 0.0) * 2.2, 35.0), -35.0)
    sharpe_proxy = 0.0
    vol = float(metric.get('volatility_pct') or 0.0)
    ret = float(metric.get('return_pct') or 0.0)
    if vol > 0:
        sharpe_proxy = max(min((ret / vol) * 18.0, 25.0), -25.0)
    drawdown_penalty = -min(float(metric.get('drawdown_proxy_pct') or 0.0) * 0.7, 20.0)
    volatility_penalty = -min(max(vol - 12.0, 0.0) * 0.45, 12.0)
    trend_bonus = max(min(float(metric.get('trend_pct') or 0.0) * 1.25, 10.0), -10.0)
    activity_bonus = min(int(metric.get('trade_count') or 0) * 1.5, 8.0)
    raw = 50.0 + return_score + sharpe_proxy + drawdown_penalty + volatility_penalty + trend_bonus + activity_bonus
    score = max(min(raw, 100.0), 0.0)

    if ret > 0:
        reasons.append('positive return')
    if sharpe_proxy > 4:
        reasons.append('efficient risk-adjusted profile')
    if trend_bonus > 0:
        reasons.append('positive recent trend')
    if vol <= 15:
        reasons.append('controlled volatility')

    if float(metric.get('drawdown_proxy_pct') or 0.0) > float(policy.get('max_drawdown_pct') or MAX_DRAWDOWN_PCT):
        blocked_reasons.append('drawdown threshold breached')
    if vol > float(policy.get('max_volatility_pct') or MAX_VOLATILITY_PCT):
        blocked_reasons.append('volatility ceiling breached')
    if int(metric.get('trade_count') or 0) < int(policy.get('min_trade_count') or MIN_TRADE_COUNT):
        blocked_reasons.append('insufficient execution history')
    if score < float(policy.get('min_score_to_allocate') or MIN_SCORE_TO_ALLOCATE):
        blocked_reasons.append('score below allocation floor')

    status = 'eligible' if not blocked_reasons else 'blocked'
    return {
        **metric,
        'score': _round_pct(score),
        'status': status,
        'score_components': {
            'base': 50.0,
            'return_score': _round_pct(return_score),
            'sharpe_proxy': _round_pct(sharpe_proxy),
            'drawdown_penalty': _round_pct(drawdown_penalty),
            'volatility_penalty': _round_pct(volatility_penalty),
            'trend_bonus': _round_pct(trend_bonus),
            'activity_bonus': _round_pct(activity_bonus),
        },
        'reasons': reasons[:4],
        'blocked_reasons': blocked_reasons,
    }


def _scoreboard(email: str):
    store = _load(email)
    policy = store.get('policy') or {}
    metrics, live = _latest_strategy_metrics(email)
    rows = [_score_strategy(m, policy) for m in metrics]
    rows.sort(key=lambda x: (x.get('status') != 'eligible', -(x.get('score') or 0.0), -(x.get('invested_capital') or 0.0)))
    return rows, live, policy


def _build_plan(email: str, period: str | None = None):
    period = period or _current_period()
    rows, live, policy = _scoreboard(email)
    ledger_data, total_nav, reserve, deployable = _deployable_capital(email)
    eligible = [r for r in rows if r.get('status') == 'eligible']
    if not eligible:
        raise HTTPException(status_code=400, detail='no eligible strategies available for allocation')
    score_total = sum(float(r.get('score') or 0.0) for r in eligible)
    if score_total <= 0:
        raise HTTPException(status_code=400, detail='eligible strategies have non-positive score total')
    cap_weight = float(policy.get('max_strategy_weight') or MAX_STRATEGY_WEIGHT)
    raw_targets = []
    remaining_weight = max(1.0 - float(policy.get('cash_reserve_floor') or CASH_RESERVE_FLOOR), 0.0)
    for row in eligible:
        weight = (float(row.get('score') or 0.0) / score_total) * remaining_weight
        weight = min(weight, cap_weight)
        raw_targets.append({**row, 'target_weight': weight})
    allocated_weight = sum(x['target_weight'] for x in raw_targets)
    if allocated_weight > 0 and allocated_weight < remaining_weight:
        residual = remaining_weight - allocated_weight
        top = max(raw_targets, key=lambda x: x['score'])
        top['target_weight'] = min(cap_weight, top['target_weight'] + residual)
    strategy_outcomes = _execution()._strategy_outcomes(email)
    current_by_strategy = {r.get('strategy_id'): _round_money(r.get('allocated_capital') or 0.0) for r in (strategy_outcomes.get('rows') or [])}
    plan_rows = []
    for row in raw_targets:
        target_weight = _round_pct(row['target_weight'] * 100.0)
        target_capital = _round_money(deployable * row['target_weight'])
        current_capital = current_by_strategy.get(row['strategy_id'], 0.0)
        delta = _round_money(target_capital - current_capital)
        action = 'hold'
        if delta > 1.0:
            action = 'increase'
        elif delta < -1.0:
            action = 'reduce'
        plan_rows.append({
            'strategy_id': row['strategy_id'],
            'strategy_name': row['strategy_name'],
            'score': row['score'],
            'status': row['status'],
            'target_weight_pct': target_weight,
            'target_capital': target_capital,
            'current_capital': current_capital,
            'rebalance_delta': delta,
            'rebalance_action': action,
            'reasons': row['reasons'],
            'blocked_reasons': row['blocked_reasons'],
            'return_pct': row['return_pct'],
            'volatility_pct': row['volatility_pct'],
            'drawdown_proxy_pct': row['drawdown_proxy_pct'],
            'trade_count': row['trade_count'],
        })
    blocked = [r for r in rows if r.get('status') != 'eligible']
    for row in blocked:
        plan_rows.append({
            'strategy_id': row['strategy_id'],
            'strategy_name': row['strategy_name'],
            'score': row['score'],
            'status': row['status'],
            'target_weight_pct': 0.0,
            'target_capital': 0.0,
            'current_capital': current_by_strategy.get(row['strategy_id'], 0.0),
            'rebalance_delta': _round_money(-current_by_strategy.get(row['strategy_id'], 0.0)),
            'rebalance_action': 'reduce' if current_by_strategy.get(row['strategy_id'], 0.0) > 0 else 'block',
            'reasons': row['reasons'],
            'blocked_reasons': row['blocked_reasons'],
            'return_pct': row['return_pct'],
            'volatility_pct': row['volatility_pct'],
            'drawdown_proxy_pct': row['drawdown_proxy_pct'],
            'trade_count': row['trade_count'],
        })
    plan_rows.sort(key=lambda x: (x.get('status') != 'eligible', -(x.get('target_capital') or 0.0), -(x.get('score') or 0.0)))
    return {
        'period': period,
        'as_of': _now_ts(),
        'policy': policy,
        'total_nav': total_nav,
        'cash_reserve_target': reserve,
        'deployable_capital': deployable,
        'eligible_strategy_count': len(eligible),
        'blocked_strategy_count': len(blocked),
        'strategies': plan_rows,
        'live_summary': live.get('summary') or {},
    }


def _persist_decision(email: str, plan: dict, note: str | None = None):
    data = _load(email)
    decision = {
        'decision_id': f'alloc_{time.time_ns()}',
        'period': plan.get('period') or _current_period(),
        'created_at': _now_ts(),
        'note': note or '',
        'policy': plan.get('policy') or {},
        'total_nav': plan.get('total_nav') or 0.0,
        'cash_reserve_target': plan.get('cash_reserve_target') or 0.0,
        'deployable_capital': plan.get('deployable_capital') or 0.0,
        'eligible_strategy_count': plan.get('eligible_strategy_count') or 0,
        'blocked_strategy_count': plan.get('blocked_strategy_count') or 0,
        'strategies': plan.get('strategies') or [],
        'live_summary': plan.get('live_summary') or {},
    }
    data.setdefault('decisions', []).insert(0, decision)
    data['decisions'] = data.get('decisions', [])[:120]
    _save(email, data)
    return decision


def _latest_decision(email: str):
    data = _load(email)
    decisions = data.get('decisions', []) or []
    return decisions[0] if decisions else None


@router.get('/api/allocation-engine')
def allocation_engine_root():
    session = _require_user()
    email = session.get('email')
    latest = _latest_decision(email)
    return {'status': 'ok', 'latest_decision': latest, 'policy': _load(email).get('policy')}


@router.get('/api/allocation-engine/summary')
def allocation_engine_summary():
    session = _require_user()
    email = session.get('email')
    plan = _build_plan(email)
    latest = _latest_decision(email)
    return {'status': 'ok', 'plan': plan, 'latest_decision': latest, 'scoreboard': _scoreboard(email)[0]}


@router.get('/api/allocation-engine/decisions')
def allocation_engine_decisions():
    session = _require_user()
    email = session.get('email')
    data = _load(email)
    return {'status': 'ok', 'decisions': data.get('decisions', [])[:24], 'policy': data.get('policy')}


@router.post('/api/allocation-engine/plan')
def allocation_engine_plan(payload: dict = Body(None)):
    session = _require_user()
    email = session.get('email')
    period = str((payload or {}).get('period') or '').strip() or _current_period()
    return {'status': 'ok', 'plan': _build_plan(email, period)}


@router.post('/api/allocation-engine/run')
def allocation_engine_run(payload: dict = Body(None)):
    session = _require_user()
    email = session.get('email')
    period = str((payload or {}).get('period') or '').strip() or _current_period()
    note = str((payload or {}).get('note') or '').strip()
    plan = _build_plan(email, period)
    decision = _persist_decision(email, plan, note)
    return {'status': 'ok', 'decision': decision, 'plan': plan}


@router.post('/api/allocation-engine/policy')
def allocation_engine_policy(payload: dict = Body(...)):
    session = _require_user()
    email = session.get('email')
    data = _load(email)
    policy = data.get('policy') or {}
    for key in ['max_strategy_weight', 'cash_reserve_floor']:
        if key in payload:
            value = float(payload.get(key) or 0.0)
            if not 0 <= value <= 1:
                raise HTTPException(status_code=400, detail=f'{key} must be between 0 and 1')
            policy[key] = value
    for key in ['max_drawdown_pct', 'max_volatility_pct', 'min_trade_count', 'min_score_to_allocate']:
        if key in payload:
            policy[key] = float(payload.get(key) or 0.0)
    data['policy'] = policy
    _save(email, data)
    return {'status': 'ok', 'policy': policy}


@router.post('/api/allocation-engine/bootstrap-demo')
def allocation_engine_bootstrap_demo(payload: dict = Body(None)):
    session = _require_user()
    email = session.get('email')
    months = int((payload or {}).get('months') or 6)
    period = str((payload or {}).get('period') or '').strip() or _current_period()
    _statement()._seed_demo(email, period)
    _execution()._bootstrap_demo(email, period)
    try:
        _performance().performance_engine_bootstrap_demo({'months': months})
    except Exception:
        # If history already exists or current_nav was stale, attempt a fresh snapshot path.
        try:
            _performance().performance_engine_snapshot({})
            _performance().performance_engine_bootstrap_demo({'months': months})
        except Exception:
            pass
    plan = _build_plan(email, period)
    decision = _persist_decision(email, plan, 'demo bootstrap allocation plan')
    return {'status': 'ok', 'plan': plan, 'decision': decision}
