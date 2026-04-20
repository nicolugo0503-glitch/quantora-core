from backend.app.investor_cash_confirmation.engine import InvestorCashConfirmationEngine
from backend.app.investor_distribution_payables.engine import InvestorDistributionPayablesEngine
from backend.app.performance_engine.state_store import load_state as load_performance_state, save_state as save_performance_state
from backend.app.settlement_reconciliation.state_store import load_state as load_settlement_state, save_state as save_settlement_state
from backend.app.treasury_cash_mobility.engine import TreasuryCashMobilityEngine


def main():
    settlement = load_settlement_state()
    settlement['cash_balance'] = 300000.0
    settlement['pending_settlements'] = []
    settlement['settled_settlements'] = []
    settlement['reconciliation_breaks'] = []
    settlement['last_reconciliation'] = {'status': 'matched'}
    save_settlement_state(settlement)

    perf = load_performance_state()
    perf.setdefault('investor_metrics', {})['latest_equity'] = 1200000.0
    perf.setdefault('investor_metrics', {})['as_of_date'] = '2026-04-17'
    perf.setdefault('metrics', {})['cumulative_return_pct'] = 0.041
    save_performance_state(perf)

    treasury = TreasuryCashMobilityEngine()
    treasury.reset({'operator': 'smoke_test', 'reason': 'qnt50011_smoke', 'clear_audit': True})
    treasury.sync_settlement_context({'source': 'smoke_test'})

    investor = InvestorCashConfirmationEngine()
    investor.reset({'operator': 'smoke_test', 'reason': 'qnt50011_smoke', 'clear_audit': True})
    investor.register_investor({
        'investor_id': 'INVESTOR_001',
        'investor_name': 'Investor One',
        'bank_instruction_verified': True,
        'statement_alignment_status': 'aligned',
        'preferred_currency': 'USD',
    })
    investor.register_investor({
        'investor_id': 'INVESTOR_002',
        'investor_name': 'Investor Two',
        'bank_instruction_verified': True,
        'statement_alignment_status': 'aligned',
        'preferred_currency': 'USD',
    })

    dist = InvestorDistributionPayablesEngine()
    dist.reset({'operator': 'smoke_test', 'reason': 'qnt50011_smoke', 'clear_audit': True})
    batch = dist.register_batch({
        'operator': 'fund_admin',
        'batch_name': 'APR_2026_MONTHLY_DISTRIBUTION',
        'distribution_type': 'profit_distribution',
        'total_amount': 25000.0,
        'currency': 'USD',
        'period_id': '2026-04',
        'statement_cycle_id': 'APR_2026',
        'allocations': [
            {'investor_id': 'INVESTOR_001', 'weight': 0.6},
            {'investor_id': 'INVESTOR_002', 'weight': 0.4},
        ],
    })['batch']
    dist.attest({'batch_id': batch['batch_id'], 'actor': 'ops_lead', 'attestation_type': 'ops'})
    dist.attest({'batch_id': batch['batch_id'], 'actor': 'finance_lead', 'attestation_type': 'finance'})
    dist.authorize_batch({'batch_id': batch['batch_id'], 'approver': 'distribution_committee'})

    line_one = batch['lines'][0]
    transfer = treasury.stage_transfer({
        'operator': 'treasury_ops',
        'decision_id': 'dist_smoke',
        'transfer_type': 'investor_distribution',
        'from_account': 'broker_buffer',
        'destination': 'investor_distribution_bank',
        'amount': line_one['amount'],
        'currency': 'USD',
        'priority': 'high',
        'purpose': 'smoke distribution payable',
        'investor_id': line_one['investor_id'],
        'statement_cycle_id': 'APR_2026',
    })['transfer']
    treasury.approve_transfer({'transfer_id': transfer['transfer_id'], 'approver': 'treasury_committee'})

    dist.bind_transfer({
        'batch_id': batch['batch_id'],
        'transfer_id': transfer['transfer_id'],
        'investor_id': line_one['investor_id'],
        'operator': 'distribution_ops',
    })
    auth = dist.authorize_payable({'transfer_id': transfer['transfer_id'], 'approver': 'payables_committee'})
    assert auth['status'] == 'authorized'
    executed = treasury.execute_transfer({'transfer_id': transfer['transfer_id'], 'operator': 'treasury_ops'})
    assert executed['status'] == 'executed'
    record = dist.record_execution({'transfer_id': transfer['transfer_id'], 'operator': 'fund_admin'})
    assert record['status'] == 'executed'
    summary = dist.summary()
    assert summary['authorized_payable_release_count'] >= 1
    assert summary['executed_payable_count'] >= 1
    print('QNT50011 smoke test passed')


if __name__ == '__main__':
    main()
