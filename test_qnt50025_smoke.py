from backend.app.executive_capital_committee.engine import ExecutiveCapitalCommitteeEngine
from backend.app.executive_scenario_arbitration.engine import ExecutiveScenarioArbitrationEngine
from backend.app.institutional_allocation_execution_charter.engine import InstitutionalAllocationExecutionCharterEngine
from backend.app.institutional_allocation_execution_charter.state_store import load_state


def main():
    committee = ExecutiveCapitalCommitteeEngine()
    committee.reset({'operator': 'smoke_test', 'reason': 'prime_committee_context_qnt50025'})
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
        'title': 'Prime committee context for QNT50025',
        'decision_scope': 'EXECUTION_AUTHORITY',
        'summary': 'Prime committee state for mandate enforcement smoke test.',
        'requested_action': 'scale_strategy',
        'target_strategy': 'btc_momentum',
        'proposed_notional': 50000.0,
        'capital_delta_pct': 0.04,
        'conviction_score': 90.0,
        'scenario_coverage_score': 85.0,
        'execution_feasibility_score': 84.0,
        'policy_alignment_score': 92.0,
        'tags': ['prime'],
    })
    committee.approve({
        'operator': 'smoke_test',
        'proposal_id': proposal['proposal']['proposal_id'],
        'outcome': 'approve',
        'rationale': 'Prime state for mandate enforcement smoke test',
    })

    arbitration = ExecutiveScenarioArbitrationEngine()
    arbitration.reset({'operator': 'smoke_test', 'reason': 'qnt50025_smoke'})
    arbitration.configure({
        'enabled': True,
        'auto_sync_sources': True,
        'require_committee_context': False,
        'require_risk_clearance': False,
        'minimum_available_liquidity': 0.0,
        'sync_after_configure': True,
    })
    arbitration.register_policy({
        'operator': 'smoke_test',
        'title': 'BTC institutional scaling policy',
        'policy_scope': 'EXECUTION_AUTHORITY_POLICY',
        'summary': 'Allow scale strategy action when resilient and aligned.',
        'target_strategy': 'btc_momentum',
        'allowed_actions': ['scale_strategy'],
        'blocked_actions': ['liquidate_all'],
        'max_capital_delta_pct': 0.10,
        'max_notional': 100000.0,
        'minimum_policy_alignment_score': 80.0,
        'minimum_scenario_resilience_score': 75.0,
        'tags': ['btc', 'policy'],
    })
    decision = arbitration.arbitrate({
        'operator': 'smoke_test',
        'title': 'Scale BTC strategy under institutional charter',
        'scenario_scope': 'EXECUTION_AUTHORITY_SCENARIO',
        'summary': 'Increase BTC under positive regime and adequate liquidity.',
        'requested_action': 'scale_strategy',
        'target_strategy': 'btc_momentum',
        'proposed_notional': 50000.0,
        'capital_delta_pct': 0.05,
        'policy_alignment_score': 93.0,
        'scenario_resilience_score': 87.0,
        'downside_risk_score': 35.0,
        'liquidity_coverage_score': 85.0,
        'rationale': 'Smoke test arbitration case for QNT50025',
        'tags': ['btc', 'scale'],
    })
    assert decision['decision']['decision_status'] in {'approved', 'guarded'}

    engine = InstitutionalAllocationExecutionCharterEngine()
    engine.reset({'operator': 'smoke_test', 'reason': 'qnt50025_smoke'})
    engine.configure({
        'enabled': True,
        'auto_sync_sources': True,
        'require_risk_clearance': False,
        'require_liquidity_support': False,
        'sync_after_configure': True,
    })
    charter = engine.register_charter({
        'operator': 'smoke_test',
        'title': 'BTC institutional execution charter',
        'summary': 'Governed BTC scaling charter.',
        'target_strategy': 'btc_momentum',
        'allowed_actions': ['scale_strategy'],
        'blocked_actions': ['liquidate_all'],
        'max_notional': 100000.0,
        'max_capital_delta_pct': 0.10,
        'tags': ['btc', 'charter'],
    })
    mandate = engine.register_mandate({
        'operator': 'smoke_test',
        'charter_id': charter['charter']['charter_id'],
        'title': 'BTC mandate A',
        'summary': 'Strategy-level execution mandate.',
        'target_strategy': 'btc_momentum',
        'allowed_actions': ['scale_strategy'],
        'blocked_actions': ['liquidate_all'],
        'minimum_mandate_alignment_score': 80.0,
        'max_notional': 100000.0,
        'max_capital_delta_pct': 0.10,
        'tags': ['btc', 'mandate'],
    })
    enforced = engine.enforce_mandate({
        'operator': 'smoke_test',
        'decision_id': decision['decision']['decision_id'],
        'mandate_id': mandate['mandate']['mandate_id'],
        'execution_action': 'scale_strategy',
        'target_strategy': 'btc_momentum',
        'proposed_notional': 50000.0,
        'capital_delta_pct': 0.05,
        'mandate_alignment_score': 90.0,
        'instruction': 'Authorize governed BTC scale instruction downstream.',
    })
    state = load_state()
    assert state['execution_charters']
    assert state['mandates']
    assert state['enforcement_directives']
    assert enforced['directive']['directive_status'] == 'issued'
    print('QNT50025 smoke passed:', enforced['status'])


if __name__ == '__main__':
    main()
