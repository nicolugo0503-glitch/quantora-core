from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=['institutional-allocation-execution-charter-layer'])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / 'backend' / 'artifacts'
ENGINE_DIR = ARTIFACTS_DIR / 'institutional_allocation_execution_charter_layer'
DEFAULT_POLICY = {
    'retain_cycles': 180,
    'minimum_charter_score': 86.0,
    'require_operator_clear': True,
    'require_release_clear': True,
    'require_safety_clear': True,
    'require_fund_admin_clear': True,
    'require_recovery_clear': True,
    'require_policy_clear': True,
    'require_arbitration_clear': True,
    'require_committee_clear': True,
    'max_notional_per_wave': 250000.0,
    'max_execution_waves': 4,
    'min_liquidity_buffer_pct': 0.10,
    'max_crossing_cost_bps': 35.0,
    'operator_review_notional_threshold': 400000.0,
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


def _rotation():
    from backend.app import qnt30711_capital_rotation_command_system_router as rotation
    return rotation


def _defense():
    from backend.app import qnt30712_defensive_systems_command_layer_router as defense
    return defense


def _allocation_governance():
    from backend.app import qnt30713_autonomous_allocation_governance_layer_router as allocation_governance
    return allocation_governance


def _executive():
    from backend.app import qnt30718_executive_ai_command_layer_router as executive
    return executive


def _committee():
    from backend.app import qnt30720_capital_committee_deliberation_layer_router as committee
    return committee


def _arbitration():
    from backend.app import qnt30721_executive_scenario_arbitration_layer_router as arbitration
    return arbitration


def _policy_layer():
    from backend.app import qnt30722_executive_capital_allocation_policy_layer_router as policy_layer
    return policy_layer


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
            'charter_runs': [],
            'alerts': [],
            'charter_book': [],
            'latest_charter_run': None,
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
    rotation = _rotation()._summary_for_email(email)
    defense = _defense()._summary_for_email(email)
    allocation = _allocation_governance()._summary_for_email(email)
    executive = _executive()._summary_for_email(email)
    committee = _committee()._summary_for_email(email)
    arbitration = _arbitration()._summary_for_email(email)
    policy_layer = _policy_layer()._summary_for_email(email)
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
        'rotation': (rotation.get('capital_rotation_status') or {}),
        'defense': (defense.get('defensive_command_status') or {}),
        'allocation_governance': (allocation.get('allocation_governance_status') or {}),
        'executive': (executive.get('executive_command_status') or {}),
        'committee': (committee.get('capital_committee_status') or {}),
        'arbitration': (arbitration.get('executive_scenario_arbitration_layer_status') or {}),
        'allocation_policy': (policy_layer.get('executive_capital_allocation_policy_layer_status') or {}),
    }


def _score_charter(payload: dict, ctx: dict, policy: dict) -> dict:
    proposed_notional = float(payload.get('proposed_notional') or 0)
    execution_waves = int(payload.get('execution_waves') or 1)
    liquidity_buffer_pct = float(payload.get('liquidity_buffer_pct') or 0)
    estimated_crossing_cost_bps = float(payload.get('estimated_crossing_cost_bps') or 0)
    reserve_hold_pct = float(payload.get('reserve_hold_pct') or 0)

    blockers = []
    flags = []
    score = 100.0

    if proposed_notional > float(policy.get('max_notional_per_wave', 250000.0)) * max(execution_waves, 1):
        blockers.append('NOTIONAL_EXCEEDS_WAVE_CAPACITY')
        score -= 16
    if execution_waves > int(policy.get('max_execution_waves', 4)):
        blockers.append('TOO_MANY_EXECUTION_WAVES')
        score -= 14
    if liquidity_buffer_pct < float(policy.get('min_liquidity_buffer_pct', 0.10)):
        blockers.append('LIQUIDITY_BUFFER_TOO_LOW')
        score -= 14
    if estimated_crossing_cost_bps > float(policy.get('max_crossing_cost_bps', 35.0)):
        flags.append('CROSSING_COST_ELEVATED')
        score -= 10
    if reserve_hold_pct < 0.05:
        flags.append('RESERVE_HOLD_THIN')
        score -= 6

    if str(ctx['operator'].get('posture')).upper() not in {'CLEAR', 'READY', 'ACTIVE'}:
        flags.append('OPERATOR_NOT_CLEAR')
        score -= 8
    if not bool(ctx['release'].get('can_deploy', True)):
        blockers.append('RELEASE_NOT_CLEAR')
        score -= 10
    if str(ctx['safety'].get('posture')).upper() in {'BLOCKED', 'LOCKED'} or bool(ctx['safety'].get('kill_switch')):
        blockers.append('SAFETY_BLOCKED')
        score -= 25
    if str(ctx['fund_admin'].get('reconciliation_status')).upper() not in {'CLEAN', 'BALANCED', 'READY'}:
        flags.append('FUND_ADMIN_RECON_PENDING')
        score -= 8
    if str(ctx['forensic'].get('posture')).upper() in {'BLOCKED', 'CRITICAL'}:
        blockers.append('FORENSIC_BLOCKED')
        score -= 12
    if bool(ctx['recovery'].get('safe_mode')):
        blockers.append('RECOVERY_SAFE_MODE')
        score -= 20
    if not bool(ctx['liquidity'].get('ready', True)):
        blockers.append('LIQUIDITY_NOT_READY')
        score -= 14
    if str(ctx['regime'].get('posture')).upper() in {'HOSTILE', 'RISK_OFF', 'BLOCKED'}:
        flags.append('REGIME_UNFAVORABLE')
        score -= 10
    if str(ctx['rotation'].get('posture')).upper() in {'BLOCKED', 'OPERATOR_REVIEW'}:
        flags.append('ROTATION_REVIEW')
        score -= 6
    if str(ctx['defense'].get('posture')).upper() in {'BLOCKED', 'DEFEND'}:
        flags.append('DEFENSE_ACTIVE')
        score -= 10
    if str(ctx['allocation_governance'].get('posture')).upper() in {'BLOCKED', 'OPERATOR_REVIEW'}:
        flags.append('ALLOCATION_GOVERNANCE_REVIEW')
        score -= 8
    if str(ctx['executive'].get('posture')).upper() in {'BLOCKED'}:
        blockers.append('EXECUTIVE_BLOCKED')
        score -= 12
    if str(ctx['committee'].get('posture')).upper() in {'BLOCKED', 'OPERATOR_REVIEW'}:
        flags.append('COMMITTEE_REVIEW')
        score -= 6
    if str(ctx['arbitration'].get('posture')).upper() in {'BLOCKED', 'WATCH', 'OPERATOR_REVIEW'}:
        flags.append('ARBITRATION_NOT_CLEAR')
        score -= 10
    if str(ctx['allocation_policy'].get('posture')).upper() in {'BLOCKED', 'WATCH'}:
        blockers.append('ALLOCATION_POLICY_NOT_CLEAR')
        score -= 16

    operator_review_required = proposed_notional >= float(policy.get('operator_review_notional_threshold', 400000.0)) or len(blockers) > 0 or len(flags) >= 4

    if blockers:
        posture = 'BLOCKED'
        execution_band = 'DO_NOT_EXECUTE'
    elif score >= float(policy.get('minimum_charter_score', 86.0)) and not operator_review_required:
        posture = 'APPROVED'
        execution_band = 'CHARTER_EXECUTE'
    elif score >= float(policy.get('minimum_charter_score', 86.0)):
        posture = 'OPERATOR_REVIEW'
        execution_band = 'STAGED_EXECUTION'
    else:
        posture = 'WATCH'
        execution_band = 'HOLD_CHARTER'

    return {
        'score': round(max(score, 0.0), 2),
        'posture': posture,
        'execution_band': execution_band,
        'operator_review_required': operator_review_required,
        'blockers': blockers,
        'flags': flags,
        'computed': {
            'proposed_notional': round(proposed_notional, 2),
            'execution_waves': execution_waves,
            'liquidity_buffer_pct': round(liquidity_buffer_pct, 4),
            'estimated_crossing_cost_bps': round(estimated_crossing_cost_bps, 2),
            'reserve_hold_pct': round(reserve_hold_pct, 4),
        },
    }


def _summary_for_email(email: str) -> dict:
    store = _load(email)
    latest = store.get('latest_charter_run') or {}
    status = {
        'posture': ((latest.get('evaluation') or {}).get('posture') if latest else 'UNINITIALIZED') or 'UNINITIALIZED',
        'latest_score': ((latest.get('evaluation') or {}).get('score') if latest else None),
        'execution_band': ((latest.get('evaluation') or {}).get('execution_band') if latest else None),
        'operator_review_required': ((latest.get('evaluation') or {}).get('operator_review_required') if latest else False),
        'charter_run_count': len(store.get('charter_runs') or []),
        'alert_count': len(store.get('alerts') or []),
    }
    return {
        'institutional_allocation_execution_charter_layer_status': status,
        'latest_charter_run': store.get('latest_charter_run'),
        'charter_runs': store.get('charter_runs')[:10],
        'alerts': store.get('alerts')[:10],
        'charter_book': store.get('charter_book')[:10],
        'policy': store.get('policy') or dict(DEFAULT_POLICY),
        'last_context': store.get('last_context') or {},
    }


@router.get('/api/institutional-allocation-execution-charter-layer/summary')
def summary(user=Depends(_require_user)):
    return _summary_for_email(user['email'])


@router.post('/api/institutional-allocation-execution-charter-layer/evaluate')
def evaluate(payload: dict = Body(default={}), user=Depends(_require_user)):
    email = user['email']
    store = _load(email)
    policy = store.get('policy') or dict(DEFAULT_POLICY)
    ctx = _cross_system_context(email)
    payload = {
        'title': payload.get('title') or 'Institutional allocation execution charter cycle',
        'summary': payload.get('summary') or 'Authorize governed staged execution of the approved allocation policy.',
        'proposed_notional': float(payload.get('proposed_notional') or 420000),
        'execution_waves': int(payload.get('execution_waves') or 3),
        'liquidity_buffer_pct': float(payload.get('liquidity_buffer_pct') or 0.14),
        'estimated_crossing_cost_bps': float(payload.get('estimated_crossing_cost_bps') or 18.0),
        'reserve_hold_pct': float(payload.get('reserve_hold_pct') or 0.11),
        'execution_style': payload.get('execution_style') or 'STAGED_LIMITED_ROTATION',
    }
    evaluation = _score_charter(payload, ctx, policy)
    row = {
        'charter_run_id': f'alloc-charter-{_now_ts()}',
        'created_at': _now_iso(),
        'title': payload['title'],
        'summary': payload['summary'],
        'payload': payload,
        'context': ctx,
        'evaluation': evaluation,
    }
    _append(store, 'charter_runs', row, policy.get('retain_cycles', 180))
    _append(store, 'charter_book', {
        'created_at': row['created_at'],
        'title': row['title'],
        'posture': evaluation['posture'],
        'execution_band': evaluation['execution_band'],
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
    store['latest_charter_run'] = row
    store['last_context'] = ctx
    _save(email, store)
    return _summary_for_email(email)


@router.post('/api/institutional-allocation-execution-charter-layer/policy')
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


@router.post('/api/institutional-allocation-execution-charter-layer/bootstrap-demo')
def bootstrap_demo(user=Depends(_require_user)):
    email = user['email']
    store = _load(email)
    if not store.get('charter_runs'):
        payload = {
            'title': 'charter governed staged allocation execution',
            'summary': 'Authorize a staged execution wave plan after allocation policy approval.',
            'proposed_notional': 420000,
            'execution_waves': 3,
            'liquidity_buffer_pct': 0.14,
            'estimated_crossing_cost_bps': 18.0,
            'reserve_hold_pct': 0.11,
            'execution_style': 'STAGED_LIMITED_ROTATION',
        }
        return evaluate(payload, user)
    return _summary_for_email(email)
