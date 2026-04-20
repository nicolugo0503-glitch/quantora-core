
from backend.app.autonomous_control_loop.engine import AutonomousControlLoopEngine
from backend.app.autonomous_control_loop.state_store import load_state


def main():
    engine = AutonomousControlLoopEngine()
    engine.reset({'operator': 'smoke_test', 'reason': 'qnt50022_smoke'})
    engine.configure({
        'enabled': True,
        'auto_sync_sources': True,
        'auto_ingest_release_queue': True,
        'require_risk_clearance': False,
        'require_liquidity_capacity': True,
        'minimum_available_liquidity': 1000.0,
        'sync_after_configure': True,
    })
    engine.sync_context({'source': 'smoke'})
    plan = engine.plan_loop({
        'operator': 'smoke_test',
        'source': 'smoke',
        'queue_index': 0,
        'max_orders': 1,
        'cycle_notional_limit': 50000.0,
        'market_prices': {'BTCUSD': 50000.0, 'ETHUSD': 2500.0, 'USDTUSD': 1.0},
    })
    assert plan['plan']['plan_id']
    cycle = engine.execute_loop({
        'operator': 'smoke_test',
        'source': 'smoke',
        'use_latest_plan': True,
        'market_prices': {'BTCUSD': 50000.0, 'ETHUSD': 2500.0, 'USDTUSD': 1.0},
    })
    state = load_state()
    assert state['control_plans']
    assert state['control_cycles']
    print('QNT50022 smoke passed:', cycle['status'])


if __name__ == '__main__':
    main()
