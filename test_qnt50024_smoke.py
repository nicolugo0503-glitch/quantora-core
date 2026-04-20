from backend.app.executive_capital_committee.engine import ExecutiveCapitalCommitteeEngine
from backend.app.executive_scenario_arbitration.engine import ExecutiveScenarioArbitrationEngine
from backend.app.executive_scenario_arbitration.state_store import load_state


def main():
    committee = ExecutiveCapitalCommitteeEngine()
    committee.reset({'operator': 'smoke_test', 'reason': 'prime_committee_context'})
    committee.configure({
        'enabled': True,
        'auto_sync_sources': True,
        'require_risk_clearance': False,
        'require_liquidity_support': False,
        'require_control_loop_context': False,
        'minimum_committee_score': 60.0,
        'sync_after_configure': True,
    })
    proposal = committee.propose({
        'operator': 'smoke_test',
        'title': 'Prime committee context',
        'decision_scope': 'STRATEGY_SCALING',
        'summary': 'Prime committee state for QNT50024 smoke test.',
        'requested_action': 'scale_strategy',
        'target_strategy': 'btc_momentum',
        'proposed_notional': 50000.0,
        'capital_delta_pct': 0.04,
        'conviction_score': 90.0,
        'scenario_coverage_score': 85.0,
        'execution_feasibility_score': 83.0,
        'policy_alignment_score': 91.0,
        'tags': ['prime'],
    })
    committee.approve({
        'operator': 'smoke_test',
        'proposal_id': proposal['proposal']['proposal_id'],
        'outcome': 'approve',
        'rationale': 'Prime state for arbitration smoke test',
    })

    engine = ExecutiveScenarioArbitrationEngine()
    engine.reset({'operator': 'smoke_test', 'reason': 'qnt50024_smoke'})
    engine.configure({
        'enabled': True,
        'auto_sync_sources': True,
        'require_committee_context': False,
        'require_risk_clearance': False,
        'minimum_available_liquidity': 0.0,
        'sync_after_configure': True,
    })
    engine.register_policy({
        'operator': 'smoke_test',
        'title': 'BTC scaling policy',
        'policy_scope': 'EXECUTIVE_ALLOCATION_POLICY',
        'summary': 'Allow scale strategy action under resilient scenario posture.',
        'target_strategy': 'btc_momentum',
        'allowed_actions': ['scale_strategy'],
        'blocked_actions': ['liquidate_all'],
        'max_capital_delta_pct': 0.10,
        'max_notional': 100000.0,
        'minimum_policy_alignment_score': 80.0,
        'minimum_scenario_resilience_score': 75.0,
        'tags': ['btc', 'policy'],
    })
    result = engine.arbitrate({
        'operator': 'smoke_test',
        'title': 'Scale BTC strategy',
        'scenario_scope': 'EXECUTIVE_ALLOCATION_SCENARIO',
        'summary': 'Increase BTC under positive regime and adequate liquidity.',
        'requested_action': 'scale_strategy',
        'target_strategy': 'btc_momentum',
        'proposed_notional': 50000.0,
        'capital_delta_pct': 0.05,
        'policy_alignment_score': 92.0,
        'scenario_resilience_score': 87.0,
        'downside_risk_score': 35.0,
        'liquidity_coverage_score': 82.0,
        'rationale': 'Smoke test arbitration case',
        'tags': ['btc', 'scale'],
    })
    assert result['decision']['decision_status'] in {'approved', 'guarded'}
    enforced = engine.enforce_policy({
        'operator': 'smoke_test',
        'decision_id': result['decision']['decision_id'],
        'enforcement_action': 'issue_allocation_directive',
        'instruction': 'Allow governed scaling directive downstream.',
    })
    state = load_state()
    assert state['allocation_policies']
    assert state['scenario_cases']
    assert state['arbitration_decisions']
    assert enforced['directive']['directive_status'] == 'issued'
    print('QNT50024 smoke passed:', enforced['status'])


if __name__ == '__main__':
    main()
