from backend.app.live_strategy_scale_up.state_store import save_state as save_scale_state
from backend.app.live_allocation_escalation.state_store import save_state as save_state, load_state
from backend.app.live_allocation_escalation.engine import LiveAllocationEscalationEngine
from backend.app.risk_control.state_store import save_state as save_risk_state
from backend.app.treasury_cash_mobility.state_store import save_state as save_treasury_state
from backend.app.performance_engine.state_store import save_state as save_performance_state
from backend.app.institutional_allocation_execution_charter.state_store import save_state as save_charter_state


def main():
    save_state({
        'generated_by': 'QNT50031',
        'status': 'degraded',
        'policy': {
            'enabled': True,
            'auto_sync_sources': True,
            'require_scale_execution': True,
            'require_risk_clearance': True,
            'require_capacity_headroom': True,
            'require_charter_alignment': False,
            'allow_live_escalation': False,
            'default_capacity_ceiling_pct': 0.4,
            'default_escalation_step_pct': 0.05,
            'max_escalation_cases': 250,
            'max_escalation_events': 500,
            'max_audit_events': 500,
        },
        'last_sync': None,
        'sync_history': [],
        'escalation_cases': [],
        'escalation_events': [],
        'audit_log': [],
    })
    save_scale_state({
        'generated_by': 'QNT50030',
        'status': 'degraded',
        'policy': {},
        'last_sync': {
            'current_regime': 'neutral'
        },
        'sync_history': [],
        'scale_cases': [],
        'ramp_events': [{
            'ramp_event_id': 'ramp_event_smoke_1',
            'status': 'executed',
            'symbol': 'BTCUSDT',
            'broker': 'binance',
            'target_weight': 0.12,
        }],
        'audit_log': [],
    })
    save_risk_state({
        'safe_mode': True,
        'execution_mode': 'paper',
        'summary': {'kill_switch_triggered': False, 'kill_switch_level': 'normal'}
    })
    save_treasury_state({'balances': {'broker_buffer': 50000, 'operating': 30000}})
    save_performance_state({'returns': [{'net_return': 0.011}]})
    save_charter_state({'directives': [{'directive_id': 'dir_smoke_1', 'status': 'active'}]})

    engine = LiveAllocationEscalationEngine()
    sync = engine.sync_context({'source': 'smoke'})
    assert sync['status'] == 'synced'

    registered = engine.register_escalation_case({
        'operator': 'smoke',
        'title': 'Escalate allocation after successful ramp',
        'scale_event_id': 'ramp_event_smoke_1',
        'strategy_id': 'alpha_trend',
        'requested_total_weight': 0.18,
        'requested_incremental_capital': 2500,
        'capacity_ceiling_pct': 0.2,
        'allocation_reason': 'post-ramp controlled escalation',
    })
    case_id = registered['escalation_case']['escalation_case_id']

    try:
        engine.approve_escalation({
            'operator': 'smoke',
            'escalation_case_id': case_id,
            'approved_total_weight': 0.18,
            'approved_incremental_capital': 2000,
            'mode': 'live',
        })
        raise AssertionError('live approval should be blocked while safe mode is enabled')
    except ValueError as exc:
        assert 'safe mode' in str(exc)

    approved = engine.approve_escalation({
        'operator': 'smoke',
        'escalation_case_id': case_id,
        'approved_total_weight': 0.18,
        'approved_incremental_capital': 2000,
        'mode': 'paper',
    })
    assert approved['status'] == 'approved'

    executed = engine.execute_escalation({
        'operator': 'smoke',
        'escalation_case_id': case_id,
        'execution_mode': 'paper',
        'incremental_capital_deployed': 2000,
        'total_weight': 0.18,
        'result_summary': 'paper escalation applied',
    })
    assert executed['status'] == 'executed'

    closed = engine.close_escalation_case({
        'operator': 'smoke',
        'escalation_case_id': case_id,
        'closure_notes': 'smoke close',
    })
    assert closed['status'] == 'closed'

    state = load_state()
    assert state['escalation_events'][0]['status'] == 'executed'
    assert state['escalation_cases'][0]['status'] == 'closed'
    print('QNT50031 smoke test passed')


if __name__ == '__main__':
    main()
