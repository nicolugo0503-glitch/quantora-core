from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=['executive-scenario-arbitration-layer'])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / 'backend' / 'artifacts'
ENGINE_DIR = ARTIFACTS_DIR / 'executive_scenario_arbitration_layer'
DEFAULT_POLICY = {
    'retain_cycles': 180,
    'minimum_arbitration_score': 84.0,
    'require_operator_clear': True,
    'require_release_clear': True,
    'require_safety_clear': True,
    'require_fund_admin_clear': True,
    'require_forensic_clear': True,
    'require_recovery_clear': True,
    'require_executive_context': True,
    'require_memory_context': True,
    'require_committee_context': True,
    'require_allocation_governance': True,
    'prefer_defense_when_regime_hostile': True,
    'prefer_defense_when_liquidity_not_ready': True,
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


def _strategy():
    from backend.app import qnt30708_strategy_evolution_engine_router as strategy
    return strategy


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
            'scenario_sets': [],
            'conflicts': [],
            'arbitrations': [],
            'alerts': [],
            'arbitration_book': [],
            'latest_scenario_set': None,
            'latest_conflict_report': None,
            'latest_arbitration': None,
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
    strategy = _strategy()._summary_for_email(email)
    liquidity = _liquidity()._summary_for_email(email)
    regime = _regime()._summary_for_email(email)
    defense = _defense()._summary_for_email(email)
    allocation = _allocation_governance()._summary_for_email(email)
    executive = _executive()._summary_for_email(email)
    memory = _memory()._summary_for_email(email)
    committee = _committee()._summary_for_email(email)
    return {
        'captured_at': _now_iso(),
        'operator': {
            'posture': (operator.get('operator_console_status') or {}).get('posture'),
            'override_required': (operator.get('operator_console_status') or {}).get('operator_override_required'),
            'execution_paused': (operator.get('operator_console_status') or {}).get('execution_paused'),
        },
        'release': {
            'can_deploy': (release.get('release_control_status') or {}).get('can_deploy'),
            'approval_backlog': (release.get('release_control_status') or {}).get('approval_backlog'),
            'active_version': (release.get('release_control_status') or {}).get('active_version'),
        },
        'safety': {
            'posture': (safety.get('safety_layer_status') or {}).get('posture'),
            'kill_switch': (safety.get('safety_layer_status') or {}).get('kill_switch'),
            'execution_paused': (safety.get('safety_layer_status') or {}).get('execution_paused'),
            'risk_score': (safety.get('safety_layer_status') or {}).get('risk_score'),
        },
        'fund_admin': {
            'readiness': (fund_admin.get('fund_admin_status') or {}).get('readiness'),
            'current_nav': (fund_admin.get('fund_admin_status') or {}).get('current_nav'),
            'reconciliation_status': (fund_admin.get('fund_admin_status') or {}).get('reconciliation_status'),
        },
        'forensic': {
            'posture': (forensic.get('forensic_status') or {}).get('posture'),
            'critical_open_count': (forensic.get('forensic_status') or {}).get('critical_open_count'),
        },
        'recovery': {
            'posture': (recovery.get('recovery_status') or {}).get('posture'),
            'safe_mode': (recovery.get('recovery_status') or {}).get('safe_mode'),
        },
        'strategy': {
            'posture': (strategy.get('strategy_evolution_status') or {}).get('posture'),
            'promotable_count': (strategy.get('strategy_evolution_status') or {}).get('promotable_count'),
            'blocked_count': (strategy.get('strategy_evolution_status') or {}).get('blocked_count'),
        },
        'liquidity': {
            'posture': (liquidity.get('liquidity_status') or {}).get('posture'),
            'ready': (liquidity.get('liquidity_status') or {}).get('ready'),
            'latest_score': (liquidity.get('liquidity_status') or {}).get('latest_score'),
        },
        'regime': {
            'posture': (regime.get('market_regime_status') or {}).get('posture'),
            'ready': (regime.get('market_regime_status') or {}).get('ready'),
            'active_regime': (regime.get('market_regime_status') or {}).get('active_regime'),
            'latest_score': (regime.get('market_regime_status') or {}).get('latest_score'),
        },
        'defense': {
            'posture': (defense.get('defensive_systems_status') or {}).get('posture'),
            'approved': (defense.get('defensive_systems_status') or {}).get('approved'),
            'active_mode': (defense.get('defensive_systems_status') or {}).get('active_mode'),
        },
        'allocation_governance': {
            'posture': (allocation.get('autonomous_allocation_governance_status') or {}).get('posture'),
            'approved': (allocation.get('autonomous_allocation_governance_status') or {}).get('approved'),
            'operator_review_required': (allocation.get('autonomous_allocation_governance_status') or {}).get('operator_review_required'),
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
        'committee': {
            'posture': (committee.get('capital_committee_deliberation_layer_status') or {}).get('posture'),
            'committee_band': (committee.get('capital_committee_deliberation_layer_status') or {}).get('committee_band'),
            'action_band': (committee.get('capital_committee_deliberation_layer_status') or {}).get('action_band'),
        },
    }


def _normalized_action(value: str) -> str:
    value = str(value or 'HOLD').upper().strip()
    if value not in {'ALLOCATE', 'TILT', 'HOLD', 'DEFEND', 'BLOCK'}:
        return 'HOLD'
    return value


def _build_scenarios_from_payload(payload: dict, ctx: dict) -> list:
    scenarios = []
    source = list(payload.get('scenarios') or [])
    if source:
        for idx, raw in enumerate(source, start=1):
            scenarios.append({
                'scenario_id': raw.get('scenario_id') or f'S{idx}',
                'label': raw.get('label') or f'Scenario {idx}',
                'bias': str(raw.get('bias') or 'NEUTRAL').upper(),
                'capital_action': _normalized_action(raw.get('capital_action')),
                'confidence': float(raw.get('confidence') or 0.0),
                'scenario_quality': float(raw.get('scenario_quality') or raw.get('confidence') or 0.0),
                'strategy_alignment': float(raw.get('strategy_alignment') or 0.0),
                'liquidity_fit': float(raw.get('liquidity_fit') or 0.0),
                'regime_fit': float(raw.get('regime_fit') or 0.0),
                'execution_feasibility': float(raw.get('execution_feasibility') or 0.0),
                'notional': float(raw.get('notional') or payload.get('proposed_notional') or 0.0),
                'thesis': raw.get('thesis') or '',
            })
        return scenarios

    executive_band = _normalized_action((ctx.get('executive') or {}).get('recommended_band') or 'HOLD')
    regime_ready = bool((ctx.get('regime') or {}).get('ready'))
    liquidity_ready = bool((ctx.get('liquidity') or {}).get('ready'))
    defense_active = str((ctx.get('defense') or {}).get('active_mode') or '').upper() in {'CRISIS_LOCKDOWN', 'HARD_STOP', 'SOFT_HEDGE'}
    scenarios.append({
        'scenario_id': 'S1',
        'label': 'Executive base case',
        'bias': 'OFFENSIVE' if executive_band in {'ALLOCATE', 'TILT'} else ('DEFENSIVE' if executive_band == 'DEFEND' else 'NEUTRAL'),
        'capital_action': executive_band,
        'confidence': float((ctx.get('executive') or {}).get('latest_score') or 72.0),
        'scenario_quality': float((ctx.get('executive') or {}).get('latest_score') or 72.0),
        'strategy_alignment': 84.0 if str((ctx.get('strategy') or {}).get('posture') or '').upper() == 'READY' else 62.0,
        'liquidity_fit': 82.0 if liquidity_ready else 48.0,
        'regime_fit': 82.0 if regime_ready else 45.0,
        'execution_feasibility': 88.0 if str((ctx.get('safety') or {}).get('posture') or '').upper() in {'SAFE', 'CONSTRAINED'} else 34.0,
        'notional': float(payload.get('proposed_notional') or 180000.0),
        'thesis': payload.get('summary') or 'Base executive scenario synthesized from current cross-system posture.',
    })
    scenarios.append({
        'scenario_id': 'S2',
        'label': 'Defensive preservation case',
        'bias': 'DEFENSIVE',
        'capital_action': 'DEFEND' if defense_active or not regime_ready or not liquidity_ready else 'HOLD',
        'confidence': 78.0 if (defense_active or not regime_ready or not liquidity_ready) else 66.0,
        'scenario_quality': 80.0 if (defense_active or not regime_ready or not liquidity_ready) else 68.0,
        'strategy_alignment': 70.0,
        'liquidity_fit': 92.0,
        'regime_fit': 90.0,
        'execution_feasibility': 86.0,
        'notional': float(payload.get('proposed_notional') or 180000.0) * 0.6,
        'thesis': 'Preserve capital when regime, liquidity, or defense posture constrains offensive deployment.',
    })
    scenarios.append({
        'scenario_id': 'S3',
        'label': 'Supervised hold case',
        'bias': 'NEUTRAL',
        'capital_action': 'HOLD',
        'confidence': 71.0,
        'scenario_quality': 74.0,
        'strategy_alignment': 76.0,
        'liquidity_fit': 78.0,
        'regime_fit': 72.0,
        'execution_feasibility': 91.0,
        'notional': float(payload.get('proposed_notional') or 180000.0) * 0.2,
        'thesis': 'Delay large capital moves until scenario conflict or confidence ambiguity resolves.',
    })
    return scenarios


def _detect_conflicts(scenarios: list, ctx: dict, policy: dict) -> dict:
    conflicts = []
    for idx, left in enumerate(scenarios):
        for right in scenarios[idx + 1:]:
            if left.get('capital_action') != right.get('capital_action'):
                conflicts.append({
                    'type': 'ACTION_CONFLICT',
                    'left': left.get('scenario_id'),
                    'right': right.get('scenario_id'),
                    'message': f"{left.get('scenario_id')} proposes {left.get('capital_action')} while {right.get('scenario_id')} proposes {right.get('capital_action')}",
                    'severity': 'high' if {'ALLOCATE', 'DEFEND'} == {left.get('capital_action'), right.get('capital_action')} else 'medium',
                })
            if abs(float(left.get('confidence') or 0.0) - float(right.get('confidence') or 0.0)) <= 6.0:
                conflicts.append({
                    'type': 'CONFIDENCE_COLLISION',
                    'left': left.get('scenario_id'),
                    'right': right.get('scenario_id'),
                    'message': f"{left.get('scenario_id')} and {right.get('scenario_id')} have similarly strong confidence.",
                    'severity': 'medium',
                })

    regime_ready = bool((ctx.get('regime') or {}).get('ready'))
    liquidity_ready = bool((ctx.get('liquidity') or {}).get('ready'))
    defense_active = str((ctx.get('defense') or {}).get('active_mode') or '').upper() in {'CRISIS_LOCKDOWN', 'HARD_STOP', 'SOFT_HEDGE'}
    for scenario in scenarios:
        action = scenario.get('capital_action')
        sid = scenario.get('scenario_id')
        if policy.get('prefer_defense_when_regime_hostile') and not regime_ready and action in {'ALLOCATE', 'TILT'}:
            conflicts.append({
                'type': 'REGIME_HOSTILITY',
                'scenario_id': sid,
                'message': f'{sid} is offensive while market regime is not favorable.',
                'severity': 'high',
            })
        if policy.get('prefer_defense_when_liquidity_not_ready') and not liquidity_ready and action in {'ALLOCATE', 'TILT'}:
            conflicts.append({
                'type': 'LIQUIDITY_STRESS',
                'scenario_id': sid,
                'message': f'{sid} is offensive while liquidity readiness is constrained.',
                'severity': 'high',
            })
        if defense_active and action in {'ALLOCATE', 'TILT'}:
            conflicts.append({
                'type': 'DEFENSE_OVERRIDE',
                'scenario_id': sid,
                'message': f'{sid} conflicts with the currently active defensive mode.',
                'severity': 'critical',
            })
    return {
        'conflict_count': len(conflicts),
        'critical_count': len([c for c in conflicts if c.get('severity') == 'critical']),
        'high_count': len([c for c in conflicts if c.get('severity') == 'high']),
        'conflicts': conflicts,
    }


def _score_scenario(scenario: dict, ctx: dict) -> float:
    base = (
        float(scenario.get('confidence') or 0.0) * 0.28 +
        float(scenario.get('scenario_quality') or 0.0) * 0.20 +
        float(scenario.get('strategy_alignment') or 0.0) * 0.15 +
        float(scenario.get('liquidity_fit') or 0.0) * 0.12 +
        float(scenario.get('regime_fit') or 0.0) * 0.12 +
        float(scenario.get('execution_feasibility') or 0.0) * 0.13
    )
    memory_band = str((ctx.get('memory') or {}).get('memory_band') or '').upper()
    committee_band = str((ctx.get('committee') or {}).get('committee_band') or '').upper()
    if memory_band in {'TRUSTED', 'COMPOUNDING'}:
        base += 4.0
    elif memory_band in {'FRAGILE', 'QUARANTINE'}:
        base -= 4.0
    if committee_band == 'HIGH_CONVICTION':
        base += 3.0
    elif committee_band == 'QUARANTINE':
        base -= 6.0
    if str((ctx.get('strategy') or {}).get('posture') or '').upper() not in {'READY', 'ATTENTION'}:
        base -= 4.0
    return round(max(0.0, min(100.0, base)), 2)


def _arbitrate(scenarios: list, conflict_report: dict, ctx: dict, policy: dict) -> dict:
    blockers = []
    if policy.get('require_operator_clear') and str((ctx.get('operator') or {}).get('posture') or '').upper() not in {'READY', 'CLEAR', 'ACTIVE'}:
        blockers.append('operator-not-clear')
    if (ctx.get('operator') or {}).get('execution_paused'):
        blockers.append('operator-execution-paused')
    if policy.get('require_release_clear') and not bool((ctx.get('release') or {}).get('can_deploy')):
        blockers.append('release-not-clear')
    safety_posture = str((ctx.get('safety') or {}).get('posture') or '').upper()
    if policy.get('require_safety_clear') and safety_posture not in {'SAFE', 'CONSTRAINED'}:
        blockers.append('safety-not-clear')
    if (ctx.get('safety') or {}).get('kill_switch'):
        blockers.append('safety-kill-switch-active')
    if policy.get('require_fund_admin_clear') and str((ctx.get('fund_admin') or {}).get('readiness') or '').lower() not in {'ready', 'attention'}:
        blockers.append('fund-admin-not-clear')
    if policy.get('require_forensic_clear') and str((ctx.get('forensic') or {}).get('posture') or '').lower() == 'blocked':
        blockers.append('forensic-not-clear')
    if policy.get('require_recovery_clear') and bool((ctx.get('recovery') or {}).get('safe_mode')):
        blockers.append('recovery-safe-mode')
    if policy.get('require_executive_context') and str((ctx.get('executive') or {}).get('posture') or '').upper() not in {'APPROVED', 'WATCH', 'OPERATOR_REVIEW'}:
        blockers.append('executive-context-missing')
    if policy.get('require_memory_context') and str((ctx.get('memory') or {}).get('posture') or '').upper() not in {'TRUSTED', 'WATCH', 'IDLE'}:
        blockers.append('memory-context-missing')
    if policy.get('require_committee_context') and str((ctx.get('committee') or {}).get('posture') or '').upper() not in {'APPROVED', 'WATCH', 'OPERATOR_REVIEW', 'IDLE'}:
        blockers.append('committee-context-missing')
    if policy.get('require_allocation_governance') and str((ctx.get('allocation_governance') or {}).get('posture') or '').upper() not in {'APPROVED', 'WATCH', 'SAFE_MODE', 'READY', 'SUPERVISED'}:
        blockers.append('allocation-governance-not-clear')

    ranked = []
    for scenario in scenarios:
        score = _score_scenario(scenario, ctx)
        penalties = []
        action = scenario.get('capital_action')
        if not bool((ctx.get('regime') or {}).get('ready')) and action in {'ALLOCATE', 'TILT'}:
            score -= 14.0
            penalties.append('regime-hostile-to-offense')
        if not bool((ctx.get('liquidity') or {}).get('ready')) and action in {'ALLOCATE', 'TILT'}:
            score -= 12.0
            penalties.append('liquidity-constrained')
        if str((ctx.get('defense') or {}).get('active_mode') or '').upper() in {'CRISIS_LOCKDOWN', 'HARD_STOP'} and action in {'ALLOCATE', 'TILT'}:
            score -= 18.0
            penalties.append('defense-override-active')
        if conflict_report.get('critical_count') and action in {'ALLOCATE', 'TILT'}:
            score -= 8.0
            penalties.append('critical-conflicts-present')
        ranked.append({
            'scenario_id': scenario.get('scenario_id'),
            'label': scenario.get('label'),
            'capital_action': action,
            'bias': scenario.get('bias'),
            'score': round(max(0.0, min(100.0, score)), 2),
            'penalties': penalties,
            'notional': float(scenario.get('notional') or 0.0),
            'thesis': scenario.get('thesis') or '',
        })
    ranked.sort(key=lambda row: row.get('score', 0.0), reverse=True)
    winner = ranked[0] if ranked else {'capital_action': 'BLOCK', 'score': 0.0}
    final_decision = winner.get('capital_action') or 'BLOCK'
    posture = 'APPROVED'
    if blockers:
        posture = 'BLOCKED'
        final_decision = 'BLOCK'
    elif winner.get('score', 0.0) < float(policy.get('minimum_arbitration_score') or 0.0):
        posture = 'WATCH'
        final_decision = 'HOLD' if final_decision in {'ALLOCATE', 'TILT'} else final_decision
    review_required = bool(
        float(winner.get('notional') or 0.0) >= float(policy.get('operator_review_notional_threshold') or 0.0)
        or (ctx.get('operator') or {}).get('override_required')
        or (ctx.get('allocation_governance') or {}).get('operator_review_required')
    )
    if review_required and posture == 'APPROVED':
        posture = 'OPERATOR_REVIEW'
    reasoning = []
    if winner.get('label'):
        reasoning.append(f"winner={winner.get('label')}")
    reasoning.extend(winner.get('penalties') or [])
    if conflict_report.get('high_count'):
        reasoning.append(f"high_conflicts={conflict_report.get('high_count')}")
    if str((ctx.get('defense') or {}).get('active_mode') or '').upper() in {'CRISIS_LOCKDOWN', 'HARD_STOP', 'SOFT_HEDGE'}:
        reasoning.append('defense-context-present')
    if not bool((ctx.get('regime') or {}).get('ready')):
        reasoning.append('regime-not-favorable')
    if not bool((ctx.get('liquidity') or {}).get('ready')):
        reasoning.append('liquidity-not-ready')
    return {
        'posture': posture,
        'final_decision': final_decision,
        'recommended_band': final_decision,
        'score': winner.get('score', 0.0),
        'review_required': review_required,
        'winner': winner,
        'ranked_scenarios': ranked,
        'blockers': blockers,
        'reasoning': reasoning[:12],
        'conflict_count': conflict_report.get('conflict_count'),
    }


def _summary_for_email(email: str) -> dict:
    store = _load(email)
    latest_set = store.get('latest_scenario_set') or {}
    latest_conflicts = store.get('latest_conflict_report') or {}
    latest_arbitration = store.get('latest_arbitration') or {}
    latest_eval = latest_arbitration.get('evaluation') or {}
    return {
        'executive_scenario_arbitration_layer_status': {
            'posture': latest_eval.get('posture', 'IDLE'),
            'latest_score': latest_eval.get('score'),
            'final_decision': latest_eval.get('final_decision'),
            'scenario_count': len((latest_set.get('scenarios') or [])),
            'conflict_count': latest_eval.get('conflict_count') or latest_conflicts.get('conflict_count') or 0,
            'arbitration_count': len(store.get('arbitrations') or []),
            'alert_count': len(store.get('alerts') or []),
        },
        'latest_scenario_set': latest_set,
        'latest_conflict_report': latest_conflicts,
        'latest_arbitration': latest_arbitration,
        'policy': store.get('policy') or dict(DEFAULT_POLICY),
        'arbitration_book': store.get('arbitration_book') or [],
        'alerts': store.get('alerts') or [],
        'last_context': store.get('last_context') or {},
    }


@router.get('/api/executive-scenario-arbitration-layer/summary')
def summary(session=Depends(_require_user)):
    return _summary_for_email(session['email'])


@router.post('/api/executive-scenario-arbitration-layer/build-scenarios')
def build_scenarios(payload: dict = Body(...), session=Depends(_require_user)):
    email = session['email']
    store = _load(email)
    policy = store.get('policy') or dict(DEFAULT_POLICY)
    ctx = _cross_system_context(email)
    scenarios = _build_scenarios_from_payload(payload or {}, ctx)
    row = {
        'scenario_set_id': f'esa-scenarios-{_now_ts()}',
        'created_at': _now_iso(),
        'title': payload.get('title') or 'executive-scenario-set',
        'summary': payload.get('summary') or '',
        'proposed_notional': float(payload.get('proposed_notional') or 0.0),
        'scenarios': scenarios,
        'context': ctx,
    }
    _append(store, 'scenario_sets', row, policy.get('retain_cycles', 180))
    store['latest_scenario_set'] = row
    store['last_context'] = ctx
    _save(email, store)
    return row


@router.post('/api/executive-scenario-arbitration-layer/detect-conflicts')
def detect_conflicts(payload: dict = Body(default={}), session=Depends(_require_user)):
    email = session['email']
    store = _load(email)
    policy = store.get('policy') or dict(DEFAULT_POLICY)
    ctx = _cross_system_context(email)
    latest_set = store.get('latest_scenario_set') or {}
    scenarios = list(payload.get('scenarios') or latest_set.get('scenarios') or [])
    report = {
        'conflict_report_id': f'esa-conflicts-{_now_ts()}',
        'created_at': _now_iso(),
        'scenario_set_id': payload.get('scenario_set_id') or latest_set.get('scenario_set_id'),
        'context': ctx,
    }
    report.update(_detect_conflicts(scenarios, ctx, policy))
    _append(store, 'conflicts', report, policy.get('retain_cycles', 180))
    store['latest_conflict_report'] = report
    store['last_context'] = ctx
    _save(email, store)
    return report


@router.post('/api/executive-scenario-arbitration-layer/arbitrate')
def arbitrate(payload: dict = Body(default={}), session=Depends(_require_user)):
    email = session['email']
    store = _load(email)
    policy = store.get('policy') or dict(DEFAULT_POLICY)
    ctx = _cross_system_context(email)
    latest_set = store.get('latest_scenario_set') or {}
    scenarios = list(payload.get('scenarios') or latest_set.get('scenarios') or [])
    conflict_report = store.get('latest_conflict_report') or _detect_conflicts(scenarios, ctx, policy)
    evaluation = _arbitrate(scenarios, conflict_report, ctx, policy)
    row = {
        'arbitration_id': f'esa-arb-{_now_ts()}',
        'created_at': _now_iso(),
        'scenario_set_id': payload.get('scenario_set_id') or latest_set.get('scenario_set_id'),
        'title': payload.get('title') or latest_set.get('title') or 'executive-scenario-arbitration',
        'context': ctx,
        'evaluation': evaluation,
    }
    _append(store, 'arbitrations', row, policy.get('retain_cycles', 180))
    _append(store, 'arbitration_book', {
        'created_at': row['created_at'],
        'title': row['title'],
        'posture': evaluation.get('posture'),
        'final_decision': evaluation.get('final_decision'),
        'score': evaluation.get('score'),
    }, policy.get('retain_cycles', 180))
    if evaluation.get('blockers') or evaluation.get('posture') in {'WATCH', 'BLOCKED', 'OPERATOR_REVIEW'}:
        _append(store, 'alerts', {
            'created_at': row['created_at'],
            'title': row['title'],
            'posture': evaluation.get('posture'),
            'final_decision': evaluation.get('final_decision'),
            'blockers': evaluation.get('blockers'),
        }, policy.get('retain_cycles', 180))
    store['latest_arbitration'] = row
    store['last_context'] = ctx
    _save(email, store)
    return row


@router.get('/api/executive-scenario-arbitration-layer/decision')
def decision(session=Depends(_require_user)):
    email = session['email']
    latest = _load(email).get('latest_arbitration') or {}
    return {
        'decision': (latest.get('evaluation') or {}).get('final_decision'),
        'posture': (latest.get('evaluation') or {}).get('posture'),
        'score': (latest.get('evaluation') or {}).get('score'),
        'reasoning': (latest.get('evaluation') or {}).get('reasoning') or [],
        'winner': (latest.get('evaluation') or {}).get('winner') or {},
    }


@router.post('/api/executive-scenario-arbitration-layer/policy')
def policy(payload: dict = Body(...), session=Depends(_require_user)):
    email = session['email']
    store = _load(email)
    merged = dict(DEFAULT_POLICY)
    merged.update(store.get('policy') or {})
    merged.update(payload or {})
    store['policy'] = merged
    _save(email, store)
    return {'ok': True, 'policy': merged}


@router.post('/api/executive-scenario-arbitration-layer/bootstrap-demo')
def bootstrap_demo(session=Depends(_require_user)):
    email = session['email']
    store = _load(email)
    policy = store.get('policy') or dict(DEFAULT_POLICY)
    ctx = _cross_system_context(email)
    payload = {
        'title': 'arbitrate offensive vs defensive capital directives',
        'summary': 'Resolve conflict between offensive executive allocation, defensive preservation, and supervised hold posture.',
        'proposed_notional': 210000,
        'scenarios': [
            {
                'scenario_id': 'S1',
                'label': 'Offensive breakout allocation',
                'bias': 'BULLISH',
                'capital_action': 'ALLOCATE',
                'confidence': 88,
                'scenario_quality': 86,
                'strategy_alignment': 90,
                'liquidity_fit': 70,
                'regime_fit': 72,
                'execution_feasibility': 84,
                'notional': 210000,
                'thesis': 'Deploy into resilient compounders if macro stress remains contained.',
            },
            {
                'scenario_id': 'S2',
                'label': 'Defensive hedge-first posture',
                'bias': 'DEFENSIVE',
                'capital_action': 'DEFEND',
                'confidence': 83,
                'scenario_quality': 82,
                'strategy_alignment': 74,
                'liquidity_fit': 92,
                'regime_fit': 90,
                'execution_feasibility': 89,
                'notional': 125000,
                'thesis': 'Preserve capital until regime and liquidity fully align.',
            },
            {
                'scenario_id': 'S3',
                'label': 'Supervised wait state',
                'bias': 'NEUTRAL',
                'capital_action': 'HOLD',
                'confidence': 76,
                'scenario_quality': 78,
                'strategy_alignment': 80,
                'liquidity_fit': 84,
                'regime_fit': 80,
                'execution_feasibility': 92,
                'notional': 40000,
                'thesis': 'Wait for conflict clarity before moving large capital.',
            },
        ],
    }
    scenario_row = {
        'scenario_set_id': f'esa-scenarios-{_now_ts()}',
        'created_at': _now_iso(),
        'title': payload['title'],
        'summary': payload['summary'],
        'proposed_notional': payload['proposed_notional'],
        'scenarios': _build_scenarios_from_payload(payload, ctx),
        'context': ctx,
    }
    _append(store, 'scenario_sets', scenario_row, policy.get('retain_cycles', 180))
    conflict_row = {
        'conflict_report_id': f'esa-conflicts-{_now_ts()}',
        'created_at': _now_iso(),
        'scenario_set_id': scenario_row['scenario_set_id'],
        'context': ctx,
    }
    conflict_row.update(_detect_conflicts(scenario_row['scenarios'], ctx, policy))
    _append(store, 'conflicts', conflict_row, policy.get('retain_cycles', 180))
    evaluation = _arbitrate(scenario_row['scenarios'], conflict_row, ctx, policy)
    arbitration_row = {
        'arbitration_id': f'esa-arb-{_now_ts()}',
        'created_at': _now_iso(),
        'scenario_set_id': scenario_row['scenario_set_id'],
        'title': scenario_row['title'],
        'context': ctx,
        'evaluation': evaluation,
    }
    _append(store, 'arbitrations', arbitration_row, policy.get('retain_cycles', 180))
    _append(store, 'arbitration_book', {
        'created_at': arbitration_row['created_at'],
        'title': arbitration_row['title'],
        'posture': evaluation.get('posture'),
        'final_decision': evaluation.get('final_decision'),
        'score': evaluation.get('score'),
    }, policy.get('retain_cycles', 180))
    if evaluation.get('blockers') or evaluation.get('posture') in {'WATCH', 'BLOCKED', 'OPERATOR_REVIEW'}:
        _append(store, 'alerts', {
            'created_at': arbitration_row['created_at'],
            'title': arbitration_row['title'],
            'posture': evaluation.get('posture'),
            'final_decision': evaluation.get('final_decision'),
            'blockers': evaluation.get('blockers'),
        }, policy.get('retain_cycles', 180))
    store['latest_scenario_set'] = scenario_row
    store['latest_conflict_report'] = conflict_row
    store['latest_arbitration'] = arbitration_row
    store['last_context'] = ctx
    _save(email, store)
    return _summary_for_email(email)
