from backend.app.performance_engine.engine import PerformanceEngine
from backend.app.performance_engine.state_store import default_state, save_state, load_state
from backend.app.risk_control.state_store import load_state as load_risk_state


def main():
    save_state(default_state())
    engine = PerformanceEngine()
    baseline = engine.recompute({'sync_risk': True})
    assert baseline['metrics']['sharpe_ratio'] is not None
    assert baseline['metrics']['max_drawdown_pct'] >= 0.0

    result = engine.register_nav_snapshot({
        'as_of_date': '2026-04-18',
        'equity': 1042000,
        'gross_exposure_pct': 0.42,
        'net_exposure_pct': 0.25,
        'strategy_attribution': [
            {'strategy_id': 'alpha_trend', 'pnl': 8800, 'return_contribution_pct': 0.0088, 'gross_exposure_pct': 0.19},
            {'strategy_id': 'beta_mean_revert', 'pnl': 1600, 'return_contribution_pct': 0.0016, 'gross_exposure_pct': 0.13},
            {'strategy_id': 'macro_defense', 'pnl': -400, 'return_contribution_pct': -0.0004, 'gross_exposure_pct': 0.10},
        ],
    })
    assert result['snapshot_count'] >= 6
    assert result['metrics']['annualized_volatility_pct'] >= 0.0
    assert len(result['strategy_attribution']) >= 3

    perf_state = load_state()
    risk_state = load_risk_state()
    assert perf_state['investor_metrics']['latest_equity'] == 1042000.0
    assert risk_state['metrics']['equity'] == 1042000.0
    print('QNT50005 smoke passed')


if __name__ == '__main__':
    main()
