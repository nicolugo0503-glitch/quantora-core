from backend.app.executive_capital_committee.engine import ExecutiveCapitalCommitteeEngine
from backend.app.executive_capital_committee.state_store import load_state


def main():
    engine = ExecutiveCapitalCommitteeEngine()
    engine.reset({'operator': 'smoke_test', 'reason': 'qnt50023_smoke'})
    engine.configure({
        'enabled': True,
        'auto_sync_sources': True,
        'require_risk_clearance': False,
        'require_liquidity_support': False,
        'require_control_loop_context': False,
        'minimum_committee_score': 60.0,
        'sync_after_configure': True,
    })
    engine.record_memory({
        'operator': 'smoke_test',
        'title': 'Prior BTC scale-up',
        'decision_scope': 'STRATEGY_SCALING',
        'summary': 'Scaled BTC sleeve when liquidity improved and performance stabilized.',
        'outcome_summary': 'Positive allocation outcome with no control breaches.',
        'tags': ['btc', 'scale', 'liquidity'],
        'memory_confidence_score': 86.0,
        'outcome_quality_score': 88.0,
    })
    proposal = engine.propose({
        'operator': 'smoke_test',
        'title': 'Increase BTC allocation',
        'decision_scope': 'STRATEGY_SCALING',
        'summary': 'Committee proposal to increase BTC notional under stable regime.',
        'requested_action': 'scale_strategy',
        'target_strategy': 'btc_momentum',
        'proposed_notional': 50000.0,
        'capital_delta_pct': 0.05,
        'conviction_score': 88.0,
        'scenario_coverage_score': 84.0,
        'execution_feasibility_score': 83.0,
        'policy_alignment_score': 90.0,
        'tags': ['btc', 'scale', 'committee'],
    })
    assert proposal['proposal']['proposal_id']
    decision = engine.approve({
        'operator': 'smoke_test',
        'proposal_id': proposal['proposal']['proposal_id'],
        'outcome': 'approve',
        'rationale': 'Smoke test approval',
    })
    state = load_state()
    assert state['decision_memories']
    assert state['committee_proposals']
    assert state['committee_decisions']
    print('QNT50023 smoke passed:', decision['status'])


if __name__ == '__main__':
    main()
