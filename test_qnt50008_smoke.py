from backend.app.treasury_cash_mobility.engine import TreasuryCashMobilityEngine
from backend.app.settlement_reconciliation.state_store import load_state as load_settlement_state, save_state as save_settlement_state


def main():
    settlement = load_settlement_state()
    settlement['cash_balance'] = 120000.0
    settlement['pending_settlements'] = []
    settlement['settled_settlements'] = []
    settlement['reconciliation_breaks'] = []
    settlement['last_reconciliation'] = {'status': 'matched'}
    save_settlement_state(settlement)

    engine = TreasuryCashMobilityEngine()
    engine.reset({'operator': 'smoke_test', 'reason': 'smoke_test_reset', 'clear_audit': True})
    sync = engine.sync_settlement_context({'source': 'smoke_test'})
    assert sync['snapshot']['cash_balance'] == 120000.0

    staged = engine.stage_transfer({
        'operator': 'smoke_test',
        'decision_id': 'smoke_decision',
        'transfer_type': 'broker_funding',
        'from_account': 'broker_buffer',
        'destination': 'IBKR',
        'amount': 12000.0,
        'currency': 'USD',
        'priority': 'high',
        'purpose': 'smoke test broker funding',
    })
    transfer_id = staged['transfer']['transfer_id']
    assert staged['status'] in {'staged', 'review'}

    approved = engine.approve_transfer({'transfer_id': transfer_id, 'approver': 'risk_committee'})
    assert approved['status'] == 'approved'

    executed = engine.execute_transfer({'transfer_id': transfer_id, 'operator': 'treasury_ops'})
    assert executed['status'] == 'executed'
    summary = engine.summary()
    assert summary['completed_transfer_count'] >= 1
    assert summary['cash_balance'] == 120000.0
    print('QNT50008 smoke test passed')


if __name__ == '__main__':
    main()
