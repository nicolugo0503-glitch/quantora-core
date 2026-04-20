from pathlib import Path
try:
    from capital_escalation_board import build_status, review_strategy, review_batch
except Exception:
    from backend.capital_escalation_board import build_status, review_strategy, review_batch

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"

def run():
    promo = review_strategy(ARTIFACTS, {
        "strategy_id":"strat_001",
        "strategy_name":"Momentum Core Variant 1",
        "performance_score":84.2,
        "win_rate":0.61,
        "realized_pnl":18450,
        "drawdown_pct":7.8,
        "current_lane":"limited_live",
        "current_capital":15000,
    })
    assert promo["review"]["decision"] == "promote"

    batch = review_batch(ARTIFACTS, {
        "strategies": [
            {"strategy_id":"strat_002","strategy_name":"Mean Reversion Core Variant 2","performance_score":58.0,"win_rate":0.49,"realized_pnl":-2100,"drawdown_pct":12.4,"current_lane":"scaled_live","current_capital":42000},
            {"strategy_id":"strat_003","strategy_name":"Crypto Breakout Variant 3","performance_score":41.0,"win_rate":0.42,"realized_pnl":-8600,"drawdown_pct":21.0,"current_lane":"limited_live","current_capital":12000},
        ]
    })
    assert batch["reductions"] >= 1
    assert batch["kills"] >= 1
    status = build_status(ARTIFACTS)
    assert status["review_count"] >= 3
    print("QNT30369 smoke test passed")

if __name__ == "__main__":
    run()
