from pathlib import Path
try:
    from execution_fairness_engine import build_status, review_execution, settle_capital
except Exception:
    from backend.execution_fairness_engine import build_status, review_execution, settle_capital

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"

def run():
    review = review_execution(ARTIFACTS, {
        "strategy_id":"strat_010",
        "strategy_name":"Momentum Auction A",
        "expected_price":100.0,
        "fill_price":100.22,
        "quantity":150,
        "side":"buy",
    })
    assert review["status"] == "execution_reviewed"
    settlement = settle_capital(ARTIFACTS, {
        "strategy_id":"strat_010",
        "strategy_name":"Momentum Auction A",
        "gross_notional":15000,
        "realized_pnl":620,
        "slippage_cost":33,
        "fees":7,
    })
    assert settlement["status"] == "capital_settled"
    status = build_status(ARTIFACTS)
    assert status["review_count"] >= 1
    assert status["settlement_count"] >= 1
    print("QNT30373 smoke test passed")

if __name__ == "__main__":
    run()
