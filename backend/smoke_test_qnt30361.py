from pathlib import Path
try:
    from institutional_portfolio_brain import (
        ingest_snapshot,
        evaluate_coordination,
        sync_allocator,
        build_status,
    )
except Exception:
    from backend.institutional_portfolio_brain import (
        ingest_snapshot,
        evaluate_coordination,
        sync_allocator,
        build_status,
    )

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"

def run():
    ingest_snapshot(ARTIFACTS, {
        "regime_tag": "balanced_trend",
        "strategies": [
            {"strategy_name":"AAPL Momentum","market":"equities","symbols":["AAPL","QQQ"],"realized_pnl":1200,"unrealized_pnl":140,"win_rate":0.61,"confidence":0.72,"volatility":0.22,"activity":8,"regime_fit":0.67},
            {"strategy_name":"NVDA Breakout","market":"equities","symbols":["NVDA"],"realized_pnl":980,"unrealized_pnl":60,"win_rate":0.57,"confidence":0.69,"volatility":0.30,"activity":5,"regime_fit":0.62},
            {"strategy_name":"BTC Carry","market":"crypto","symbols":["BTCUSD"],"realized_pnl":860,"unrealized_pnl":110,"win_rate":0.59,"confidence":0.66,"volatility":0.35,"activity":4,"regime_fit":0.71},
            {"strategy_name":"AAPL Mean Revert","market":"equities","symbols":["AAPL"],"realized_pnl":300,"unrealized_pnl":25,"win_rate":0.52,"confidence":0.51,"volatility":0.18,"activity":3,"regime_fit":0.45},
        ]
    })
    coord = evaluate_coordination(ARTIFACTS, {"max_active_strategies": 3, "max_symbol_overlap": 1, "conflict_penalty": 15.0})
    assert coord["status"] == "coordinated"
    assert len(coord["allocations"]) >= 4
    synced = sync_allocator(ARTIFACTS, {"total_capital": 250000, "reserve_pct": 0.1})
    assert synced["deployable_capital"] == 225000.0
    status = build_status(ARTIFACTS)
    assert status["strategy_count"] >= 4
    print("QNT30361 smoke test passed")

if __name__ == "__main__":
    run()
