from backend.app.live_strategy_scale_up.engine import LiveStrategyScaleUpEngine
from backend.app.live_capital_reactivation.engine import LiveCapitalReactivationEngine
from backend.app.post_recovery_capital_reinstatement.engine import PostRecoveryCapitalReinstatementEngine
from backend.app.performance_engine.state_store import load_state as load_perf_state, save_state as save_perf_state
from backend.app.risk_control.state_store import load_state as load_risk_state, save_state as save_risk_state
from backend.app.strategy_deployment.state_store import load_state as load_strategy_state, save_state as save_strategy_state
from backend.app.treasury_cash_mobility.state_store import load_state as load_treasury_state, save_state as save_treasury_state


def prime_context():
    risk = load_risk_state()
    risk['kill_switch_triggered'] = False
    risk['kill_switch_level'] = 'normal'
    save_risk_state(risk)

    treasury = load_treasury_state()
    treasury.setdefault('accounts', {})['operating'] = {'currency': 'USD', 'balance': 30000.0}
    treasury.setdefault('accounts', {})['broker_buffer'] = {'currency': 'USD', 'balance': 40000.0}
    treasury.setdefault('accounts', {})['custody_reserve'] = {'currency': 'USD', 'balance': 15000.0}
    save_treasury_state(treasury)

    strategy = load_strategy_state()
    strategy['safe_mode'] = True
    strategy['execution_mode'] = 'paper'
    profiles = strategy.get('deployment_profiles') or []
    found = False
    for profile in profiles:
        if profile.get('strategy_id') == 'alpha_trend':
            profile['status'] = 'active'
            profile['enabled'] = True
            found = True
    if not found:
        profiles.append({
            'strategy_id': 'alpha_trend',
            'symbol': 'BTCUSDT',
            'allowed_brokers': ['paper', 'binance'],
            'enabled': True,
            'status': 'active',
        })
        strategy['deployment_profiles'] = profiles
    save_strategy_state(strategy)

    perf = load_perf_state()
    perf['returns'] = [{'date': '2026-04-18', 'net_return': 0.0125}]
    save_perf_state(perf)

    reauth = PostRecoveryCapitalReinstatementEngine()
    reauth.reset({'operator': 'smoke', 'reason': 'qnt50030_smoke'})
    reauth_case = reauth.register_reauthorization({
        'operator': 'smoke',
        'title': 'Seed post-recovery reinstatement',
        'action_id': 'action_smoke_qnt50030',
        'cycle_id': 'cycle_smoke_qnt50030',
        'requested_capital': 16000.0,
        'reinstatement_pct': 60.0,
        'rationale': 'seed for scale-up governance test',
    })['reauthorization']
    reauth.approve_reinstatement({
        'operator': 'smoke',
        'reauthorization_id': reauth_case['reauthorization_id'],
        'approved_capital': 15000.0,
        'approval_notes': 'approved for paper re-entry',
    })
    reauth.execute_reinstatement({
        'operator': 'smoke',
        'reauthorization_id': reauth_case['reauthorization_id'],
        'execution_mode': 'controlled',
        'capital_reinstated': 15000.0,
        'destination_account': 'broker_buffer',
        'result_summary': 'seeded for scale-up path',
    })

    reentry = LiveCapitalReactivationEngine()
    reentry.reset({'operator': 'smoke', 'reason': 'qnt50030_smoke'})
    reentry.sync_context({'source': 'smoke'})
    reactivation = reentry.register_reactivation({
        'operator': 'smoke',
        'title': 'Reactivate alpha trend',
        'reauthorization_id': reauth_case['reauthorization_id'],
        'strategy_id': 'alpha_trend',
        'requested_capital': 10000.0,
        'requested_weight': 0.10,
        'reentry_reason': 'controlled resumption after recovery',
    })['reactivation']
    reentry.approve_reentry({
        'operator': 'smoke',
        'reactivation_id': reactivation['reactivation_id'],
        'approved_capital': 9500.0,
        'approved_weight': 0.09,
        'mode': 'paper',
        'approval_notes': 'paper mode only while safe mode remains enabled',
    })
    event = reentry.execute_reentry({
        'operator': 'smoke',
        'reactivation_id': reactivation['reactivation_id'],
        'execution_mode': 'paper',
        'capital_activated': 9500.0,
        'release_to': 'execution_queue',
        'result_summary': 'paper re-entry activated',
    })['event']
    return event['event_id']


def run_smoke():
    reentry_event_id = prime_context()
    engine = LiveStrategyScaleUpEngine()
    engine.reset({'operator': 'smoke', 'reason': 'qnt50030_smoke'})
    engine.sync_context({'source': 'smoke'})

    scale_case = engine.register_scale_case({
        'operator': 'smoke',
        'title': 'Scale alpha trend after controlled re-entry',
        'reentry_event_id': reentry_event_id,
        'strategy_id': 'alpha_trend',
        'current_capital': 9500.0,
        'requested_ramp_capital': 4000.0,
        'requested_target_weight': 0.13,
        'ramp_steps': 3,
        'max_ramp_pct': 0.2,
        'ramp_reason': 'controlled increase after stable restart',
    })['scale_case']
    assert scale_case['status'] == 'registered'

    approved = engine.approve_ramp({
        'operator': 'smoke',
        'scale_case_id': scale_case['scale_case_id'],
        'approved_ramp_capital': 3500.0,
        'approved_target_weight': 0.125,
        'mode': 'paper',
        'approval_notes': 'paper-only ramp while safe mode remains enabled',
    })
    assert approved['status'] == 'approved'

    executed = engine.execute_ramp({
        'operator': 'smoke',
        'scale_case_id': scale_case['scale_case_id'],
        'execution_mode': 'paper',
        'ramp_capital_deployed': 3500.0,
        'target_weight': 0.125,
        'release_to': 'allocation_engine',
        'result_summary': 'paper scale-up applied',
    })
    assert executed['status'] == 'executed'

    closed = engine.close_scale_case({
        'operator': 'smoke',
        'scale_case_id': scale_case['scale_case_id'],
        'closure_notes': 'paper scale-up completed',
    })
    assert closed['status'] == 'closed'

    summary = engine.summary()
    assert summary['ramp_event_count'] >= 1
    return summary


if __name__ == '__main__':
    print(run_smoke())
