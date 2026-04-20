from backend.app.intercompany_ledger.engine import IntercompanyLedgerEngine


def main():
    engine = IntercompanyLedgerEngine()
    engine.sync_context({'source': 'smoke'})
    registered = engine.register_flow({
        'operator': 'smoke',
        'from_entity': 'fund_master',
        'to_entity': 'spv_delta',
        'amount': 1000,
        'purpose': 'working capital rebalance',
        'flow_type': 'intercompany_funding',
        'fund_id': 'fund_master',
        'spv_id': 'spv_delta',
        'jurisdiction': 'US',
    })
    case = registered['flow_case']
    approved = engine.approve_flow({'flow_case_id': case['flow_case_id'], 'approver': 'controller'})
    posted = engine.post_flow({'flow_case_id': case['flow_case_id'], 'operator': 'ledger_ops'})
    settled = engine.settle_flow({'flow_case_id': case['flow_case_id'], 'operator': 'treasury_ops'})
    summary = engine.summary()
    assert approved['flow_case']['status'] == 'approved'
    assert posted['flow_case']['status'] == 'posted'
    assert settled['flow_case']['status'] == 'settled'
    assert summary['journal_entry_count'] >= 1
    assert summary['settlement_count'] >= 1
    print('QNT50018 smoke passed')


if __name__ == '__main__':
    main()
