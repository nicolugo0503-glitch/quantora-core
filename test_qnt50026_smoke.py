from backend.app.institutional_allocation_execution_charter.engine import InstitutionalAllocationExecutionCharterEngine
from backend.app.institutional_breach_exception_resolution.engine import InstitutionalBreachExceptionResolutionEngine
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
    committee.reset({'operator': 'smoke', 'reason': 'qnt50026_smoke'})
    committee.record_memory({
        'operator': 'smoke',
        'title': 'Prime committee context for QNT50026',
        'memory_type': 'capital_committee',
        'summary': 'Committee memory for breach escalation test.',
        'tags': ['smoke'],
    })

    arbitration = ExecutiveScenarioArbitrationEngine()
    arbitration.reset({'operator': 'smoke', 'reason': 'qnt50026_smoke'})
    decision = arbitration.arbitrate({
        'operator': 'smoke',
        'scenario_name': 'QNT50026 arbitration case',
        'title': 'QNT50026 arbitration case',
        'requested_action': 'allocate',
        'target_strategy': 'GLOBAL_MACRO',
        'policy_alignment_score': 91.0,
        'summary': 'Smoke scenario.',
    })['decision']

    charter = InstitutionalAllocationExecutionCharterEngine()
    charter.reset({'operator': 'smoke', 'reason': 'qnt50026_smoke'})
    charter.sync_context({'source': 'smoke'})
    charter_id = charter.register_charter({
        'operator': 'smoke',
        'title': 'QNT50026 charter',
        'target_strategy': 'GLOBAL_MACRO',
        'allowed_actions': ['allocate'],
        'max_notional': 50000.0,
        'max_capital_delta_pct': 0.10,
    })['charter']['charter_id']
    mandate_id = charter.register_mandate({
        'operator': 'smoke',
        'charter_id': charter_id,
        'title': 'QNT50026 mandate',
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
    return directive['directive_id']


def run_smoke():
    directive_id = prime_context()
    engine = InstitutionalBreachExceptionResolutionEngine()
    engine.reset({'operator': 'smoke', 'reason': 'qnt50026_smoke'})
    engine.sync_context({'source': 'smoke'})

    case = engine.register_case({
        'operator': 'smoke',
        'title': 'Breach case',
        'directive_id': directive_id,
        'breach_type': 'MANDATE_EXCEPTION',
        'severity': 'high',
        'alignment_score': 50.0,
        'summary': 'Escalation needed before exception resolution.',
    })['case']
    assert case['severity'] == 'severe'

    escalated = engine.escalate_case({
        'operator': 'smoke',
        'case_id': case['case_id'],
        'escalation_level': 'supervisory',
        'reason': 'severe breach',
    })
    assert escalated['status'] == 'escalated'

    resolved = engine.resolve_exception({
        'operator': 'smoke',
        'case_id': case['case_id'],
        'resolution_type': 'override',
        'approved': True,
        'exception_scope': 'single_directive',
        'control_actions': ['heightened_monitoring'],
        'notes': 'approved after supervisory escalation',
    })
    assert resolved['status'] == 'approved'

    summary = engine.summary()
    assert summary['resolution_count'] >= 1
    return summary


if __name__ == '__main__':
    print(run_smoke())
