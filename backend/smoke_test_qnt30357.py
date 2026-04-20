
from performance_intelligence import (
    default_performance_intelligence_state,
    performance_state_view,
    ingest_attribution_event,
    build_performance_snapshot,
    evaluate_meta_allocator,
    apply_meta_allocation,
)
from allocator_intelligence import default_allocator_intelligence_state, allocator_intelligence_state_view, propose_rebalance


def main():
    perf = performance_state_view(default_performance_intelligence_state())
    allocator = allocator_intelligence_state_view(default_allocator_intelligence_state())
    operator_state = {
        'strategies': {'strategies': [
            {'strategy_id': 'strat_aapl', 'name': 'AAPL Momentum', 'capital_limit': 12000, 'ai_confidence': 0.71},
            {'strategy_id': 'strat_btc', 'name': 'BTC Breakout', 'capital_limit': 15000, 'ai_confidence': 0.67},
            {'strategy_id': 'strat_es', 'name': 'ES Hedge', 'capital_limit': 10000, 'ai_confidence': 0.54},
        ]},
        'strategy_engine': {'metrics': {
            'strat_aapl': {'realized_pnl': 1200, 'unrealized_pnl': 210, 'win_rate': 0.62, 'capital_in_use': 11000},
            'strat_btc': {'realized_pnl': 1700, 'unrealized_pnl': 80, 'win_rate': 0.58, 'capital_in_use': 14500},
            'strat_es': {'realized_pnl': -400, 'unrealized_pnl': -90, 'win_rate': 0.41, 'capital_in_use': 9000},
        }}
    }
    for _ in range(4):
        ingest_attribution_event(perf, strategy_id='strat_aapl', strategy_name='AAPL Momentum', pnl=320, capital_used=11000, trades=5, win_rate=0.62, confidence=0.71)
        ingest_attribution_event(perf, strategy_id='strat_btc', strategy_name='BTC Breakout', pnl=250, capital_used=14500, trades=4, win_rate=0.58, confidence=0.67)
        ingest_attribution_event(perf, strategy_id='strat_es', strategy_name='ES Hedge', pnl=-180, capital_used=9000, trades=3, win_rate=0.41, confidence=0.54)
    propose_rebalance(allocator, operator_state=operator_state, portfolio_risk={})
    snap = build_performance_snapshot(perf, operator_state=operator_state, allocator_state=allocator)
    assert len(snap['strategies']) == 3
    result = evaluate_meta_allocator(perf, operator_state=operator_state, allocator_state=allocator)
    assert result['status'] == 'ok'
    assert len(result['proposals']) == 3
    applied = apply_meta_allocation(perf, operator_state=operator_state, allocator_state=allocator)
    assert applied['status'] == 'ok'
    assert any(c['action'] in ('boost', 'decay') for c in applied['changes'])
    print('QNT30357 smoke test passed')


if __name__ == '__main__':
    main()
