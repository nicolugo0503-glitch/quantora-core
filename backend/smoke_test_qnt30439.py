from fund_management import empty_state, add_investor_commitment, record_cash_movement, create_fund_account, fund_summary

def run():
    state = empty_state()
    add_investor_commitment(state, "LP One", 100000, status="active")
    record_cash_movement(state, "deposit", 50000, "seed")
    create_fund_account(state, "Alpha Mandate", "multi-asset")
    summary = fund_summary(state)
    assert summary["active_investor_capital"] == 100000.0
    assert summary["treasury_balance"] == 50000.0
    assert summary["fund_accounts_count"] == 1
    print("QNT30439 smoke test passed")

if __name__ == "__main__":
    run()
