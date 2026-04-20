from backend.app.autonomous_control_loop.engine import AutonomousControlLoopEngine
from backend.app.autonomous_remediation_recovery.engine import AutonomousRemediationRecoveryEngine
from backend.app.institutional_breach_exception_resolution.engine import InstitutionalBreachExceptionResolutionEngine
from backend.app.institutional_allocation_execution_charter.engine import InstitutionalAllocationExecutionCharterEngine
from backend.app.executive_capital_committee.engine import ExecutiveCapitalCommitteeEngine
from backend.app.executive_scenario_arbitration.engine import ExecutiveScenarioArbitrationEngine
from backend.app.risk_control.state_store import load_state as load_risk_state, save_state as save_risk_state


def prime_context():
    risk = load_risk_state()
    risk['kill_switch_triggered'] = False
    risk['kill_switch_level'] = 'normal'
    risk.setdefault('metrics', {})['breach_count'] = 0
    save_risk_state(risk)

    committee = ExecutiveCapitalCommitteeEngine()
    committee.reset({'operator': 'smoke', 'reason': 'qnt50027_smoke'})
    committee.record_memory({
        'operator': 'smoke',
        'title': 'Prime committee context for QNT50027',
        'memory_type': 'capital_committee',
        'summary': 'Committee memory for remediation test.',
        'tags': ['smoke'],
    })

    arbitration = ExecutiveScenarioArbitrationEngine()
    arbitration.reset({'operator': 'smoke', 'reason': 'qnt50027_smoke'})
    decision = arbitration.arbitrate({
        'operator': 'smoke',
        'scenario_name': 'QNT50027 arbitration case',
        'title': 'QNT50027 arbitration case',
        'requested_action': 'allocate',
        'target_strategy': 'GLOBAL_MACRO',
        'policy_alignment_score': 93.0,
        'summary': 'Smoke scenario.',
    })['decision']

    charter = InstitutionalAllocationExecutionCharterEngine()
    charter.reset({'operator': 'smoke', 'reason': 'qnt50027_smoke'})
    charter.sync_context({'source': 'smoke'})
    charter_id = charter.register_charter({
        'operator': 'smoke',
        'title': 'QNT50027 charter',
        'target_strategy': 'GLOBAL_MACRO',
        'allowed_actions': ['allocate'],
        'max_notional': 50000.0,
        'max_capital_delta_pct': 0.10,
    })['charter']['charter_id']
    mandate_id = charter.register_mandate({
        'operator': 'smoke',
        'charter_id': charter_id,
        'title': 'QNT50027 mandate',
        'target_strategy': 'GLOBAL_MACRO',
        'allowed_actions': ['allocate'],
        'minimum_mandate_alignment_score': 80.0,
        'max_notional': 50000.0,
        'max_capital_delta_pct': 0.10,
    })['mandate']['mandate_id']
    directive = charter.enforce_mandate({
        'operator': 'smoke',
        'decision_id': decision['decision_id'],
        'mandate_id': mandate_id,
        'execution_action': 'allocate',
        'target_strategy': 'GLOBAL_MACRO',
        'proposed_notional': 25000.0,
        'capital_delta_pct': 0.05,
        'mandate_alignment_score': 92.0,
        'instruction': 'approved for smoke test',
    })['directive']

    breach = InstitutionalBreachExceptionResolutionEngine()
    breach.reset({'operator': 'smoke', 'reason': 'qnt50027_smoke'})
    breach.sync_context({'source': 'smoke'})
    case = breach.register_case({
        'operator': 'smoke',
        'title': 'Recovery breach case',
        'directive_id': directive['directive_id'],
        'breach_type': 'MANDATE_EXCEPTION',
        'severity': 'high',
        'alignment_score': 50.0,
        'summary': 'Recovery path needed.',
    })['case']
    breach.escalate_case({
        'operator': 'smoke',
        'case_id': case['case_id'],
        'escalation_level': 'supervisory',
        'reason': 'severe breach',
    })
    resolution = breach.resolve_exception({
        'operator': 'smoke',
        'case_id': case['case_id'],
        'resolution_type': 'override',
        'approved': True,
        'exception_scope': 'single_directive',
        'control_actions': ['heightened_monitoring'],
        'notes': 'approved for controlled recovery',
    })['resolution']

    control = AutonomousControlLoopEngine()
    control.reset({'operator': 'smoke', 'reason': 'qnt50027_smoke'})
    control.sync_context({'source': 'smoke'})

    return case['case_id'], resolution['resolution_id']


def run_smoke():
    case_id, resolution_id = prime_context()
    engine = AutonomousRemediationRecoveryEngine()
    engine.reset({'operator': 'smoke', 'reason': 'qnt50027_smoke'})
    engine.sync_context({'source': 'smoke'})

    action = engine.register_action({
        'operator': 'smoke',
        'case_id': case_id,
        'resolution_id': resolution_id,
        'title': 'Controlled remediation action',
        'requested_actions': ['reduce exposure', 'rebalance treasury buffer'],
        'capital_at_risk': 10000.0,
        'estimated_recovery_pct': 65.0,
    })['action']
    assert action['status'] == 'registered'

    auth = engine.authorize_recovery({
        'operator': 'smoke',
        'action_id': action['action_id'],
        'recovery_instruction': 'execute staged recovery',
        'required_confidence_score': 82.0,
    })
    assert auth['status'] == 'authorized'

    execution = engine.execute_recovery({
        'operator': 'smoke',
        'action_id': action['action_id'],
        'execution_mode': 'controlled',
        'steps_executed': ['reduce exposure', 'rebalance treasury buffer'],
        'recovered_capital': 6400.0,
        'residual_risk_score': 18.0,
        'result_summary': 'partial capital restored',
    })
    assert execution['status'] == 'executed'

    closed = engine.close_action({
        'operator': 'smoke',
        'action_id': action['action_id'],
        'closure_notes': 'recovery cycle complete',
    })
    assert closed['status'] == 'closed'

    summary = engine.summary()
    assert summary['recovery_cycle_count'] >= 1
    return summary


if __name__ == '__main__':
    print(run_smoke())
