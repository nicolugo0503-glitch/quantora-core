from pathlib import Path
try:
    from strategy_retirement_board import build_status, review_strategy, review_batch
except Exception:
    from backend.strategy_retirement_board import build_status, review_strategy, review_batch

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"

def run():
    retire = review_strategy(ARTIFACTS, {
        "strategy_id":"strat_003",
        "strategy_name":"Crypto Breakout Variant 3",
        "performance_score":39.0,
        "realized_pnl":-14250,
        "drawdown_pct":22.4,
        "current_capital":18000,
        "current_lane":"limited_live",
    })
    assert retire["review"]["decision"] == "retire"

    batch = review_batch(ARTIFACTS, {
        "strategies": [
            {"strategy_id":"strat_002","strategy_name":"Mean Reversion Core Variant 2","performance_score":53.0,"realized_pnl":-4200,"drawdown_pct":15.0,"current_capital":24000,"current_lane":"scaled_live"},
            {"strategy_id":"strat_004","strategy_name":"Trend Core Variant 4","performance_score":68.0,"realized_pnl":6200,"drawdown_pct":8.1,"current_capital":12000,"current_lane":"limited_live"},
        ]
    })
    assert batch["retirements"] >= 0
    assert batch["watchlist"] >= 1
    status = build_status(ARTIFACTS)
    assert status["review_count"] >= 3
    print("QNT30370 smoke test passed")

if __name__ == "__main__":
    run()
