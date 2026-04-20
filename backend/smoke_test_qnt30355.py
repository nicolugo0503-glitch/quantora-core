from portfolio_risk_fabric import (
    default_portfolio_risk_state,
    evaluate_limits,
    net_cross_market_exposure,
    portfolio_risk_state_view,
    portfolio_risk_summary,
    upsert_exposure,
)

def main():
    state = portfolio_risk_state_view(default_portfolio_risk_state())
    upsert_exposure(state, symbol="AAPL", market="equities", side="long", qty=100, mark_price=180, beta=1.1, strategy_id="strat_aapl")
    upsert_exposure(state, symbol="ES1!", market="futures", side="short", qty=1, mark_price=18000, beta=0.9, strategy_id="hedge_es", hedge_tag="index_hedge")
    upsert_exposure(state, symbol="BTCUSD", market="crypto", side="long", qty=0.75, mark_price=68000, beta=1.4, strategy_id="strat_btc")
    netting = net_cross_market_exposure(state)
    assert netting["status"] == "ok", netting
    evaluation = evaluate_limits(state)
    assert evaluation["status"] in ("ok", "breach"), evaluation
    summary = portfolio_risk_summary(state)
    assert summary["positions"] == 3, summary
    print("QNT30355 smoke test passed")

if __name__ == "__main__":
    main()
