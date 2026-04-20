from backend.app.multi_fund_expansion.engine import MultiFundExpansionEngine
from backend.app.live_allocation_escalation.state_store import save_state as save_allocation_state, default_state as default_allocation_state
from backend.app.risk_control.state_store import save_state as save_risk_state, default_state as default_risk_state
from backend.app.treasury_cash_mobility.state_store import save_state as save_treasury_state, default_state as default_treasury_state
from backend.app.institutional_allocation_execution_charter.state_store import save_state as save_charter_state, default_state as default_charter_state
from backend.app.multi_fund_expansion.state_store import save_state as save_state, default_state as default_state


def reset_dependencies():
    allocation = default_allocation_state()
    allocation['escalation_events'] = [{
        'escalation_event_id': 'esc_evt_001',
        'status': 'executed',
        'strategy_id': 'stat_1',
        'symbol': 'BTCUSDT',
        'broker': 'paper',
    }]
    save_allocation_state(allocation)

    risk = default_risk_state()
    risk['summary'] = {
        'kill_switch_triggered': False,
        'kill_switch_armed': False,
        'kill_switch_level': 'normal',
        'safe_mode': False,
        'execution_mode': 'live',
    }
    save_risk_state(risk)

    treasury = default_treasury_state()
    treasury['cash_balances'] = {'operating': 5000000.0}
    save_treasury_state(treasury)

    charter = default_charter_state()
    charter['directives'] = [{
        'directive_id': 'dir_001',
        'status': 'approved',
    }]
    save_charter_state(charter)

    save_state(default_state())


def test_qnt50033_smoke():
    reset_dependencies()
    engine = MultiFundExpansionEngine()
    sync = engine.sync_context({'source': 'test'})
    assert sync['status'] == 'synced'

    registered = engine.register_launch_case({
        'operator': 'qa',
        'vehicle_name': 'Quantora Global Expansion I',
        'vehicle_type': 'fund',
        'jurisdiction': 'Cayman',
        'launch_reason': 'capacity expansion',
        'strategy_scope': 'multi-strategy',
        'seed_capital_required': 1000000,
        'target_capacity_pct': 0.3,
        'launch_mode': 'paper',
    })
    case_id = registered['launch_case']['launch_case_id']
    assert registered['status'] == 'registered'

    approved = engine.approve_launch({
        'operator': 'qa',
        'launch_case_id': case_id,
        'approved_seed_capital': 1000000,
        'approved_vehicle_code': 'QGE1',
        'approval_mode': 'paper',
    })
    assert approved['status'] == 'approved'

    executed = engine.execute_launch({
        'operator': 'qa',
        'launch_case_id': case_id,
        'execution_mode': 'paper',
        'vehicle_code': 'QGE1',
        'seed_capital_deployed': 1000000,
    })
    assert executed['status'] == 'executed'

    closed = engine.close_launch_case({
        'operator': 'qa',
        'launch_case_id': case_id,
        'closure_notes': 'smoke complete',
    })
    assert closed['status'] == 'closed'
