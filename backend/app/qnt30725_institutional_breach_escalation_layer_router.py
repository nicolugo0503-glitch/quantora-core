from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=['institutional-breach-escalation-layer'])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / 'backend' / 'artifacts'
ENGINE_DIR = ARTIFACTS_DIR / 'institutional_breach_escalation_layer'
DEFAULT_POLICY = {
    'retain_cycles': 180,
    'minimum_breach_score': 90.0,
    'require_operator_clear': True,
    'require_release_clear': True,
    'require_safety_clear': True,
    'require_recovery_clear': True,
    'require_mandate_clear': True,
    'critical_breach_threshold': 2,
    'material_breach_threshold': 1,
    'operator_escalation_notional_threshold': 500000.0,
    'require_freeze_on_critical': True,
    'require_forensic_case_on_critical': True,
    'max_open_critical_incidents': 0,
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


def _forensic():
    from backend.app import qnt30706_forensic_audit_system_router as forensic
    return forensic


def _recovery():
    from backend.app import qnt30707_recovery_system_router as recovery
    return recovery


def _committee():
    from backend.app import qnt30720_capital_committee_deliberation_layer_router as committee
    return committee


def _arbitration():
    from backend.app import qnt30721_executive_scenario_arbitration_layer_router as arbitration
    return arbitration


def _policy_layer():
    from backend.app import qnt30722_executive_capital_allocation_policy_layer_router as policy_layer
    return policy_layer


def _charter_layer():
    from backend.app import qnt30723_institutional_allocation_execution_charter_layer_router as charter_layer
    return charter_layer


def _mandate_layer():
    from backend.app import qnt30724_institutional_mandate_enforcement_layer_router as mandate_layer
    return mandate_layer


def _safe(v: str) -> str:
    return hashlib.sha256((v or '').strip().lower().encode('utf-8')).hexdigest()[:24]


def _path(email: str) -> Path:
    ENGINE_DIR.mkdir(parents=True, exist_ok=True)
    return ENGINE_DIR / f'{_safe(email)}.json'


def _require_user():
    return _mu()._require_session()


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
            'breach_runs': [],
            'alerts': [],
            'breach_book': [],
            'latest_breach_run': None,
            'last_context': {},
        }
        path.write_text(json.dumps(data, indent=2), encoding='utf-8')
        return data
    return json.loads(path.read_text(encoding='utf-8'))


def _save(email: str, data: dict):
    _path(email).write_text(json.dumps(data, indent=2), encoding='utf-8')


def _summary_for_email(email: str) -> dict:
    s = _load(email)
    latest = s.get('latest_breach_run') or {}
    return {
        'institutional_breach_escalation_layer_status': {
            'posture': latest.get('posture', 'UNINITIALIZED'),
            'latest_score': latest.get('breach_score'),
            'breach_band': latest.get('breach_band', 'UNSET'),
            'breach_run_count': len(s.get('breach_runs') or []),
            'alert_count': len(s.get('alerts') or []),
            'requires_freeze': bool(latest.get('requires_freeze', False)),
        },
        'latest_breach_run': latest,
        'alerts': s.get('alerts') or [],
        'policy': s.get('policy') or dict(DEFAULT_POLICY),
        'last_context': s.get('last_context') or {},
    }


def _cross_system_context(email: str) -> dict:
    operator = _operator()._summary_for_email(email)
    release = _release()._summary_for_email(email)
    safety = _safety()._summary_for_email(email)
    forensic = _forensic()._summary_for_email(email)
    recovery = _recovery()._summary_for_email(email)
    committee = _committee()._summary_for_email(email)
    arbitration = _arbitration()._summary_for_email(email)
    policy_layer = _policy_layer()._summary_for_email(email)
    charter_layer = _charter_layer()._summary_for_email(email)
    mandate_layer = _mandate_layer()._summary_for_email(email)
    return {
        'captured_at': _now_iso(),
        'operator': operator.get('operator_console_status') or {},
        'release': release.get('release_control_status') or {},
        'safety': safety.get('safety_layer_status') or {},
        'forensic': forensic.get('forensic_status') or {},
        'recovery': recovery.get('recovery_status') or {},
        'committee': committee.get('capital_committee_status') or {},
        'arbitration': arbitration.get('executive_scenario_arbitration_layer_status') or {},
        'allocation_policy': policy_layer.get('executive_capital_allocation_policy_layer_status') or {},
        'execution_charter': charter_layer.get('institutional_allocation_execution_charter_layer_status') or {},
        'mandate': mandate_layer.get('institutional_mandate_enforcement_layer_status') or {},
    }


def _score_breach(payload: dict, ctx: dict, policy: dict) -> dict:
    critical_count = int(payload.get('critical_breach_count') or 0)
    material_count = int(payload.get('material_breach_count') or 0)
    unresolved_critical = int(payload.get('open_critical_incidents') or 0)
    proposed_notional = float(payload.get('proposed_notional') or 0)
    breach_type = str(payload.get('breach_type') or 'CONTROL').upper()
    remediation_ready = bool(payload.get('remediation_ready', False))
    containment_ready = bool(payload.get('containment_ready', False))
    investor_notification_required = bool(payload.get('investor_notification_required', False))

    score = 100.0
    blockers = []
    flags = []

    if critical_count >= int(policy.get('critical_breach_threshold', 2)):
        blockers.append('CRITICAL_BREACH_THRESHOLD_MET')
        score -= 24
    if material_count >= int(policy.get('material_breach_threshold', 1)):
        flags.append('MATERIAL_BREACH_PRESENT')
        score -= 12
    if unresolved_critical > int(policy.get('max_open_critical_incidents', 0)):
        blockers.append('OPEN_CRITICAL_INCIDENTS_PRESENT')
        score -= 18
    if not remediation_ready:
        blockers.append('REMEDIATION_PLAN_NOT_READY')
        score -= 14
    if not containment_ready:
        blockers.append('CONTAINMENT_NOT_READY')
        score -= 14
    if breach_type in {'MANDATE', 'REGULATORY', 'INVESTOR'}:
        flags.append('HIGH_SENSITIVITY_BREACH_TYPE')
        score -= 8
    if investor_notification_required:
        flags.append('INVESTOR_NOTIFICATION_REQUIRED')
        score -= 5

    if str(ctx['mandate'].get('posture')).upper() not in {'APPROVED', 'ENFORCED', 'CLEAR'}:
        blockers.append('MANDATE_LAYER_NOT_CLEAR')
        score -= 12
    if not bool(ctx['release'].get('can_deploy', True)):
        blockers.append('RELEASE_NOT_CLEAR')
        score -= 8
    if str(ctx['safety'].get('posture')).upper() not in {'APPROVED', 'READY', 'CLEAR'}:
        flags.append('SAFETY_POSTURE_NOT_CLEAR')
        score -= 8
    if str(ctx['recovery'].get('posture')).upper() not in {'READY', 'RECOVERED', 'CLEAR'}:
        blockers.append('RECOVERY_NOT_CLEAR')
        score -= 10
    if str(ctx['forensic'].get('posture')).upper() not in {'READY', 'CLEAR', 'CLOSED'}:
        flags.append('FORENSIC_REVIEW_OPEN')
        score -= 6
    if str(ctx['operator'].get('posture')).upper() not in {'CLEAR', 'READY', 'ACTIVE'}:
        flags.append('OPERATOR_NOT_CLEAR')
        score -= 6
    if str(ctx['execution_charter'].get('posture')).upper() not in {'APPROVED', 'CLEAR', 'AUTHORIZED'}:
        flags.append('EXECUTION_CHARTER_NOT_CLEAR')
        score -= 5
    if str(ctx['allocation_policy'].get('posture')).upper() not in {'APPROVED', 'CLEAR'}:
        flags.append('ALLOCATION_POLICY_NOT_CLEAR')
        score -= 5

    requires_freeze = bool(policy.get('require_freeze_on_critical', True)) and critical_count > 0
    operator_escalation_required = proposed_notional >= float(policy.get('operator_escalation_notional_threshold', 500000.0)) or critical_count > 0
    forensic_case_required = bool(policy.get('require_forensic_case_on_critical', True)) and critical_count > 0

    if blockers:
        posture = 'ESCALATE_NOW'
        band = 'CRITICAL'
    elif score >= max(float(policy.get('minimum_breach_score', 90.0)), 90.0):
        posture = 'CONTAINED'
        band = 'CONTROLLED'
    elif score >= 75:
        posture = 'OPERATOR_REVIEW'
        band = 'MATERIAL'
    else:
        posture = 'ESCALATE_NOW'
        band = 'CRITICAL'

    return {
        'breach_score': round(max(score, 0.0), 2),
        'posture': posture,
        'breach_band': band,
        'blockers': blockers,
        'flags': flags,
        'requires_freeze': requires_freeze,
        'operator_escalation_required': operator_escalation_required,
        'forensic_case_required': forensic_case_required,
    }


@router.get('/api/institutional-breach-escalation-layer/summary')
def summary(user=Depends(_require_user)):
    return _summary_for_email(user['email'])


@router.post('/api/institutional-breach-escalation-layer/policy')
def update_policy(payload: dict = Body(...), user=Depends(_require_user)):
    email = user['email']
    store = _load(email)
    store['policy'] = {**dict(DEFAULT_POLICY), **(store.get('policy') or {}), **(payload or {})}
    _save(email, store)
    return _summary_for_email(email)


@router.post('/api/institutional-breach-escalation-layer/evaluate')
def evaluate(payload: dict = Body(...), user=Depends(_require_user)):
    email = user['email']
    store = _load(email)
    policy = store.get('policy') or dict(DEFAULT_POLICY)
    ctx = _cross_system_context(email)
    result = _score_breach(payload or {}, ctx, policy)
    row = {
        'id': f"breach_{int(time.time()*1000)}",
        'captured_at': _now_iso(),
        'title': payload.get('title') or 'institutional breach escalation review',
        'summary': payload.get('summary') or 'Review breach materiality, containment, and escalation posture.',
        'payload': payload,
        **result,
    }
    store['latest_breach_run'] = row
    store['last_context'] = ctx
    _append(store, 'breach_runs', row, int(policy.get('retain_cycles', 180)))
    _append(store, 'breach_book', {
        'id': row['id'], 'captured_at': row['captured_at'], 'posture': row['posture'], 'breach_band': row['breach_band']
    }, int(policy.get('retain_cycles', 180)))
    if row['blockers'] or row['flags']:
        _append(store, 'alerts', {
            'id': row['id'], 'captured_at': row['captured_at'], 'severity': row['breach_band'],
            'blockers': row['blockers'], 'flags': row['flags'], 'requires_freeze': row['requires_freeze']
        }, int(policy.get('retain_cycles', 180)))
    _save(email, store)
    return {'ok': True, **_summary_for_email(email)}


@router.post('/api/institutional-breach-escalation-layer/bootstrap-demo')
def bootstrap_demo(user=Depends(_require_user)):
    payload = {
        'title': 'escalate mandate and control breach cluster',
        'summary': 'Evaluate material and critical breach conditions and determine freeze/escalation posture.',
        'critical_breach_count': 1,
        'material_breach_count': 2,
        'open_critical_incidents': 1,
        'proposed_notional': 650000,
        'breach_type': 'MANDATE',
        'remediation_ready': True,
        'containment_ready': True,
        'investor_notification_required': True,
    }
    return evaluate(payload, user)
