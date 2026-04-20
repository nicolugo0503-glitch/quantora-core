from backend.app.execution.fill_handler import load_state as load_execution_state, save_state as save_execution_state
from backend.app.execution.order_router import OrderRouter
from backend.app.risk_control.engine import RiskKillSwitchEngine
from backend.app.risk_control.state_store import load_state as load_risk_state, save_state as save_risk_state


def main():
    engine = RiskKillSwitchEngine()

    risk = load_risk_state()
    risk['kill_switch_triggered'] = False
    risk['trigger_reason'] = None
    risk['active_breaches'] = []
    risk['armed'] = True
    risk['metrics']['portfolio_drawdown_pct'] = 0.0
    risk['metrics']['daily_loss_pct'] = 0.0
    risk['metrics']['open_notional'] = 0.0
    risk['blocked_orders'] = []
    save_risk_state(risk)

    execution = load_execution_state()
    execution['mode'] = 'paper'
    execution['safe_mode'] = True
    execution['active_broker'] = 'paper'
    execution['locked'] = False
    save_state = save_execution_state
    save_state(execution)

    result = engine.update_metrics({
        'peak_equity': 1000000,
        'equity': 870000,
        'portfolio_drawdown_pct': 0.13,
        'daily_loss_pct': 0.01,
    })
    assert result['status'] == 'triggered'

    try:
        OrderRouter().route({
            'symbol': 'BTCUSDT',
            'side': 'BUY',
            'qty': 1,
            'price': 100,
            'strategy_id': 'alpha_trend',
            'allocation_id': 'alloc_smoke',
            'risk_tag': 'SMOKE',
            'decision_id': 'dec_smoke',
            'order_type': 'LIMIT',
        })
        raise AssertionError('kill switch should block order routing')
    except PermissionError:
        pass

    engine.override({
        'approver': 'smoke_test',
        'ticket_id': 'OVR-50004',
        'reason': 'controlled release',
        'keep_armed': True,
    })
    engine.update_metrics({
        'peak_equity': 1000000,
        'equity': 995000,
        'portfolio_drawdown_pct': 0.005,
        'daily_loss_pct': 0.001,
        'open_notional': 0.0,
        'largest_position_pct': 0.0,
        'margin_usage_pct': 0.0,
        'venue_connectivity_ok': True,
    })

    routed = OrderRouter().route({
        'symbol': 'BTCUSDT',
        'side': 'BUY',
        'qty': 1,
        'price': 100,
        'strategy_id': 'alpha_trend',
        'allocation_id': 'alloc_smoke',
        'risk_tag': 'SMOKE',
        'decision_id': 'dec_smoke_2',
        'order_type': 'LIMIT',
    })
    assert routed['status'] == 'filled'
    print('QNT50004 smoke passed')


if __name__ == '__main__':
    main()
