from backend.app.investor_cash_confirmation.engine import InvestorCashConfirmationEngine
from backend.app.treasury_cash_mobility.engine import TreasuryCashMobilityEngine
from backend.app.settlement_reconciliation.state_store import load_state as load_settlement_state, save_state as save_settlement_state


def main():
    settlement = load_settlement_state()
    settlement['cash_balance'] = 150000.0
    settlement['pending_settlements'] = []
    settlement['settled_settlements'] = []
    settlement['reconciliation_breaks'] = []
    settlement['last_reconciliation'] = {'status': 'matched'}
    save_settlement_state(settlement)

    treasury = TreasuryCashMobilityEngine()
    treasury.reset({'operator': 'smoke_test', 'reason': 'qnt50009_smoke', 'clear_audit': True})
    treasury.sync_settlement_context({'source': 'smoke_test'})

    investor = InvestorCashConfirmationEngine()
    investor.reset({'operator': 'smoke_test', 'reason': 'qnt50009_smoke', 'clear_audit': True})
    investor.register_investor({
        'investor_id': 'INVESTOR_001',
        'investor_name': 'Investor One',
        'bank_instruction_verified': True,
        'statement_alignment_status': 'aligned',
        'preferred_currency': 'USD',
    })

    staged = treasury.stage_transfer({
        'operator': 'smoke_test',
        'decision_id': 'investor_release_smoke',
        'transfer_type': 'investor_redemption',
        'from_account': 'broker_buffer',
        'destination': 'investor_settlement',
        'amount': 12000.0,
        'currency': 'USD',
        'priority': 'high',
        'purpose': 'smoke test investor redemption',
        'investor_id': 'INVESTOR_001',
        'capital_activity_id': 'RED_001',
        'statement_cycle_id': 'APR_2026',
    })
    transfer_id = staged['transfer']['transfer_id']
    treasury.approve_transfer({'transfer_id': transfer_id, 'approver': 'treasury_committee'})

    blocked = None
    try:
        treasury.execute_transfer({'transfer_id': transfer_id, 'operator': 'treasury_ops'})
    except ValueError as exc:
        blocked = str(exc)
    assert blocked and 'release authority' in blocked.lower()

    requested = investor.request_release({
        'operator': 'investor_ops',
        'transfer_id': transfer_id,
        'investor_id': 'INVESTOR_001',
        'dealing_reference': 'RED_001',
        'statement_cycle_id': 'APR_2026',
    })
    release_request_id = requested['release_request']['release_request_id']
    investor.acknowledge({'release_request_id': release_request_id, 'actor': 'investor_ops', 'ack_type': 'ops'})
    investor.acknowledge({'release_request_id': release_request_id, 'actor': 'investor_contact', 'ack_type': 'investor'})
    authority = investor.authorize_release({'release_request_id': release_request_id, 'approver': 'release_committee'})
    assert authority['status'] == 'authorized'

    executed = treasury.execute_transfer({'transfer_id': transfer_id, 'operator': 'treasury_ops'})
    assert executed['status'] == 'executed'
    summary = investor.summary()
    assert summary['authorized_release_count'] >= 1
    print('QNT50009 smoke test passed')


if __name__ == '__main__':
    main()
