from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["autonomous-fund-mode"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
AUTO_DIR = ARTIFACTS_DIR / "autonomous_fund_mode"

DEFAULT_STATE = {
    'mode': 'IDLE',
    'scheduler': 'manual',
    'frequency': 'monthly',
    'kill_switch': False,
    'capital_state': 'CASH',
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _statement():
    from backend.app import qnt30627_statement_batch_router as statement
    return statement


def _performance():
    from backend.app import qnt30628_performance_engine_router as performance
    return performance


def _execution():
    from backend.app import qnt30629_strategy_execution_router as execution
    return execution


def _allocation():
    from backend.app import qnt30630_allocation_engine_router as allocation
    return allocation


def _broker():
    from backend.app import qnt30631_broker_integration_router as broker
    return broker


def _safe(v: str) -> str:
    return hashlib.sha256((v or '').strip().lower().encode('utf-8')).hexdigest()[:24]


def _path(email: str) -> Path:
    AUTO_DIR.mkdir(parents=True, exist_ok=True)
    return AUTO_DIR / f'{_safe(email)}.json'


def _require_user():
    return _mu()._require_session()


def _now_ts() -> int:
    return int(time.time())


def _current_period() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m')


def _round_money(v) -> float:
    return round(float(v or 0.0), 2)


def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {
            'email': email,
            'system_state': {
                **DEFAULT_STATE,
                'current_period': _current_period(),
                'last_cycle': None,
                'last_cycle_status': None,
            },
            'cycle_history': [],
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


def _health_check(email: str) -> dict:
    checks = {
        'allocation_engine': 'ok',
        'broker_layer': 'ok',
        'execution_engine': 'ok',
        'performance_engine': 'ok',
        'statement_engine': 'ok',
    }
    errors = []
    try:
        _allocation()._build_plan(email)
    except Exception as exc:
        checks['allocation_engine'] = 'error'
        errors.append(f'allocation_engine: {exc}')
    try:
        _execution()._summary(email)
    except Exception as exc:
        checks['execution_engine'] = 'error'
        errors.append(f'execution_engine: {exc}')
    try:
        _performance()._live_summary(email)
    except Exception as exc:
        checks['performance_engine'] = 'error'
        errors.append(f'performance_engine: {exc}')
    try:
        _statement()._load(email)
    except Exception as exc:
        checks['statement_engine'] = 'error'
        errors.append(f'statement_engine: {exc}')
    try:
        _broker()._summary(email)
    except Exception as exc:
        checks['broker_layer'] = 'error'
        errors.append(f'broker_layer: {exc}')
    return {
        'checks': checks,
        'status': 'ok' if not errors else 'error',
        'errors': errors,
    }


def _persist_statement_snapshot(email: str, period: str) -> dict:
    statements = _statement()
    data = statements._load(email)
    snapshot = statements._build_period_snapshot(email, period)
    data.setdefault('periods', {})[period] = snapshot
    data.setdefault('batch_runs', []).insert(0, {
        'batch_id': snapshot.get('batch_id'),
        'period': period,
        'generated_at': snapshot.get('generated_at'),
        'status': snapshot.get('status'),
        'statement_count': snapshot.get('summary', {}).get('statement_count', 0),
        'reconciliation_status': snapshot.get('reconciliation', {}).get('status'),
    })
    data['batch_runs'] = data.get('batch_runs', [])[:200]
    statements._save(email, data)
    return snapshot


def _run_cycle(email: str, period: str | None = None) -> dict:
    data = _load(email)
    state = data.setdefault('system_state', {})
    if state.get('kill_switch'):
        raise HTTPException(status_code=423, detail='autonomous fund kill switch is enabled')
    use_period = str(period or state.get('current_period') or _current_period())
    state['mode'] = 'RUNNING'
    state['current_period'] = use_period
    _save(email, data)

    health = _health_check(email)
    if health['status'] != 'ok':
        state['mode'] = 'ERROR'
        state['last_cycle_status'] = 'health_check_failed'
        _save(email, data)
        raise HTTPException(status_code=500, detail='; '.join(health['errors']))

    plan = _allocation()._build_plan(email, use_period)
    broker_result = _broker()._apply_allocation_plan(email, plan, use_period)
    performance = _performance()._live_summary(email)
    statement_snapshot = _persist_statement_snapshot(email, use_period)
    exec_summary = _execution()._summary(email, use_period)

    cycle = {
        'cycle_id': f'cycle_{time.time_ns()}',
        'period': use_period,
        'started_at': _now_ts(),
        'completed_at': _now_ts(),
        'health': health,
        'allocation_plan': {
            'eligible_strategy_count': plan.get('eligible_strategy_count'),
            'blocked_strategy_count': plan.get('blocked_strategy_count'),
            'deployable_capital': plan.get('deployable_capital'),
            'reserve_target': plan.get('cash_reserve_target'),
            'strategies': [
                {
                    'strategy_id': r.get('strategy_id'),
                    'strategy_name': r.get('strategy_name'),
                    'target_capital': r.get('target_capital'),
                    'rebalance_action': r.get('rebalance_action'),
                    'status': r.get('status'),
                }
                for r in (plan.get('strategies') or [])
            ],
        },
        'broker_execution': {
            'executed_orders': broker_result.get('executed_orders', 0),
            'blocked_strategies': broker_result.get('blocked_strategies', []),
            'fills': broker_result.get('fills', []),
        },
        'performance': performance.get('summary', {}),
        'execution_summary': exec_summary,
        'statements': {
            'batch_id': statement_snapshot.get('batch_id'),
            'statement_count': statement_snapshot.get('summary', {}).get('statement_count', 0),
            'reconciliation_status': statement_snapshot.get('reconciliation', {}).get('status'),
        },
        'status': 'completed',
    }

    data = _load(email)
    state = data.setdefault('system_state', {})
    state['mode'] = 'IDLE'
    state['last_cycle'] = cycle['completed_at']
    state['last_cycle_status'] = 'completed'
    state['capital_state'] = 'DEPLOYED' if broker_result.get('executed_orders', 0) > 0 else 'CASH'
    data.setdefault('cycle_history', []).insert(0, cycle)
    data['cycle_history'] = data.get('cycle_history', [])[:120]
    _save(email, data)
    return cycle


def _bootstrap_demo(email: str, period: str | None = None) -> dict:
    use_period = str(period or _current_period())
    _statement()._seed_demo(email, use_period)
    _execution()._bootstrap_demo(email, use_period)
    _performance().performance_engine_bootstrap_demo({'months': 6})
    _broker()._bootstrap_demo(email, use_period)
    cycle = _run_cycle(email, use_period)
    return {
        'period': use_period,
        'cycle_id': cycle.get('cycle_id'),
        'executed_orders': cycle.get('broker_execution', {}).get('executed_orders', 0),
        'statement_count': cycle.get('statements', {}).get('statement_count', 0),
    }


def _summary(email: str) -> dict:
    data = _load(email)
    state = data.get('system_state') or {}
    cycles = data.get('cycle_history') or []
    latest = cycles[0] if cycles else None
    performance = _performance()._live_summary(email).get('summary', {})
    return {
        'system_state': state,
        'cycle_count': len(cycles),
        'latest_cycle': latest,
        'performance': performance,
        'broker_summary': _broker()._summary(email),
        'health': _health_check(email),
    }


@router.get('/api/autonomous-fund/summary')
def autonomous_fund_summary():
    session = _require_user()
    email = session.get('email')
    data = _load(email)
    return {
        'status': 'ok',
        **_summary(email),
        'cycle_history': data.get('cycle_history') or [],
    }


@router.post('/api/autonomous-fund/state')
def autonomous_fund_state(payload: dict = Body(...)):
    session = _require_user()
    email = session.get('email')
    data = _load(email)
    state = data.setdefault('system_state', {})
    for field in ['scheduler', 'frequency', 'current_period']:
        if field in payload:
            state[field] = payload.get(field)
    if 'kill_switch' in payload:
        state['kill_switch'] = bool(payload.get('kill_switch'))
    if 'mode' in payload:
        mode = str(payload.get('mode') or state.get('mode') or 'IDLE').upper()
        if mode not in {'IDLE', 'RUNNING', 'PAUSED', 'ERROR'}:
            raise HTTPException(status_code=400, detail='invalid mode')
        state['mode'] = mode
    _save(email, data)
    return {'status': 'updated', 'system_state': state}


@router.post('/api/autonomous-fund/run-cycle')
def autonomous_fund_run_cycle(payload: dict = Body(None)):
    session = _require_user()
    email = session.get('email')
    period = str((payload or {}).get('period') or _current_period())
    cycle = _run_cycle(email, period)
    return {'status': 'completed', 'cycle': cycle, 'summary': _summary(email)}


@router.post('/api/autonomous-fund/bootstrap-demo')
def autonomous_fund_bootstrap_demo(payload: dict = Body(None)):
    session = _require_user()
    email = session.get('email')
    period = str((payload or {}).get('period') or _current_period())
    demo = _bootstrap_demo(email, period)
    return {'status': 'seeded', 'demo': demo, 'summary': _summary(email)}
