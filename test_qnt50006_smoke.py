from backend.app.allocation.engine import AllocationEngine
from backend.app.allocation.state_store import default_state as allocation_default_state, save_state as save_allocation_state
from backend.app.autonomous_execution.engine import AutonomousExecutionEngine
from backend.app.autonomous_execution.state_store import default_state as auto_default_state, load_state as load_auto_state, save_state as save_auto_state
from backend.app.execution.fill_handler import load_state as load_execution_state, save_state as save_execution_state
from backend.app.performance_engine.engine import PerformanceEngine
from backend.app.performance_engine.state_store import default_state as perf_default_state, save_state as save_perf_state
from backend.app.risk_control.state_store import load_state as load_risk_state, save_state as save_risk_state
from backend.app.strategy_deployment.engine import StrategyDeploymentEngine
from backend.app.strategy_deployment.state_store import default_state as deployment_default_state, save_state as save_deployment_state


def main():
    save_allocation_state(allocation_default_state())
    save_deployment_state(deployment_default_state())
    save_perf_state(perf_default_state())
    save_auto_state(auto_default_state())

    risk = load_risk_state()
    risk['kill_switch_triggered'] = False
    risk['active_breaches'] = []
    risk['armed'] = True
    risk['metrics']['portfolio_drawdown_pct'] = 0.01
    risk['metrics']['daily_loss_pct'] = 0.001
    save_risk_state(risk)

    execution = load_execution_state()
    execution['mode'] = 'paper'
    execution['safe_mode'] = True
    execution['active_broker'] = 'paper'
    save_execution_state(execution)

    AllocationEngine().recommend({'capital': 1000000, 'regime': 'neutral', 'liquidity_state': 'normal'})
    AllocationEngine().approve({'approver': 'smoke_committee', 'notes': 'approved'})
    StrategyDeploymentEngine().evaluate({})
    StrategyDeploymentEngine().deploy({'approver': 'smoke_committee', 'notes': 'deploy approved'})
    PerformanceEngine().recompute({'sync_risk': True})

    engine = AutonomousExecutionEngine()
    ingest = engine.ingest_release_queue({'queue_index': 0, 'clear_existing': True})
    assert ingest['inserted_count'] >= 1

    engine.configure({'enabled': True, 'auto_execute_paper': True, 'minimum_sharpe_ratio': -1.0})
    plan = engine.plan_cycle({'market_prices': {'BTCUSDT': 65000, 'ETHUSDT': 3200, 'USDTUSD': 1.0}})
    assert plan['status'] in {'ready', 'blocked', 'empty'}
    assert len(plan['planned_orders']) >= 1

    result = engine.execute_cycle({'market_prices': {'BTCUSDT': 65000, 'ETHUSDT': 3200, 'USDTUSD': 1.0}, 'approver': 'smoke_auto'})
    assert result['status'] in {'completed', 'partial', 'escalated'}
    state = load_auto_state()
    assert state['last_cycle'] is not None
    assert len(state['cycle_history']) >= 1
    print('QNT50006 smoke passed')


if __name__ == '__main__':
    main()
