from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["governance-compliance-layer"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
GOV_DIR = ARTIFACTS_DIR / "governance_compliance_layer"

DEFAULT_POLICIES = {
    "max_strategy_weight": 0.40,
    "max_single_order_notional": 250000.0,
    "max_portfolio_drawdown_pct": 20.0,
    "max_open_orders": 12,
    "restricted_symbols": ["GME", "AMC"],
    "approved_strategies": [],
    "approval_required_live_mode": True,
    "allow_autonomous_cycles": True,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _audit():
    from backend.app import qnt30602_audit_trail_router as audit
    return audit


def _breach():
    from backend.app import qnt30610_governance_router as breach
    return breach


def _autonomous():
    from backend.app import qnt30632_autonomous_fund_router as autonomous
    return autonomous


def _allocation():
    from backend.app import qnt30630_allocation_engine_router as allocation
    return allocation


def _broker():
    from backend.app import qnt30631_broker_integration_router as broker
    return broker


def _safe(v: str) -> str:
    return hashlib.sha256((v or '').strip().lower().encode('utf-8')).hexdigest()[:24]


def _path(email: str) -> Path:
    GOV_DIR.mkdir(parents=True, exist_ok=True)
    return GOV_DIR / f'{_safe(email)}.json'


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
            'policies': dict(DEFAULT_POLICIES),
            'compliance_events': [],
            'approval_queue': [],
            'override_log': [],
            'audit_snapshots': [],
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


def _append_event(data: dict, event_type: str, severity: str, status: str, details: dict):
    event = {
        'event_id': f'gc_{time.time_ns()}',
        'type': event_type,
        'severity': severity,
        'status': status,
        'timestamp': _now_ts(),
        **details,
    }
    data.setdefault('compliance_events', []).insert(0, event)
    data['compliance_events'] = data.get('compliance_events', [])[:500]
    return event


def _append_approval(data: dict, payload: dict):
    approval = {
        'approval_id': f'appr_{time.time_ns()}',
        'requested_at': _now_ts(),
        'status': 'pending',
        **payload,
    }
    data.setdefault('approval_queue', []).insert(0, approval)
    data['approval_queue'] = data.get('approval_queue', [])[:200]
    return approval


def _append_override(data: dict, payload: dict):
    override = {
        'override_id': f'ovr_{time.time_ns()}',
        'timestamp': _now_ts(),
        **payload,
    }
    data.setdefault('override_log', []).insert(0, override)
    data['override_log'] = data.get('override_log', [])[:200]
    return override


def _capture_snapshot(email: str, data: dict | None = None) -> dict:
    store = data or _load(email)
    audit_summary = _audit().audit_summary()
    breach_summary = _breach().governance_summary()
    autonomous_summary = _autonomous()._summary(email)
    broker_summary = _broker()._summary(email)
    allocation_plan = _allocation()._build_plan(email)
    latest_cycle = autonomous_summary.get('latest_cycle') or {}
    snapshot = {
        'snapshot_id': f'snap_{time.time_ns()}',
        'timestamp': _now_ts(),
        'period': (autonomous_summary.get('system_state') or {}).get('current_period') or _current_period(),
        'audit_chain_ok': bool(audit_summary.get('chain_integrity_ok')),
        'breach_status': (breach_summary.get('latest_snapshot') or {}).get('status', 'clear'),
        'autonomous_mode': (autonomous_summary.get('system_state') or {}).get('mode'),
        'broker_mode': broker_summary.get('mode'),
        'open_order_count': broker_summary.get('open_order_count'),
        'latest_cycle_status': latest_cycle.get('status'),
        'portfolio_return_pct': (autonomous_summary.get('performance') or {}).get('portfolio_return_pct'),
        'max_drawdown_pct': (autonomous_summary.get('performance') or {}).get('max_drawdown_pct'),
        'strategy_count': allocation_plan.get('strategy_count'),
        'eligible_strategy_count': allocation_plan.get('eligible_strategy_count'),
        'blocked_strategy_count': allocation_plan.get('blocked_strategy_count'),
    }
    store.setdefault('audit_snapshots', []).insert(0, snapshot)
    store['audit_snapshots'] = store.get('audit_snapshots', [])[:120]
    return snapshot


def _evaluate_action(email: str, action: dict, data: dict | None = None) -> dict:
    store = data or _load(email)
    policies = store.get('policies') or {}
    action_type = str(action.get('action_type') or 'unknown')
    strategy_id = str(action.get('strategy_id') or '').strip()
    symbol = str(action.get('symbol') or '').upper().strip()
    target_weight = float(action.get('target_weight') or 0.0)
    order_notional = float(action.get('order_notional') or 0.0)
    projected_drawdown = float(action.get('projected_drawdown_pct') or 0.0)
    execution_mode = str(action.get('execution_mode') or 'paper').lower()
    reasons = []
    warnings = []
    status = 'approved'

    if symbol and symbol in {s.upper() for s in policies.get('restricted_symbols') or []}:
        reasons.append(f'symbol {symbol} is restricted')
        status = 'blocked'
    if target_weight > float(policies.get('max_strategy_weight') or DEFAULT_POLICIES['max_strategy_weight']) + 1e-9:
        reasons.append('strategy weight exceeds governance limit')
        status = 'blocked'
    if order_notional > float(policies.get('max_single_order_notional') or DEFAULT_POLICIES['max_single_order_notional']) + 1e-9:
        reasons.append('single order notional exceeds limit')
        status = 'blocked'
    if projected_drawdown > float(policies.get('max_portfolio_drawdown_pct') or DEFAULT_POLICIES['max_portfolio_drawdown_pct']) + 1e-9:
        reasons.append('projected drawdown exceeds portfolio policy')
        status = 'blocked'

    broker_summary = _broker()._summary(email)
    if int(broker_summary.get('open_order_count') or 0) > int(policies.get('max_open_orders') or DEFAULT_POLICIES['max_open_orders']):
        warnings.append('open order count exceeds soft operating range')
        if status == 'approved':
            status = 'requires_review'

    approved_strategies = {str(s).strip() for s in (policies.get('approved_strategies') or []) if str(s).strip()}
    if strategy_id and approved_strategies and strategy_id not in approved_strategies:
        warnings.append('strategy is outside approved strategy universe')
        if status == 'approved':
            status = 'requires_review'

    if execution_mode == 'live' and bool(policies.get('approval_required_live_mode')):
        warnings.append('live execution requires approval')
        if status == 'approved':
            status = 'requires_approval'

    if action_type == 'autonomous_cycle' and not bool(policies.get('allow_autonomous_cycles')):
        reasons.append('autonomous cycles are disabled by policy')
        status = 'blocked'

    return {
        'action_type': action_type,
        'strategy_id': strategy_id or None,
        'symbol': symbol or None,
        'status': status,
        'reasons': reasons,
        'warnings': warnings,
        'evaluated_at': _now_ts(),
    }


def _summary(email: str) -> dict:
    data = _load(email)
    if not data.get('audit_snapshots'):
        _capture_snapshot(email, data)
        _save(email, data)
    policies = data.get('policies') or {}
    events = data.get('compliance_events') or []
    approvals = data.get('approval_queue') or []
    overrides = data.get('override_log') or []
    audit_summary = _audit().audit_summary()
    breach_summary = _breach().governance_summary()
    autonomous_summary = _autonomous()._summary(email)
    broker_summary = _broker()._summary(email)
    allocation_plan = _allocation()._build_plan(email)
    open_approvals = [a for a in approvals if a.get('status') == 'pending']
    blocking_events = [e for e in events if e.get('status') == 'blocked']
    return {
        'policies': policies,
        'event_count': len(events),
        'open_approval_count': len(open_approvals),
        'override_count': len(overrides),
        'blocked_event_count': len(blocking_events),
        'latest_snapshot': (data.get('audit_snapshots') or [None])[0],
        'audit_summary': audit_summary,
        'breach_summary': breach_summary,
        'autonomous_summary': autonomous_summary,
        'broker_summary': broker_summary,
        'allocation_overview': {
            'strategy_count': allocation_plan.get('strategy_count'),
            'eligible_strategy_count': allocation_plan.get('eligible_strategy_count'),
            'blocked_strategy_count': allocation_plan.get('blocked_strategy_count'),
            'deployable_capital': allocation_plan.get('deployable_capital'),
            'cash_reserve_target': allocation_plan.get('cash_reserve_target'),
        },
        'recent_events': events[:25],
        'approval_queue': approvals[:25],
        'override_log': overrides[:25],
        'snapshots': (data.get('audit_snapshots') or [])[:25],
    }


def _seed_demo(email: str) -> dict:
    _autonomous()._bootstrap_demo(email, _current_period())
    data = _load(email)
    snapshot = _capture_snapshot(email, data)
    eval_order = _evaluate_action(email, {
        'action_type': 'broker_order',
        'strategy_id': 'BTC_MOMENTUM',
        'symbol': 'BTCUSD',
        'target_weight': 0.32,
        'order_notional': 85000,
        'projected_drawdown_pct': 11.0,
        'execution_mode': 'paper',
    }, data)
    _append_event(data, 'broker_order_review', 'info', eval_order['status'], eval_order)
    eval_live = _evaluate_action(email, {
        'action_type': 'broker_order',
        'strategy_id': 'MACRO_TREND',
        'symbol': 'AAPL',
        'target_weight': 0.18,
        'order_notional': 120000,
        'projected_drawdown_pct': 9.0,
        'execution_mode': 'live',
    }, data)
    approval = None
    if eval_live['status'] == 'requires_approval':
        approval = _append_approval(data, {
            'action_type': 'live_execution',
            'strategy_id': 'MACRO_TREND',
            'symbol': 'AAPL',
            'requested_by': email,
            'evaluation': eval_live,
        })
    _audit()._append_record(email, 'governance_compliance_snapshot', snapshot)
    _save(email, data)
    return {
        'snapshot_id': snapshot.get('snapshot_id'),
        'approval_id': approval.get('approval_id') if approval else None,
        'event_count': len(data.get('compliance_events') or []),
    }


@router.get('/api/governance-compliance/summary')
def governance_compliance_summary():
    session = _require_user()
    email = session.get('email')
    data = _load(email)
    return {
        'status': 'ok',
        **_summary(email),
        'compliance_events': data.get('compliance_events') or [],
    }


@router.post('/api/governance-compliance/policies')
def governance_compliance_policies(payload: dict = Body(...)):
    session = _require_user()
    email = session.get('email')
    data = _load(email)
    policies = data.setdefault('policies', dict(DEFAULT_POLICIES))
    for key in DEFAULT_POLICIES:
        if key in payload:
            policies[key] = payload.get(key)
    _append_event(data, 'policy_update', 'info', 'recorded', {'changes': payload})
    _audit()._append_record(email, 'governance_policy_update', {'changes': payload})
    _save(email, data)
    return {'status': 'updated', 'policies': policies}


@router.post('/api/governance-compliance/evaluate-action')
def governance_compliance_evaluate_action(payload: dict = Body(...)):
    session = _require_user()
    email = session.get('email')
    data = _load(email)
    evaluation = _evaluate_action(email, payload, data)
    severity = 'high' if evaluation['status'] == 'blocked' else ('medium' if evaluation['status'] in {'requires_approval', 'requires_review'} else 'info')
    event = _append_event(data, 'action_evaluation', severity, evaluation['status'], {'evaluation': evaluation})
    approval = None
    if evaluation['status'] == 'requires_approval':
        approval = _append_approval(data, {
            'action_type': evaluation['action_type'],
            'strategy_id': evaluation.get('strategy_id'),
            'symbol': evaluation.get('symbol'),
            'requested_by': email,
            'evaluation': evaluation,
        })
    _audit()._append_record(email, 'governance_action_evaluation', {'evaluation': evaluation, 'approval': approval})
    _save(email, data)
    return {'status': evaluation['status'], 'evaluation': evaluation, 'event': event, 'approval': approval}


@router.post('/api/governance-compliance/capture-cycle')
def governance_compliance_capture_cycle(payload: dict = Body(None)):
    session = _require_user()
    email = session.get('email')
    data = _load(email)
    snapshot = _capture_snapshot(email, data)
    event = _append_event(data, 'cycle_snapshot', 'info', 'captured', snapshot)
    _audit()._append_record(email, 'governance_cycle_snapshot', snapshot)
    _save(email, data)
    return {'status': 'captured', 'snapshot': snapshot, 'event': event}


@router.post('/api/governance-compliance/approval-decision')
def governance_compliance_approval_decision(payload: dict = Body(...)):
    session = _require_user()
    email = session.get('email')
    data = _load(email)
    approval_id = str(payload.get('approval_id') or '')
    decision = str(payload.get('decision') or '').lower()
    justification = str(payload.get('justification') or '')
    if decision not in {'approved', 'rejected'}:
        raise HTTPException(status_code=400, detail='decision must be approved or rejected')
    approval = next((a for a in data.get('approval_queue', []) if a.get('approval_id') == approval_id), None)
    if not approval:
        raise HTTPException(status_code=404, detail='approval request not found')
    approval['status'] = decision
    approval['decided_at'] = _now_ts()
    approval['justification'] = justification
    event = _append_event(data, 'approval_decision', 'info' if decision == 'approved' else 'medium', decision, {'approval_id': approval_id, 'justification': justification})
    _audit()._append_record(email, 'governance_approval_decision', {'approval_id': approval_id, 'decision': decision, 'justification': justification})
    _save(email, data)
    return {'status': decision, 'approval': approval, 'event': event}


@router.post('/api/governance-compliance/override')
def governance_compliance_override(payload: dict = Body(...)):
    session = _require_user()
    email = session.get('email')
    data = _load(email)
    justification = str(payload.get('justification') or '').strip()
    if not justification:
        raise HTTPException(status_code=400, detail='justification required')
    override = _append_override(data, {
        'action_type': str(payload.get('action_type') or 'manual_override'),
        'reference_id': str(payload.get('reference_id') or ''),
        'justification': justification,
        'operator': session.get('display_name') or email,
    })
    event = _append_event(data, 'governance_override', 'medium', 'recorded', override)
    _audit()._append_record(email, 'governance_override', override)
    _save(email, data)
    return {'status': 'recorded', 'override': override, 'event': event}


@router.post('/api/governance-compliance/bootstrap-demo')
def governance_compliance_bootstrap_demo(payload: dict = Body(None)):
    session = _require_user()
    email = session.get('email')
    demo = _seed_demo(email)
    return {'status': 'seeded', 'demo': demo, 'summary': _summary(email)}
