from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=['capital-committee-deliberation-layer'])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / 'backend' / 'artifacts'
ENGINE_DIR = ARTIFACTS_DIR / 'capital_committee_deliberation_layer'
DEFAULT_POLICY = {
    'retain_cycles': 180,
    'minimum_committee_score': 86.0,
    'require_operator_clear': True,
    'require_release_clear': True,
    'require_safety_clear': True,
    'require_fund_admin_clear': True,
    'require_forensic_clear': True,
    'require_recovery_clear': True,
    'require_memory_context': True,
    'require_allocation_governance': True,
    'operator_review_notional_threshold': 250000.0,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _operator():
    from backend.app import qnt30702_operator_command_console_router as operator
    return operator


def _release():
    from backend.app import qnt30700_institutional_release_control_router as release
    return release


def _safety():
    from backend.app import qnt30703_live_broker_safety_layer_router as safety
    return safety


def _fund_admin():
    from backend.app import qnt30705_fund_admin_control_center_router as fund_admin
    return fund_admin


def _forensic():
    from backend.app import qnt30706_forensic_audit_system_router as forensic
    return forensic


def _recovery():
    from backend.app import qnt30707_recovery_system_router as recovery
    return recovery


def _executive():
    from backend.app import qnt30718_executive_ai_command_layer_router as executive
    return executive


def _memory():
    from backend.app import qnt30719_executive_decision_memory_layer_router as memory
    return memory


def _allocation_governance():
    from backend.app import qnt30713_autonomous_allocation_governance_layer_router as allocation_governance
    return allocation_governance


def _safe(v: str) -> str:
    return hashlib.sha256((v or '').strip().lower().encode('utf-8')).hexdigest()[:24]


def _path(email: str) -> Path:
    ENGINE_DIR.mkdir(parents=True, exist_ok=True)
    return ENGINE_DIR / f'{_safe(email)}.json'


def _require_user():
    return _mu()._require_session()


def _now_ts() -> int:
    return int(time.time())


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append(store: dict, key: str, row: dict, retain: int):
    arr = list(store.get(key) or [])
    arr.insert(0, row)
    store[key] = arr[: max(int(retain or 1), 1)]


def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {
            'email': email,
            'policy': dict(DEFAULT_POLICY),
            'deliberations': [],
            'votes': [],
            'alerts': [],
            'committee_book': [],
            'last_context': {},
            'latest_deliberation': None,
            'latest_vote': None,
        }
        path.write_text(json.dumps(data, indent=2), encoding='utf-8')
        return data
    return json.loads(path.read_text(encoding='utf-8'))


def _save(email: str, data: dict):
    _path(email).write_text(json.dumps(data, indent=2), encoding='utf-8')


def _cross_system_context(email: str) -> dict:
    operator = _operator()._summary_for_email(email)
    release = _release()._summary_for_email(email)
    safety = _safety()._summary_for_email(email)
    fund_admin = _fund_admin()._summary_for_email(email)
    forensic = _forensic()._summary_for_email(email)
    recovery = _recovery()._summary_for_email(email)
    executive = _executive()._summary_for_email(email)
    memory = _memory()._summary_for_email(email)
    allocation = _allocation_governance()._summary_for_email(email)
    return {
        'captured_at': _now_iso(),
        'operator': {
            'posture': (operator.get('operator_command_console_status') or {}).get('posture'),
            'override_required': (operator.get('operator_command_console_status') or {}).get('operator_override_required'),
            'execution_paused': (operator.get('operator_command_console_status') or {}).get('execution_paused'),
        },
        'release': {
            'posture': (release.get('institutional_release_control_status') or {}).get('posture'),
            'active_version': (release.get('institutional_release_control_status') or {}).get('active_version'),
        },
        'safety': {
            'posture': (safety.get('live_broker_safety_layer_status') or {}).get('posture'),
            'kill_switch_active': (safety.get('live_broker_safety_layer_status') or {}).get('kill_switch_active'),
            'latest_score': (safety.get('live_broker_safety_layer_status') or {}).get('latest_score'),
        },
        'fund_admin': {
            'posture': (fund_admin.get('fund_admin_control_center_status') or {}).get('posture'),
            'latest_score': (fund_admin.get('fund_admin_control_center_status') or {}).get('latest_score'),
            'aum': (fund_admin.get('fund_admin_control_center_status') or {}).get('aum'),
        },
        'forensic': {
            'posture': (forensic.get('forensic_status') or {}).get('posture'),
            'critical_open_count': (forensic.get('forensic_status') or {}).get('critical_open_count'),
        },
        'recovery': {
            'posture': (recovery.get('recovery_status') or {}).get('posture'),
            'safe_mode': (recovery.get('recovery_status') or {}).get('safe_mode'),
            'valid_state': (recovery.get('current_validation') or {}).get('valid_state'),
        },
        'executive': {
            'posture': (executive.get('executive_ai_command_layer_status') or {}).get('posture'),
            'recommended_band': (executive.get('executive_ai_command_layer_status') or {}).get('recommended_band'),
            'latest_score': (executive.get('executive_ai_command_layer_status') or {}).get('latest_score'),
        },
        'memory': {
            'posture': (memory.get('executive_decision_memory_layer_status') or {}).get('posture'),
            'memory_band': (memory.get('executive_decision_memory_layer_status') or {}).get('memory_band'),
            'memory_count': (memory.get('executive_decision_memory_layer_status') or {}).get('memory_count'),
        },
        'allocation_governance': {
            'posture': (allocation.get('autonomous_allocation_governance_layer_status') or {}).get('posture'),
            'latest_score': (allocation.get('autonomous_allocation_governance_layer_status') or {}).get('latest_score'),
            'autonomy_band': (allocation.get('autonomous_allocation_governance_layer_status') or {}).get('autonomy_band'),
        },
    }


def _evaluate(payload: dict, ctx: dict, policy: dict) -> dict:
    conviction = float(payload.get('conviction_score') or 0.0)
    scenario = float(payload.get('scenario_coverage_score') or 0.0)
    dissent = float(payload.get('dissent_risk_score') or 0.0)
    execution = float(payload.get('execution_feasibility_score') or 0.0)
    notional = float(payload.get('proposed_notional') or 0.0)
    blockers = []
    if policy.get('require_operator_clear') and ctx.get('operator', {}).get('posture') not in ('READY', 'CLEAR', 'ACTIVE'):
        blockers.append('operator-not-clear')
    if ctx.get('operator', {}).get('execution_paused'):
        blockers.append('operator-execution-paused')
    if policy.get('require_release_clear') and ctx.get('release', {}).get('posture') not in ('READY', 'CLEAR', 'DEPLOYED', 'ACTIVE'):
        blockers.append('release-not-clear')
    if policy.get('require_safety_clear'):
        safety_posture = ctx.get('safety', {}).get('posture')
        if safety_posture not in ('APPROVED', 'READY', 'SAFE', 'CLEAR'):
            blockers.append('safety-not-clear')
        if ctx.get('safety', {}).get('kill_switch_active'):
            blockers.append('safety-kill-switch-active')
    if policy.get('require_fund_admin_clear') and ctx.get('fund_admin', {}).get('posture') not in ('READY', 'CLEAR', 'CLOSED'):
        blockers.append('fund-admin-not-clear')
    if policy.get('require_forensic_clear') and ctx.get('forensic', {}).get('posture') not in ('READY', 'CLEAR', 'STABLE'):
        blockers.append('forensic-not-clear')
    if policy.get('require_recovery_clear') and (ctx.get('recovery', {}).get('safe_mode') or not ctx.get('recovery', {}).get('valid_state')):
        blockers.append('recovery-not-clear')
    if policy.get('require_memory_context') and ctx.get('memory', {}).get('posture') not in ('TRUSTED', 'WATCH'):
        blockers.append('memory-context-missing')
    if policy.get('require_allocation_governance') and ctx.get('allocation_governance', {}).get('posture') not in ('APPROVED', 'SUPERVISED', 'READY', 'CLEAR'):
        blockers.append('allocation-governance-not-clear')

    score = round(max(0.0, min(100.0, conviction * 0.30 + scenario * 0.25 + execution * 0.25 + (100.0 - dissent) * 0.20)), 2)

    posture = 'APPROVED'
    action_band = 'EXECUTE'
    if blockers:
        posture = 'BLOCKED'
        action_band = 'DEFER'
    elif score < float(policy.get('minimum_committee_score') or 0.0):
        posture = 'WATCH'
        action_band = 'REVIEW'

    review_required = bool(notional >= float(policy.get('operator_review_notional_threshold') or 0.0) or ctx.get('operator', {}).get('override_required'))
    if review_required and posture == 'APPROVED':
        posture = 'OPERATOR_REVIEW'
        action_band = 'SUPERVISE'

    committee_band = 'HIGH_CONVICTION'
    if posture == 'BLOCKED':
        committee_band = 'QUARANTINE'
    elif posture in ('WATCH', 'OPERATOR_REVIEW'):
        committee_band = 'SUPERVISED'

    return {
        'score': score,
        'posture': posture,
        'committee_band': committee_band,
        'action_band': action_band,
        'review_required': review_required,
        'blockers': blockers,
    }


def _summary_for_email(email: str) -> dict:
    store = _load(email)
    latest = store.get('latest_deliberation') or {}
    latest_vote = store.get('latest_vote') or {}
    return {
        'capital_committee_deliberation_layer_status': {
            'posture': (latest.get('evaluation') or {}).get('posture', 'IDLE'),
            'latest_score': (latest.get('evaluation') or {}).get('score'),
            'committee_band': (latest.get('evaluation') or {}).get('committee_band'),
            'action_band': (latest.get('evaluation') or {}).get('action_band'),
            'deliberation_count': len(store.get('deliberations') or []),
            'vote_count': len(store.get('votes') or []),
            'alert_count': len(store.get('alerts') or []),
        },
        'latest_deliberation': latest,
        'latest_vote': latest_vote,
        'policy': store.get('policy') or dict(DEFAULT_POLICY),
        'committee_book': store.get('committee_book') or [],
        'alerts': store.get('alerts') or [],
        'last_context': store.get('last_context') or {},
    }


@router.get('/api/capital-committee-deliberation-layer/summary')
def summary(session=Depends(_require_user)):
    return _summary_for_email(session['email'])


@router.post('/api/capital-committee-deliberation-layer/evaluate')
def evaluate(payload: dict = Body(...), session=Depends(_require_user)):
    email = session['email']
    store = _load(email)
    policy = store.get('policy') or dict(DEFAULT_POLICY)
    ctx = _cross_system_context(email)
    evaluation = _evaluate(payload, ctx, policy)
    row = {
        'deliberation_id': f'ccdelib-{_now_ts()}',
        'created_at': _now_iso(),
        'proposal_title': payload.get('proposal_title') or 'untitled-capital-committee-proposal',
        'proposal_scope': payload.get('proposal_scope') or 'CAPITAL_COMMITTEE',
        'proposal_summary': payload.get('proposal_summary') or '',
        'capital_action': payload.get('capital_action') or 'HOLD',
        'inputs': payload,
        'context': ctx,
        'evaluation': evaluation,
    }
    _append(store, 'deliberations', row, policy.get('retain_cycles', 180))
    _append(store, 'committee_book', {
        'created_at': row['created_at'],
        'proposal_title': row['proposal_title'],
        'posture': evaluation.get('posture'),
        'committee_band': evaluation.get('committee_band'),
        'action_band': evaluation.get('action_band'),
    }, policy.get('retain_cycles', 180))
    if evaluation.get('blockers'):
        _append(store, 'alerts', {
            'created_at': row['created_at'],
            'proposal_title': row['proposal_title'],
            'posture': evaluation.get('posture'),
            'blockers': evaluation.get('blockers'),
        }, policy.get('retain_cycles', 180))
    store['last_context'] = ctx
    store['latest_deliberation'] = row
    _save(email, store)
    return row


@router.post('/api/capital-committee-deliberation-layer/vote')
def vote(payload: dict = Body(...), session=Depends(_require_user)):
    email = session['email']
    store = _load(email)
    policy = store.get('policy') or dict(DEFAULT_POLICY)
    latest = store.get('latest_deliberation') or {}
    vote_row = {
        'vote_id': f'ccvote-{_now_ts()}',
        'created_at': _now_iso(),
        'deliberation_id': payload.get('deliberation_id') or latest.get('deliberation_id'),
        'vote': (payload.get('vote') or 'APPROVE').upper(),
        'voter_role': payload.get('voter_role') or 'OPERATOR',
        'commentary': payload.get('commentary') or '',
    }
    _append(store, 'votes', vote_row, policy.get('retain_cycles', 180))
    store['latest_vote'] = vote_row
    _save(email, store)
    return vote_row


@router.post('/api/capital-committee-deliberation-layer/policy')
def policy(payload: dict = Body(...), session=Depends(_require_user)):
    email = session['email']
    store = _load(email)
    merged = dict(DEFAULT_POLICY)
    merged.update(store.get('policy') or {})
    merged.update(payload or {})
    store['policy'] = merged
    _save(email, store)
    return {'ok': True, 'policy': merged}


@router.post('/api/capital-committee-deliberation-layer/bootstrap-demo')
def bootstrap_demo(session=Depends(_require_user)):
    email = session['email']
    store = _load(email)
    policy = store.get('policy') or dict(DEFAULT_POLICY)
    ctx = _cross_system_context(email)
    payload = {
        'proposal_title': 'rotate capital toward resilient compounder sleeve',
        'proposal_scope': 'CAPITAL_REALLOCATION',
        'proposal_summary': 'Committee weighs a governed tilt toward resilient compounding sleeves under favorable executive and memory context.',
        'capital_action': 'TILT',
        'proposed_notional': 180000,
        'conviction_score': 92,
        'scenario_coverage_score': 88,
        'dissent_risk_score': 21,
        'execution_feasibility_score': 90,
    }
    evaluation = _evaluate(payload, ctx, policy)
    row = {
        'deliberation_id': f'ccdelib-{_now_ts()}',
        'created_at': _now_iso(),
        'proposal_title': payload['proposal_title'],
        'proposal_scope': payload['proposal_scope'],
        'proposal_summary': payload['proposal_summary'],
        'capital_action': payload['capital_action'],
        'inputs': payload,
        'context': ctx,
        'evaluation': evaluation,
    }
    _append(store, 'deliberations', row, policy.get('retain_cycles', 180))
    _append(store, 'committee_book', {
        'created_at': row['created_at'],
        'proposal_title': row['proposal_title'],
        'posture': evaluation.get('posture'),
        'committee_band': evaluation.get('committee_band'),
        'action_band': evaluation.get('action_band'),
    }, policy.get('retain_cycles', 180))
    store['last_context'] = ctx
    store['latest_deliberation'] = row
    store['latest_vote'] = {
        'vote_id': f'ccvote-{_now_ts()}-demo',
        'created_at': _now_iso(),
        'deliberation_id': row['deliberation_id'],
        'vote': 'APPROVE' if evaluation.get('posture') in ('APPROVED', 'OPERATOR_REVIEW') else 'DEFER',
        'voter_role': 'CHAIR',
        'commentary': 'Demo committee vote recorded from the current governed context.',
    }
    _append(store, 'votes', store['latest_vote'], policy.get('retain_cycles', 180))
    if evaluation.get('blockers'):
        _append(store, 'alerts', {
            'created_at': row['created_at'],
            'proposal_title': row['proposal_title'],
            'posture': evaluation.get('posture'),
            'blockers': evaluation.get('blockers'),
        }, policy.get('retain_cycles', 180))
    _save(email, store)
    return _summary_for_email(email)
