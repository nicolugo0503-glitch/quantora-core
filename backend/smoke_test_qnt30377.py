from pathlib import Path
try:
    from execution_replay_lab import build_status, replay_execution, attribute_fills
except Exception:
    from backend.execution_replay_lab import build_status, replay_execution, attribute_fills

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"

def run():
    replay = replay_execution(ARTIFACTS, {
        "order_id":"ord_3001",
        "symbol":"AAPL",
        "events":[
            {"quantity":50,"latency_ms":420,"slippage_bps":12.5},
            {"quantity":70,"latency_ms":510,"slippage_bps":14.2},
            {"quantity":60,"latency_ms":460,"slippage_bps":10.8},
        ]
    })
    assert replay["status"] == "execution_replayed"
    attr = attribute_fills(ARTIFACTS, {
        "strategy_id":"strat_020",
        "symbol":"AAPL",
        "fills":[
            {"venue_id":"alpaca_live","quantity":90,"realized_pnl":420,"slippage_bps":11.2},
            {"venue_id":"venue_y","quantity":60,"realized_pnl":260,"slippage_bps":13.4},
            {"venue_id":"alpaca_paper","quantity":30,"realized_pnl":75,"slippage_bps":16.8},
        ]
    })
    assert attr["status"] == "fills_attributed"
    status = build_status(ARTIFACTS)
    assert status["replay_count"] >= 1
    assert status["attribution_count"] >= 1
    print("QNT30377 smoke test passed")

if __name__ == "__main__":
    run()
