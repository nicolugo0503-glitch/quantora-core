from backend.app.period_close_distribution_ledger.engine import PeriodCloseDistributionLedgerEngine
from backend.app.investor_distribution_payables.state_store import save_state as save_distribution_state, default_state as default_distribution_state
from backend.app.settlement_reconciliation.state_store import save_state as save_settlement_state, default_state as default_settlement_state
from backend.app.performance_engine.state_store import save_state as save_performance_state, default_state as default_performance_state
from backend.app.investor_exit_finalization.state_store import save_state as save_exit_state, default_state as default_exit_state
from backend.app.period_close_distribution_ledger.state_store import save_state as save_period_close_state, default_state as default_period_close_state


def main():
    dist = default_distribution_state()
    dist['distribution_batches'] = [{
        'batch_id': 'batch_1',
        'period_id': '2026-04',
        'statement_cycle_id': 'APR-2026',
        'currency': 'USD',
        'distribution_type': 'profit_distribution',
        'source_nav_date': '2026-04-30',
    }]
    dist['executed_payables'] = [{
        'batch_id': 'batch_1',
        'investor_id': 'INV-001',
        'investor_name': 'Investor One',
        'amount': 1250.0,
        'currency': 'USD',
        'executed_at': 1,
        'treasury_transfer_id': 'tx_1',
    }, {
        'batch_id': 'batch_1',
        'investor_id': 'INV-002',
        'investor_name': 'Investor Two',
        'amount': 1750.0,
        'currency': 'USD',
        'executed_at': 1,
        'treasury_transfer_id': 'tx_2',
    }]
    save_distribution_state(dist)

    settlement = default_settlement_state()
    settlement['reconciliation_breaks'] = []
    settlement['last_reconciliation'] = {'status': 'matched'}
    save_settlement_state(settlement)

    perf = default_performance_state()
    perf['metrics'] = {'cumulative_return_pct': 0.21}
    perf['investor_metrics'] = {'latest_equity': 100000.0, 'nav_per_unit': 1.2345, 'as_of_date': '2026-04-30'}
    save_performance_state(perf)

    save_exit_state(default_exit_state())
    save_period_close_state(default_period_close_state())

    engine = PeriodCloseDistributionLedgerEngine()
    registered = engine.register_close({'operator': 'ops', 'period_id': '2026-04', 'statement_cycle_id': 'APR-2026', 'ops_attested': True, 'finance_attested': True})
    pcid = registered['period_close']['period_close_id']
    assert registered['period_close']['distribution_total'] == 3000.0

    ledger = engine.finalize_ledger({'period_close_id': pcid, 'approver': 'controller'})
    assert ledger['status'] == 'pending_notice_finalization'

    engine.finalize_notice({'period_close_id': pcid, 'investor_id': 'INV-001', 'operator': 'ops'})
    notices = engine.finalize_notice({'period_close_id': pcid, 'investor_id': 'INV-002', 'operator': 'ops'})
    assert notices['status'] == 'ready_for_period_close'

    closed = engine.close_period({'period_close_id': pcid, 'approver': 'cfo'})
    assert closed['status'] == 'closed'
    print('QNT50012 smoke passed')


if __name__ == '__main__':
    main()
