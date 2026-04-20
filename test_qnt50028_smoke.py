from backend.app.autonomous_remediation_recovery.engine import AutonomousRemediationRecoveryEngine
from backend.app.executive_capital_committee.engine import ExecutiveCapitalCommitteeEngine
from backend.app.executive_scenario_arbitration.engine import ExecutiveScenarioArbitrationEngine
from backend.app.institutional_allocation_execution_charter.engine import InstitutionalAllocationExecutionCharterEngine
from backend.app.institutional_breach_exception_resolution.engine import InstitutionalBreachExceptionResolutionEngine
from backend.app.post_recovery_capital_reinstatement.engine import PostRecoveryCapitalReinstatementEngine
from backend.app.risk_control.state_store import load_state as load_risk_state, save_state as save_risk_state


def prime_context():
    risk = load_risk_state()
    risk['kill_switch_triggered'] = False
    risk['kill_switch_level'] = 'normal'
    risk.setdefault('metrics', {})['breach_count'] = 0
    save_risk_state(risk)

    committee = ExecutiveCapitalCommitteeEngine()
    committee.reset({'operator': 'smoke', 'reason': 'qnt50028_smoke'})
    committee.record_memory({
        'operator': 'smoke',
        'title': 'Prime committee context for QNT50028',
        'memory_type': 'capital_committee',
        'summary': 'Committee memory for reauthorization test.',
        'tags': ['smoke'],
    })

    arbitration = ExecutiveScenarioArbitrationEngine()
    arbitration.reset({'operator': 'smoke', 'reason': 'qnt50028_smoke'})
    decision = arbitration.arbitrate({
        'operator': 'smoke',
        'scenario_name': 'QNT50028 arbitration case',
        'title': 'QNT50028 arbitration case',
        'requested_action': 'allocate',
        'target_strategy': 'GLOBAL_MACRO',
        'policy_alignment_score': 95.0,
        'summary': 'Smoke scenario for reauthorization.',
    })['decision']

    charter = InstitutionalAllocationExecutionCharterEngine()
    charter.reset({'operator': 'smoke', 'reason': 'qnt50028_smoke'})
    charter.sync_context({'source': 'smoke'})
    charter_id = charter.register_charter({
        'operator': 'smoke',
        'title': 'QNT50028 charter',
        'target_strategy': 'GLOBAL_MACRO',
        'allowed_actions': ['allocate'],
        'max_notional': 100000.0,
        'max_capital_delta_pct': 0.2,
    })['charter']['charter_id']
    mandate_id = charter.register_mandate({
        'operator': 'smoke',
        'charter_id': charter_id,
        'title': 'QNT50028 mandate',
        'target_strategy': 'GLOBAL_MACRO',
        'allowed_actions': ['allocate'],
        'minimum_mandate_alignment_score': 80.0,
        'max_notional': 100000.0,
        'max_capital_delta_pct': 0.2,
    })['mandate']['mandate_id']
    directive = charter.enforce_mandate({
        'operator': 'smoke',
        'decision_id': decision['decision_id'],
        'mandate_id': mandate_id,
        'execution_action': 'allocate',
        'target_strategy': 'GLOBAL_MACRO',
        'proposed_notional': 30000.0,
        'capital_delta_pct': 0.06,
        'mandate_alignment_score': 94.0,
        'instruction': 'approved for reauthorization smoke test',
    })['directive']

    breach = InstitutionalBreachExceptionResolutionEngine()
    breach.reset({'operator': 'smoke', 'reason': 'qnt50028_smoke'})
    breach.sync_context({'source': 'smoke'})
    case = breach.register_case({
        'operator': 'smoke',
        'title': 'Post-recovery breach case',
        'directive_id': directive['directive_id'],
        'breach_type': 'MANDATE_EXCEPTION',
        'severity': 'high',
        'alignment_score': 48.0,
        'summary': 'Recovery path needed before reinstatement.',
    })['case']
    breach.escalate_case({
        'operator': 'smoke',
        'case_id': case['case_id'],
        'escalation_level': 'supervisory',
        'reason': 'capital reinstatement requires governed review',
    })
    resolution = breach.resolve_exception({
        'operator': 'smoke',
        'case_id': case['case_id'],
        'resolution_type': 'override',
        'approved': True,
        'exception_scope': 'single_directive',
        'control_actions': ['heightened_monitoring'],
        'notes': 'approved for controlled recovery and later reinstatement',
    })['resolution']

    remediation = AutonomousRemediationRecoveryEngine()
    remediation.reset({'operator': 'smoke', 'reason': 'qnt50028_smoke'})
    remediation.sync_context({'source': 'smoke'})
    action = remediation.register_action({
        'operator': 'smoke',
        'case_id': case['case_id'],
        'resolution_id': resolution['resolution_id'],
        'directive_id': directive['directive_id'],
        'title': 'Controlled remediation action',
        'requested_actions': ['reduce exposure', 'stabilize treasury buffer'],
        'capital_at_risk': 15000.0,
        'estimated_recovery_pct': 70.0,
    })['action']
    remediation.authorize_recovery({
        'operator': 'smoke',
        'action_id': action['action_id'],
        'recovery_instruction': 'execute staged recovery',
        'required_confidence_score': 84.0,
    })
    cycle = remediation.execute_recovery({
        'operator': 'smoke',
        'action_id': action['action_id'],
        'execution_mode': 'controlled',
        'steps_executed': ['reduce exposure', 'stabilize treasury buffer'],
        'recovered_capital': 9600.0,
        'residual_risk_score': 16.0,
        'result_summary': 'capital materially restored',
    })['cycle']
    remediation.close_action({
        'operator': 'smoke',
        'action_id': action['action_id'],
        'closure_notes': 'recovery cycle complete',
    })
    return action['action_id'], cycle['cycle_id'], case['case_id'], resolution['resolution_id']



def run_smoke():
    action_id, cycle_id, case_id, resolution_id = prime_context()
    engine = PostRecoveryCapitalReinstatementEngine()
    engine.reset({'operator': 'smoke', 'reason': 'qnt50028_smoke'})
    engine.sync_context({'source': 'smoke'})

    reauth = engine.register_reauthorization({
        'operator': 'smoke',
        'title': 'Reauthorize recovered capital',
        'action_id': action_id,
        'cycle_id': cycle_id,
        'case_id': case_id,
        'resolution_id': resolution_id,
        'target_strategy': 'GLOBAL_MACRO',
        'requested_capital': 9000.0,
        'reinstatement_pct': 60.0,
        'rationale': 'recovery succeeded; partial controlled reinstatement approved',
    })['reauthorization']
    assert reauth['status'] == 'registered'

    approved = engine.approve_reinstatement({
        'operator': 'smoke',
        'reauthorization_id': reauth['reauthorization_id'],
        'approved_capital': 8500.0,
        'approval_notes': 'stage capital back in slowly',
    })
    assert approved['status'] == 'approved'

    executed = engine.execute_reinstatement({
        'operator': 'smoke',
        'reauthorization_id': reauth['reauthorization_id'],
        'execution_mode': 'controlled',
        'capital_reinstated': 8500.0,
        'destination_account': 'broker_buffer',
        'result_summary': 'capital reinstated to broker buffer',
    })
    assert executed['status'] == 'executed'

    closed = engine.close_reauthorization({
        'operator': 'smoke',
        'reauthorization_id': reauth['reauthorization_id'],
        'closure_notes': 'post-recovery reinstatement complete',
    })
    assert closed['status'] == 'closed'

    summary = engine.summary()
    assert summary['reinstatement_event_count'] >= 1
    return summary


if __name__ == '__main__':
    print(run_smoke())
