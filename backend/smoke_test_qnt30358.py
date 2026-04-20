
from research_memory import (
    default_research_memory_state,
    research_memory_state_view,
    ingest_research_note,
    build_regime_snapshot,
    evaluate_regime_allocator,
)
from performance_intelligence import default_performance_intelligence_state, performance_state_view, ingest_attribution_event
from allocator_intelligence import default_allocator_intelligence_state, allocator_intelligence_state_view
from portfolio_risk_fabric import default_portfolio_risk_state, portfolio_risk_state_view


def main():
    research = research_memory_state_view(default_research_memory_state())
    perf = performance_state_view(default_performance_intelligence_state())
    allocator = allocator_intelligence_state_view(default_allocator_intelligence_state())
    risk = portfolio_risk_state_view(default_portfolio_risk_state())
    operator_state = {
        'strategies': {'strategies': [
            {'strategy_id': 'strat_aapl', 'name': 'AAPL Momentum', 'capital_limit': 12000, 'ai_confidence': 0.72},
            {'strategy_id': 'strat_spy', 'name': 'SPY Mean Revert', 'capital_limit': 10000, 'ai_confidence': 0.58},
        ]},
        'strategy_engine': {'metrics': {
            'strat_aapl': {'realized_pnl': 1500, 'unrealized_pnl': 230, 'win_rate': 0.62},
            'strat_spy': {'realized_pnl': -240, 'unrealized_pnl': -30, 'win_rate': 0.44},
        }}
    }
    ingest_research_note(research, note_type='macro', title='Liquidity stable', content='Depth remains healthy and trend breadth improving.', market='equities', regime_tag='trend', confidence=0.74)
    ingest_research_note(research, note_type='risk', title='Volatility contained', content='Cross-asset volatility remains below panic thresholds.', market='equities', regime_tag='calm', confidence=0.68)
    for _ in range(3):
        ingest_attribution_event(perf, strategy_id='strat_aapl', strategy_name='AAPL Momentum', pnl=280, capital_used=11000, trades=4, win_rate=0.62, confidence=0.72)
        ingest_attribution_event(perf, strategy_id='strat_spy', strategy_name='SPY Mean Revert', pnl=-40, capital_used=9000, trades=3, win_rate=0.44, confidence=0.58)
    snapshot = build_regime_snapshot(research, market='equities', volatility_bps=110, breadth=0.67, liquidity_score=0.76, trend_score=0.74, macro_score=0.61, operator_state=operator_state, performance_state=perf, portfolio_risk=risk)
    assert snapshot['regime_label'] in ('trend_expansion', 'balanced')
    result = evaluate_regime_allocator(research, market='equities', volatility_bps=110, breadth=0.67, liquidity_score=0.76, trend_score=0.74, macro_score=0.61, operator_state=operator_state, performance_state=perf, allocator_state=allocator, portfolio_risk=risk)
    assert result['status'] == 'ok'
    assert len(result['adjustments']) == 2
    assert any(x['action'] in ('increase', 'decrease', 'hold') for x in result['adjustments'])
    print('QNT30358 smoke test passed')


if __name__ == '__main__':
    main()
