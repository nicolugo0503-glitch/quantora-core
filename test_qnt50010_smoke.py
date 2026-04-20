from backend.app.investor_cash_confirmation.engine import InvestorCashConfirmationEngine
from backend.app.investor_exit_finalization.engine import InvestorExitFinalizationEngine
from backend.app.settlement_reconciliation.state_store import load_state as load_settlement_state, save_state as save_settlement_state
from backend.app.treasury_cash_mobility.engine import TreasuryCashMobilityEngine


def main():
    settlement = load_settlement_state()
    settlement['cash_balance'] = 150000.0
    settlement['pending_settlements'] = []
    settlement['settled_settlements'] = []
    settlement['reconciliation_breaks'] = []
    settlement['last_reconciliation'] = {'status': 'matched'}
    save_settlement_state(settlement)

    treasury = TreasuryCashMobilityEngine()
    treasury.reset({'operator': 'smoke_test', 'reason': 'qnt50010_smoke', 'clear_audit': True})
    treasury.sync_settlement_context({'source': 'smoke_test'})

    investor = InvestorCashConfirmationEngine()
    investor.reset({'operator': 'smoke_test', 'reason': 'qnt50010_smoke', 'clear_audit': True})
    investor.register_investor({
        'investor_id': 'INVESTOR_001',
        'investor_name': 'Investor One',
        'bank_instruction_verified': True,
        'statement_alignment_status': 'aligned',
        'preferred_currency': 'USD',
    })

    transfer = treasury.stage_transfer({
        'operator': 'smoke_test',
        'decision_id': 'investor_exit_smoke',
        'transfer_type': 'investor_redemption',
        'from_account': 'broker_buffer',
        'destination': 'investor_settlement',
        'amount': 12000.0,
        'currency': 'USD',
        'priority': 'high',
        'purpose': 'smoke test investor exit',
        'investor_id': 'INVESTOR_001',
        'capital_activity_id': 'RED_002',
        'statement_cycle_id': 'APR_2026',
    })['transfer']
    treasury.approve_transfer({'transfer_id': transfer['transfer_id'], 'approver': 'treasury_committee'})

    requested = investor.request_release({
        'operator': 'investor_ops',
        'transfer_id': transfer['transfer_id'],
        'investor_id': 'INVESTOR_001',
        'dealing_reference': 'RED_002',
        'statement_cycle_id': 'APR_2026',
    })
    request_id = requested['release_request']['release_request_id']
    investor.acknowledge({'release_request_id': request_id, 'actor': 'investor_ops', 'ack_type': 'ops'})
    investor.acknowledge({'release_request_id': request_id, 'actor': 'investor_contact', 'ack_type': 'investor'})
    investor.authorize_release({'release_request_id': request_id, 'approver': 'release_committee'})
    treasury.execute_transfer({'transfer_id': transfer['transfer_id'], 'operator': 'treasury_ops'})

    exit_engine = InvestorExitFinalizationEngine()
    exit_engine.reset({'operator': 'smoke_test', 'reason': 'qnt50010_smoke', 'clear_audit': True})
    case = exit_engine.register_case({
        'operator': 'investor_ops',
        'transfer_id': transfer['transfer_id'],
        'investor_id': 'INVESTOR_001',
        'gross_redemption_amount': 12000.0,
        'cash_paid_amount': 12000.0,
        'statement_cycle_id': 'APR_2026',
        'dealing_reference': 'RED_002',
    })['case']
    exit_engine.attest({'case_id': case['case_id'], 'actor': 'investor_ops', 'attestation_type': 'ops'})
    exit_engine.attest({'case_id': case['case_id'], 'actor': 'investor_contact', 'attestation_type': 'investor'})
    exit_engine.attest({'case_id': case['case_id'], 'actor': 'recon_control', 'attestation_type': 'reconciliation'})
    auth = exit_engine.authorize_finalization({'case_id': case['case_id'], 'approver': 'exit_committee'})
    assert auth['status'] == 'authorized'
    final = exit_engine.finalize({'case_id': case['case_id'], 'operator': 'fund_admin'})
    assert final['status'] == 'finalized'
    summary = exit_engine.summary()
    assert summary['finalized_exit_count'] >= 1
    print('QNT50010 smoke test passed')


if __name__ == '__main__':
    main()
