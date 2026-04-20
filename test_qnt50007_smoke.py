from backend.app.execution.fill_handler import load_state as load_execution_state, save_state as save_execution_state
from backend.app.settlement_reconciliation.engine import SettlementReconciliationEngine
from backend.app.settlement_reconciliation.state_store import default_state, load_state, save_state


def main():
    save_state(default_state())
    execution = load_execution_state()
    execution['fills'] = [
        {
            'recorded_at': 1763330000,
            'strategy_id': 'alpha_trend',
            'allocation_id': 'alloc_smoke_001',
            'decision_id': 'decision_smoke_001',
            'risk_tag': 'AUTO_EXEC',
            'broker': 'paper',
            'order_id': 'order_smoke_buy_001',
            'symbol': 'BTCUSDT',
            'side': 'BUY',
            'filled_qty': 0.5,
            'fill_price': 60000.0,
            'status': 'FILLED',
            'executed_at': 1763330000,
        }
    ]
    execution['orders'] = []
    save_execution_state(execution)

    engine = SettlementReconciliationEngine()
    ingest = engine.ingest_execution_fills({'auto_process': False})
    assert ingest['inserted_count'] == 1

    pending = load_state()['pending_settlements']
    assert len(pending) == 1
    settlement_id = pending[0]['settlement_id']

    confirm = engine.confirm_settlement({
        'settlement_ids': [settlement_id],
        'operator': 'smoke_ops',
        'cash_confirmed': True,
        'custody_confirmed': True,
        'notes': 'smoke confirmation',
    })
    assert confirm['settled_count'] == 1
    state = load_state()
    assert state['positions']['BTCUSDT'] == 0.5
    assert state['cash_balance'] == -30000.0

    matched = engine.reconcile({
        'broker_positions': {'BTCUSDT': 0.5},
        'broker_cash_balance': -30000.0,
        'operator': 'smoke_ops',
        'auto_ingest': False,
    })
    assert matched['status'] == 'matched'

    broken = engine.reconcile({
        'broker_positions': {'BTCUSDT': 0.4},
        'broker_cash_balance': -29900.0,
        'operator': 'smoke_ops',
        'auto_ingest': False,
    })
    assert broken['status'] == 'breaks_detected'
    assert broken['break_count'] >= 2
    print('QNT50007 smoke passed')


if __name__ == '__main__':
    main()
