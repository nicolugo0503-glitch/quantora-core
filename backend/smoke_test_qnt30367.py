from pathlib import Path
try:
    from validation_gatekeeper import build_status, evaluate_candidate, review_promotion_batch
except Exception:
    from backend.validation_gatekeeper import build_status, evaluate_candidate, review_promotion_batch

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"

def run():
    approved = evaluate_candidate(ARTIFACTS, {
        "candidate_id":"cand_1001",
        "strategy_name":"Momentum Core Variant 1",
        "promotion_score":72.4,
        "backtest_win_rate":0.58,
        "max_drawdown":9.8,
        "edge_score":66.0,
        "stability_score":68.5,
        "risk_budget_pct":1.4,
    })
    assert approved["review"]["verdict"] == "APPROVED"

    batch = review_promotion_batch(ARTIFACTS, {
        "candidates": [
            {"candidate_id":"cand_1002","strategy_name":"Mean Reversion Core Variant 2","promotion_score":67.8,"backtest_win_rate":0.55,"max_drawdown":10.5,"edge_score":58.5,"stability_score":61.0,"risk_budget_pct":1.8},
            {"candidate_id":"cand_1003","strategy_name":"Crypto Breakout Variant 3","promotion_score":61.0,"backtest_win_rate":0.51,"max_drawdown":16.2,"edge_score":54.0,"stability_score":57.0,"risk_budget_pct":2.6},
        ]
    })
    assert batch["approved_count"] >= 0
    assert batch["rejected_count"] >= 1
    status = build_status(ARTIFACTS)
    assert status["review_count"] >= 3
    print("QNT30367 smoke test passed")

if __name__ == "__main__":
    run()
