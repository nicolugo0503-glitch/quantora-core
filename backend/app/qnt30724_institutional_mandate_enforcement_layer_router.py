from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=['institutional-mandate-enforcement-layer'])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / 'backend' / 'artifacts'
ENGINE_DIR = ARTIFACTS_DIR / 'institutional_mandate_enforcement_layer'
DEFAULT_POLICY = {
    'retain_cycles': 180,
    'minimum_mandate_score': 88.0,
    'require_operator_clear': True,
    'require_release_clear': True,
    'require_safety_clear': True,
    'require_fund_admin_clear': True,
    'require_recovery_clear': True,
    'require_charter_clear': True,
    'require_policy_clear': True,
    'require_committee_clear': True,
    'enforce_jurisdiction_alignment': True,
    'enforce_investor_restriction_alignment': True,
    'max_mandate_breach_tolerance': 0,
    'operator_review_notional_threshold': 500000.0,
    'max_concentration_pct': 0.22,
    'min_control_coverage_pct': 0.90,
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


def _liquidity():
    from backend.app import qnt30709_liquidity_intelligence_system_router as liquidity
    return liquidity


def _regime():
    from backend.app import qnt30710_market_regime_intelligence_system_router as regime
    return regime


def _defense():
    from backend.app import qnt30712_defensive_systems_command_layer_router as defense
    return defense


def _allocation_governance():
    from backend.app import qnt30713_autonomous_allocation_governance_layer_router as allocation_governance
    return allocation_governance


def _executive():
    from backend.app import qnt30718_executive_ai_command_layer_router as executive
    return executive


def _memory():
    from backend.app import qnt30719_executive_decision_memory_layer_router as memory
    return memory


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
            'mandate_runs': [],
            'alerts': [],
            'mandate_book': [],
            'latest_mandate_run': None,
            'last_context': {},
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
    liquidity = _liquidity()._summary_for_email(email)
    regime = _regime()._summary_for_email(email)
    defense = _defense()._summary_for_email(email)
    allocation = _allocation_governance()._summary_for_email(email)
    executive = _executive()._summary_for_email(email)
    memory = _memory()._summary_for_email(email)
    committee = _committee()._summary_for_email(email)
    arbitration = _arbitration()._summary_for_email(email)
    policy_layer = _policy_layer()._summary_for_email(email)
    charter_layer = _charter_layer()._summary_for_email(email)
    return {
        'captured_at': _now_iso(),
        'operator': (operator.get('operator_console_status') or {}),
        'release': (release.get('release_control_status') or {}),
        'safety': (safety.get('safety_layer_status') or {}),
        'fund_admin': (fund_admin.get('fund_admin_status') or {}),
        'forensic': (forensic.get('forensic_status') or {}),
        'recovery': (recovery.get('recovery_status') or {}),
        'liquidity': (liquidity.get('liquidity_status') or {}),
        'regime': (regime.get('market_regime_status') or {}),
        'defense': (defense.get('defensive_command_status') or {}),
        'allocation_governance': (allocation.get('allocation_governance_status') or {}),
        'executive': (executive.get('executive_command_status') or {}),
        'memory': (memory.get('executive_decision_memory_layer_status') or {}),
        'committee': (committee.get('capital_committee_status') or {}),
        'arbitration': (arbitration.get('executive_scenario_arbitration_layer_status') or {}),
        'allocation_policy': (policy_layer.get('executive_capital_allocation_policy_layer_status') or {}),
        'execution_charter': (charter_layer.get('institutional_allocation_execution_charter_layer_status') or {}),
    }


def _score_mandate(payload: dict, ctx: dict, policy: dict) -> dict:
    proposed_notional = float(payload.get('proposed_notional') or 0)
    concentration_pct = float(payload.get('concentration_pct') or 0)
    control_coverage_pct = float(payload.get('control_coverage_pct') or 0)
    mandate_breach_count = int(payload.get('mandate_breach_count') or 0)
    jurisdiction_clear = bool(payload.get('jurisdiction_clear', True))
    investor_restriction_clear = bool(payload.get('investor_restriction_clear', True))
    leverage_profile = str(payload.get('leverage_profile') or 'MODERATE').upper()

    blockers = []
    flags = []
    score = 100.0

    if mandate_breach_count > int(policy.get('max_mandate_breach_tolerance', 0)):
        blockers.append('MANDATE_BREACH_DETECTED')
        score -= 20
    if concentration_pct > float(policy.get('max_concentration_pct', 0.22)):
        blockers.append('CONCENTRATION_EXCEEDS_MANDATE')
        score -= 16
    if control_coverage_pct < float(policy.get('min_control_coverage_pct', 0.90)):
        blockers.append('CONTROL_COVERAGE_INSUFFICIENT')
        score -= 16
    if bool(policy.get('enforce_jurisdiction_alignment', True)) and not jurisdiction_clear:
        blockers.append('JURISDICTION_NOT_CLEAR')
        score -= 18
    if bool(policy.get('enforce_investor_restriction_alignment', True)) and not investor_restriction_clear:
        blockers.append('INVESTOR_RESTRICTION_MISMATCH')
        score -= 18
    if leverage_profile in {'HIGH', 'AGGRESSIVE'}:
        flags.append('LEVERAGE_PROFILE_ELEVATED')
        score -= 8

    if str(ctx['operator'].get('posture')).upper() not in {'CLEAR', 'READY', 'ACTIVE'}:
        flags.append('OPERATOR_NOT_CLEAR')
        score -= 8
    if not bool(ctx['release'].get('can_deploy', True)):
        blockers.append('RELEASE_NOT_CLEAR')
        score -= 10
    if str(ctx['safety'].get('posture')).upper() in {'BLOCKED', 'LOCKED'} or bool(ctx['safety'].get('kill_switch')):
        blockers.append('SAFETY_BLOCKED')
        score -= 20
    if str(ctx['fund_admin'].get('reconciliation_status')).upper() not in {'CLEAN', 'BALANCED', 'READY'}:
        flags.append('FUND_ADMIN_RECON_PENDING')
        score -= 8
    if str(ctx['forensic'].get('posture')).upper() in {'BLOCKED', 'CRITICAL'}:
        blockers.append('FORENSIC_BLOCKED')
        score -= 10
    if bool(ctx['recovery'].get('safe_mode')):
        blockers.append('RECOVERY_SAFE_MODE')
        score -= 18
    if not bool(ctx['liquidity'].get('ready', True)):
        blockers.append('LIQUIDITY_NOT_READY')
        score -= 12
    if str(ctx['regime'].get('posture')).upper() in {'HOSTILE', 'RISK_OFF', 'BLOCKED'}:
        flags.append('REGIME_UNFAVORABLE')
        score -= 8
    if str(ctx['defense'].get('posture')).upper() in {'BLOCKED', 'DEFEND'}:
        flags.append('DEFENSE_ACTIVE')
        score -= 10
    if str(ctx['allocation_governance'].get('posture')).upper() in {'BLOCKED', 'OPERATOR_REVIEW'}:
        flags.append('ALLOCATION_GOVERNANCE_REVIEW')
        score -= 8
    if str(ctx['executive'].get('posture')).upper() in {'BLOCKED'}:
        blockers.append('EXECUTIVE_BLOCKED')
        score -= 10
    if str(ctx['memory'].get('posture')).upper() in {'UNTRUSTED', 'BLOCKED'}:
        flags.append('MEMORY_NOT_TRUSTED')
        score -= 6
    if str(ctx['committee'].get('posture')).upper() in {'BLOCKED', 'OPERATOR_REVIEW'}:
        flags.append('COMMITTEE_REVIEW')
        score -= 6
    if str(ctx['arbitration'].get('posture')).upper() in {'BLOCKED', 'WATCH', 'OPERATOR_REVIEW'}:
        flags.append('ARBITRATION_NOT_CLEAR')
        score -= 8
    if str(ctx['allocation_policy'].get('posture')).upper() in {'BLOCKED', 'WATCH'}:
        blockers.append('ALLOCATION_POLICY_NOT_CLEAR')
        score -= 12
    if str(ctx['execution_charter'].get('posture')).upper() not in {'APPROVED'}:
        blockers.append('EXECUTION_CHARTER_NOT_APPROVED')
        score -= 16

    operator_review_required = proposed_notional >= float(policy.get('operator_review_notional_threshold', 500000.0)) or len(blockers) > 0 or len(flags) >= 4

    if blockers:
        posture = 'BLOCKED'
        mandate_band = 'DO_NOT_AUTHORIZE'
    elif score >= float(policy.get('minimum_mandate_score', 88.0)) and not operator_review_required:
        posture = 'APPROVED'
        mandate_band = 'MANDATE_ENFORCED'
    elif score >= float(policy.get('minimum_mandate_score', 88.0)):
        posture = 'OPERATOR_REVIEW'
        mandate_band = 'SUPERVISED_ENFORCEMENT'
    else:
        posture = 'WATCH'
        mandate_band = 'MANDATE_HOLD'

    return {
        'score': round(max(score, 0.0), 2),
        'posture': posture,
        'mandate_band': mandate_band,
        'operator_review_required': operator_review_required,
        'blockers': blockers,
        'flags': flags,
        'computed': {
            'proposed_notional': round(proposed_notional, 2),
            'concentration_pct': round(concentration_pct, 4),
            'control_coverage_pct': round(control_coverage_pct, 4),
            'mandate_breach_count': mandate_breach_count,
            'jurisdiction_clear': jurisdiction_clear,
            'investor_restriction_clear': investor_restriction_clear,
            'leverage_profile': leverage_profile,
        },
    }


def _summary_for_email(email: str) -> dict:
    store = _load(email)
    latest = store.get('latest_mandate_run') or {}
    status = {
        'posture': ((latest.get('evaluation') or {}).get('posture') if latest else 'UNINITIALIZED') or 'UNINITIALIZED',
        'latest_score': ((latest.get('evaluation') or {}).get('score') if latest else None),
        'mandate_band': ((latest.get('evaluation') or {}).get('mandate_band') if latest else None),
        'operator_review_required': ((latest.get('evaluation') or {}).get('operator_review_required') if latest else False),
        'mandate_run_count': len(store.get('mandate_runs') or []),
        'alert_count': len(store.get('alerts') or []),
    }
    return {
        'institutional_mandate_enforcement_layer_status': status,
        'latest_mandate_run': store.get('latest_mandate_run'),
        'mandate_runs': (store.get('mandate_runs') or [])[:10],
        'alerts': (store.get('alerts') or [])[:10],
        'mandate_book': (store.get('mandate_book') or [])[:10],
        'policy': store.get('policy') or dict(DEFAULT_POLICY),
        'last_context': store.get('last_context') or {},
    }


@router.get('/api/institutional-mandate-enforcement-layer/summary')
def summary(user=Depends(_require_user)):
    return _summary_for_email(user['email'])


@router.post('/api/institutional-mandate-enforcement-layer/evaluate')
def evaluate(payload: dict = Body(default={}), user=Depends(_require_user)):
    email = user['email']
    store = _load(email)
    policy = store.get('policy') or dict(DEFAULT_POLICY)
    ctx = _cross_system_context(email)
    payload = {
        'title': payload.get('title') or 'Institutional mandate enforcement cycle',
        'summary': payload.get('summary') or 'Enforce mandate constraints against the approved execution charter.',
        'proposed_notional': float(payload.get('proposed_notional') or 420000),
        'concentration_pct': float(payload.get('concentration_pct') or 0.18),
        'control_coverage_pct': float(payload.get('control_coverage_pct') or 0.94),
        'mandate_breach_count': int(payload.get('mandate_breach_count') or 0),
        'jurisdiction_clear': bool(payload.get('jurisdiction_clear', True)),
        'investor_restriction_clear': bool(payload.get('investor_restriction_clear', True)),
        'leverage_profile': payload.get('leverage_profile') or 'MODERATE',
    }
    evaluation = _score_mandate(payload, ctx, policy)
    row = {
        'mandate_run_id': f'mandate-enforcement-{_now_ts()}',
        'created_at': _now_iso(),
        'title': payload['title'],
        'summary': payload['summary'],
        'payload': payload,
        'context': ctx,
        'evaluation': evaluation,
    }
    _append(store, 'mandate_runs', row, policy.get('retain_cycles', 180))
    _append(store, 'mandate_book', {
        'created_at': row['created_at'],
        'title': row['title'],
        'posture': evaluation['posture'],
        'mandate_band': evaluation['mandate_band'],
        'score': evaluation['score'],
    }, policy.get('retain_cycles', 180))
    if evaluation['blockers'] or evaluation['posture'] in {'WATCH', 'OPERATOR_REVIEW', 'BLOCKED'}:
        _append(store, 'alerts', {
            'created_at': row['created_at'],
            'title': row['title'],
            'posture': evaluation['posture'],
            'blockers': evaluation['blockers'],
            'flags': evaluation['flags'],
        }, policy.get('retain_cycles', 180))
    store['latest_mandate_run'] = row
    store['last_context'] = ctx
    _save(email, store)
    return _summary_for_email(email)


@router.post('/api/institutional-mandate-enforcement-layer/policy')
def update_policy(payload: dict = Body(default={}), user=Depends(_require_user)):
    email = user['email']
    store = _load(email)
    current = dict(DEFAULT_POLICY)
    current.update(store.get('policy') or {})
    for key in DEFAULT_POLICY.keys():
        if key in payload:
            current[key] = payload[key]
    store['policy'] = current
    _save(email, store)
    return _summary_for_email(email)


@router.post('/api/institutional-mandate-enforcement-layer/bootstrap-demo')
def bootstrap_demo(user=Depends(_require_user)):
    email = user['email']
    store = _load(email)
    if not store.get('mandate_runs'):
        payload = {
            'title': 'enforce institutional mandate constraints',
            'summary': 'Confirm the approved execution charter satisfies institutional mandate rules.',
            'proposed_notional': 420000,
            'concentration_pct': 0.18,
            'control_coverage_pct': 0.94,
            'mandate_breach_count': 0,
            'jurisdiction_clear': True,
            'investor_restriction_clear': True,
            'leverage_profile': 'MODERATE',
        }
        return evaluate(payload, user)
    return _summary_for_email(email)
