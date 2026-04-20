from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=['executive-capital-allocation-policy-layer'])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / 'backend' / 'artifacts'
ENGINE_DIR = ARTIFACTS_DIR / 'executive_capital_allocation_policy_layer'
DEFAULT_POLICY = {
    'retain_cycles': 180,
    'minimum_policy_score': 85.0,
    'require_operator_clear': True,
    'require_release_clear': True,
    'require_safety_clear': True,
    'require_fund_admin_clear': True,
    'require_forensic_clear': True,
    'require_recovery_clear': True,
    'require_committee_clear': True,
    'require_executive_clear': True,
    'require_arbitration_clear': True,
    'max_single_sleeve_pct': 0.35,
    'max_defensive_override_pct': 0.55,
    'min_cash_buffer_pct': 0.08,
    'operator_review_notional_threshold': 300000.0,
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
            'policy_runs': [],
            'alerts': [],
            'policy_book': [],
            'latest_policy_run': None,
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
    allocation = _allocation_governance()._summary_for_email(email)
    executive = _executive()._summary_for_email(email)
    memory = _memory()._summary_for_email(email)
    committee = _committee()._summary_for_email(email)
    arbitration = _arbitration()._summary_for_email(email)
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
        'allocation_governance': (allocation.get('allocation_governance_status') or {}),
        'executive': (executive.get('executive_command_status') or {}),
        'memory': (memory.get('executive_decision_memory_status') or {}),
        'committee': (committee.get('capital_committee_status') or {}),
        'arbitration': (arbitration.get('executive_scenario_arbitration_layer_status') or {}),
    }


def _policy_score(payload: dict, ctx: dict, policy: dict):
    target_allocations = payload.get('target_allocations') or []
    total_pct = sum(float(x.get('target_pct') or 0) for x in target_allocations)
    max_sleeve = max([float(x.get('target_pct') or 0) for x in target_allocations] or [0])
    cash_buffer = float(payload.get('cash_buffer_pct') or 0)
    defensive_override = float(payload.get('defensive_override_pct') or 0)
    proposed_notional = float(payload.get('proposed_notional') or 0)
    posture_flags = []
    blockers = []
    score = 100.0

    if abs(total_pct - 1.0) > 0.02:
        blockers.append('TARGET_ALLOCATIONS_NOT_BALANCED')
        score -= 20
    if max_sleeve > float(policy.get('max_single_sleeve_pct', 0.35)):
        blockers.append('SLEEVE_CONCENTRATION_BREACH')
        score -= 18
    if defensive_override > float(policy.get('max_defensive_override_pct', 0.55)):
        blockers.append('DEFENSIVE_OVERRIDE_TOO_HIGH')
        score -= 10
    if cash_buffer < float(policy.get('min_cash_buffer_pct', 0.08)):
        blockers.append('CASH_BUFFER_TOO_LOW')
        score -= 14

    if str(ctx['operator'].get('posture')).upper() not in {'CLEAR','READY','ACTIVE'}:
        posture_flags.append('OPERATOR_NOT_CLEAR')
        score -= 8
    if not bool(ctx['release'].get('can_deploy', True)):
        blockers.append('RELEASE_NOT_CLEAR')
        score -= 10
    if str(ctx['safety'].get('posture')).upper() in {'BLOCKED','LOCKED'} or bool(ctx['safety'].get('kill_switch')):
        blockers.append('SAFETY_BLOCKED')
        score -= 25
    if str(ctx['fund_admin'].get('reconciliation_status')).upper() not in {'CLEAN','BALANCED','READY'}:
        posture_flags.append('FUND_ADMIN_RECON_PENDING')
        score -= 8
    if str(ctx['forensic'].get('posture')).upper() in {'BLOCKED','CRITICAL'}:
        blockers.append('FORENSIC_BLOCKED')
        score -= 12
    if bool(ctx['recovery'].get('safe_mode')):
        blockers.append('RECOVERY_SAFE_MODE')
        score -= 20
    if not bool(ctx['liquidity'].get('ready', True)):
        posture_flags.append('LIQUIDITY_NOT_READY')
        score -= 10
    if str(ctx['regime'].get('posture')).upper() in {'HOSTILE','RISK_OFF','BLOCKED'}:
        posture_flags.append('HOSTILE_REGIME')
        score -= 10
    if str(ctx['allocation_governance'].get('posture')).upper() in {'BLOCKED','OPERATOR_REVIEW'}:
        posture_flags.append('ALLOCATION_GOVERNANCE_REVIEW')
        score -= 8
    if str(ctx['executive'].get('posture')).upper() in {'BLOCKED'}:
        blockers.append('EXECUTIVE_BLOCKED')
        score -= 12
    if str(ctx['committee'].get('posture')).upper() in {'BLOCKED','OPERATOR_REVIEW'}:
        posture_flags.append('COMMITTEE_REVIEW')
        score -= 6
    if str(ctx['arbitration'].get('posture')).upper() in {'BLOCKED','WATCH','OPERATOR_REVIEW'}:
        posture_flags.append('ARBITRATION_NOT_CLEAR')
        score -= 10

    operator_review_required = proposed_notional >= float(policy.get('operator_review_notional_threshold',300000.0)) or len(blockers) > 0 or len(posture_flags) >= 3

    if blockers:
        posture = 'BLOCKED'
        allocation_band = 'DEFEND'
    elif score >= float(policy.get('minimum_policy_score',85.0)) and not operator_review_required:
        posture = 'APPROVED'
        allocation_band = 'ALLOCATE'
    elif score >= float(policy.get('minimum_policy_score',85.0)):
        posture = 'OPERATOR_REVIEW'
        allocation_band = 'TILT'
    else:
        posture = 'WATCH'
        allocation_band = 'HOLD'

    return {
        'score': round(max(score, 0.0), 2),
        'posture': posture,
        'allocation_band': allocation_band,
        'operator_review_required': operator_review_required,
        'blockers': blockers,
        'flags': posture_flags,
        'computed': {
            'total_target_pct': round(total_pct,4),
            'max_single_sleeve_pct': round(max_sleeve,4),
            'cash_buffer_pct': round(cash_buffer,4),
            'defensive_override_pct': round(defensive_override,4),
        }
    }


def _summary_for_email(email: str) -> dict:
    store = _load(email)
    latest = store.get('latest_policy_run') or {}
    status = {
        'posture': ((latest.get('evaluation') or {}).get('posture') if latest else 'UNINITIALIZED') or 'UNINITIALIZED',
        'latest_score': ((latest.get('evaluation') or {}).get('score') if latest else None),
        'allocation_band': ((latest.get('evaluation') or {}).get('allocation_band') if latest else None),
        'operator_review_required': ((latest.get('evaluation') or {}).get('operator_review_required') if latest else False),
        'policy_run_count': len(store.get('policy_runs') or []),
        'alert_count': len(store.get('alerts') or []),
    }
    return {
        'executive_capital_allocation_policy_layer_status': status,
        'latest_policy_run': store.get('latest_policy_run'),
        'policy_runs': store.get('policy_runs')[:10],
        'alerts': store.get('alerts')[:10],
        'policy_book': store.get('policy_book')[:10],
        'policy': store.get('policy') or dict(DEFAULT_POLICY),
        'last_context': store.get('last_context') or {},
    }


@router.get('/api/executive-capital-allocation-policy-layer/summary')
def summary(user=Depends(_require_user)):
    return _summary_for_email(user['email'])


@router.post('/api/executive-capital-allocation-policy-layer/evaluate')
def evaluate(payload: dict = Body(default={}), user=Depends(_require_user)):
    email = user['email']
    store = _load(email)
    policy = store.get('policy') or dict(DEFAULT_POLICY)
    ctx = _cross_system_context(email)
    payload = {
        'title': payload.get('title') or 'Executive capital allocation policy cycle',
        'summary': payload.get('summary') or 'Govern target capital weights across institutional sleeves.',
        'proposed_notional': float(payload.get('proposed_notional') or 320000),
        'cash_buffer_pct': float(payload.get('cash_buffer_pct') or 0.12),
        'defensive_override_pct': float(payload.get('defensive_override_pct') or 0.18),
        'target_allocations': payload.get('target_allocations') or [
            {'sleeve': 'core-compounding', 'target_pct': 0.34},
            {'sleeve': 'tactical-alpha', 'target_pct': 0.24},
            {'sleeve': 'defensive-hedge', 'target_pct': 0.18},
            {'sleeve': 'cash-reserve', 'target_pct': 0.24},
        ],
    }
    evaluation = _policy_score(payload, ctx, policy)
    row = {
        'policy_run_id': f'ecap-policy-{_now_ts()}',
        'created_at': _now_iso(),
        'title': payload['title'],
        'summary': payload['summary'],
        'payload': payload,
        'context': ctx,
        'evaluation': evaluation,
    }
    _append(store, 'policy_runs', row, policy.get('retain_cycles', 180))
    _append(store, 'policy_book', {
        'created_at': row['created_at'],
        'title': row['title'],
        'posture': evaluation['posture'],
        'allocation_band': evaluation['allocation_band'],
        'score': evaluation['score'],
    }, policy.get('retain_cycles', 180))
    if evaluation['blockers'] or evaluation['posture'] in {'WATCH','OPERATOR_REVIEW','BLOCKED'}:
        _append(store, 'alerts', {
            'created_at': row['created_at'],
            'title': row['title'],
            'posture': evaluation['posture'],
            'blockers': evaluation['blockers'],
            'flags': evaluation['flags'],
        }, policy.get('retain_cycles', 180))
    store['latest_policy_run'] = row
    store['last_context'] = ctx
    _save(email, store)
    return _summary_for_email(email)


@router.post('/api/executive-capital-allocation-policy-layer/policy')
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


@router.post('/api/executive-capital-allocation-policy-layer/bootstrap-demo')
def bootstrap_demo(user=Depends(_require_user)):
    email = user['email']
    store = _load(email)
    if not store.get('policy_runs'):
        payload = {
            'title': 'govern offensive vs defensive capital sleeve policy',
            'summary': 'Set institutional target weights after scenario arbitration.',
            'proposed_notional': 360000,
            'cash_buffer_pct': 0.12,
            'defensive_override_pct': 0.22,
            'target_allocations': [
                {'sleeve': 'core-compounding', 'target_pct': 0.31},
                {'sleeve': 'tactical-alpha', 'target_pct': 0.23},
                {'sleeve': 'defensive-hedge', 'target_pct': 0.20},
                {'sleeve': 'cash-reserve', 'target_pct': 0.26},
            ],
        }
        return evaluate(payload, user)
    return _summary_for_email(email)
