from backend.app.live_capital_reactivation.engine import LiveCapitalReactivationEngine
from backend.app.post_recovery_capital_reinstatement.engine import PostRecoveryCapitalReinstatementEngine
from backend.app.risk_control.state_store import load_state as load_risk_state, save_state as save_risk_state
from backend.app.strategy_deployment.state_store import load_state as load_strategy_state, save_state as save_strategy_state
from backend.app.treasury_cash_mobility.state_store import load_state as load_treasury_state, save_state as save_treasury_state


def prime_context():
    risk = load_risk_state()
    risk['kill_switch_triggered'] = False
    risk['kill_switch_level'] = 'normal'
    save_risk_state(risk)

    treasury = load_treasury_state()
    treasury.setdefault('accounts', {})['operating'] = {'currency': 'USD', 'balance': 20000.0}
    treasury.setdefault('accounts', {})['broker_buffer'] = {'currency': 'USD', 'balance': 25000.0}
    treasury.setdefault('accounts', {})['custody_reserve'] = {'currency': 'USD', 'balance': 15000.0}
    save_treasury_state(treasury)

    strategy = load_strategy_state()
    strategy['safe_mode'] = True
    strategy['execution_mode'] = 'paper'
    profiles = strategy.get('deployment_profiles') or []
    found = False
    for profile in profiles:
        if profile.get('strategy_id') == 'alpha_trend':
            profile['status'] = 'standby'
            profile['enabled'] = True
            found = True
    if not found:
        profiles.append({
            'strategy_id': 'alpha_trend',
            'symbol': 'BTCUSDT',
            'allowed_brokers': ['paper', 'binance'],
            'enabled': True,
            'status': 'standby',
        })
        strategy['deployment_profiles'] = profiles
    save_strategy_state(strategy)

    reauth = PostRecoveryCapitalReinstatementEngine()
    reauth.reset({'operator': 'smoke', 'reason': 'qnt50029_smoke'})
    case = reauth.register_reauthorization({
        'operator': 'smoke',
        'title': 'Seed post-recovery reinstatement',
        'action_id': 'action_smoke_qnt50029',
        'cycle_id': 'cycle_smoke_qnt50029',
        'requested_capital': 12000.0,
        'reinstatement_pct': 50.0,
        'rationale': 'seed for re-entry governance test',
    })['reauthorization']
    reauth.approve_reinstatement({
        'operator': 'smoke',
        'reauthorization_id': case['reauthorization_id'],
        'approved_capital': 11000.0,
        'approval_notes': 'approved for paper re-entry',
    })
    reauth.execute_reinstatement({
        'operator': 'smoke',
        'reauthorization_id': case['reauthorization_id'],
        'execution_mode': 'controlled',
        'capital_reinstated': 11000.0,
        'destination_account': 'broker_buffer',
        'result_summary': 'seeded for re-entry',
    })
    return case['reauthorization_id']


def run_smoke():
    reauthorization_id = prime_context()
    engine = LiveCapitalReactivationEngine()
    engine.reset({'operator': 'smoke', 'reason': 'qnt50029_smoke'})
    engine.sync_context({'source': 'smoke'})

    reactivation = engine.register_reactivation({
        'operator': 'smoke',
        'title': 'Reactivate alpha trend',
        'reauthorization_id': reauthorization_id,
        'strategy_id': 'alpha_trend',
        'requested_capital': 9000.0,
        'requested_weight': 0.09,
        'reentry_reason': 'controlled resumption after recovery',
    })['reactivation']
    assert reactivation['status'] == 'registered'

    approved = engine.approve_reentry({
        'operator': 'smoke',
        'reactivation_id': reactivation['reactivation_id'],
        'approved_capital': 8500.0,
        'approved_weight': 0.08,
        'mode': 'paper',
        'approval_notes': 'paper mode only while safe mode remains enabled',
    })
    assert approved['status'] == 'approved'

    executed = engine.execute_reentry({
        'operator': 'smoke',
        'reactivation_id': reactivation['reactivation_id'],
        'execution_mode': 'paper',
        'capital_activated': 8500.0,
        'release_to': 'execution_queue',
        'result_summary': 'paper re-entry activated',
    })
    assert executed['status'] == 'executed'

    closed = engine.close_reactivation({
        'operator': 'smoke',
        'reactivation_id': reactivation['reactivation_id'],
        'closure_notes': 'paper strategy re-entry completed',
    })
    assert closed['status'] == 'closed'

    summary = engine.summary()
    assert summary['reentry_event_count'] >= 1
    return summary


if __name__ == '__main__':
    print(run_smoke())
