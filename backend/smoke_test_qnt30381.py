import json
from pathlib import Path

try:
    from autonomous_trade_execution_engine import build_status, ingest_signal, execute_cycle, dispatch_cycle, seed_execution_stack
    from regime_aware_capital_allocation import build_status as allocator_status
    from adaptive_execution_policy_brain import build_status as policy_status
except Exception:
    from backend.autonomous_trade_execution_engine import build_status, ingest_signal, execute_cycle, dispatch_cycle, seed_execution_stack
    from backend.regime_aware_capital_allocation import build_status as allocator_status
    from backend.adaptive_execution_policy_brain import build_status as policy_status

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"


def seed_quality_scoreboard():
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / "execution_quality_scoreboard.json").write_text(
        json.dumps(
            {
                "scores": [
                    {"venue_id": "lit_nyse", "venue_name": "Lit NYSE", "quality_score": 93.0, "flagged": False, "avg_slippage_bps": 2.8, "fill_rate": 0.985, "reject_rate": 0.01, "avg_latency_ms": 29.0, "available_liquidity": 2200.0},
                    {"venue_id": "lit_nasdaq", "venue_name": "Lit NASDAQ", "quality_score": 89.5, "flagged": False, "avg_slippage_bps": 3.6, "fill_rate": 0.978, "reject_rate": 0.012, "avg_latency_ms": 26.0, "available_liquidity": 1800.0},
                    {"venue_id": "dark_pool_x", "venue_name": "Dark Pool X", "quality_score": 56.0, "flagged": True, "avg_slippage_bps": 10.2, "fill_rate": 0.84, "reject_rate": 0.06, "avg_latency_ms": 71.0, "available_liquidity": 3100.0},
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def run():
    seed_quality_scoreboard()
    seeded = seed_execution_stack(ARTIFACTS)
    assert seeded["status"] == "execution_stack_seeded"
    signal = ingest_signal(
        ARTIFACTS,
        {
            "strategy_id": "mean_reversion_us_eq",
            "symbol": "AAPL",
            "side": "buy",
            "confidence": 0.83,
            "target_price": 198.50,
            "market_price": 197.80,
            "requested_qty": 900,
            "urgency": "high",
            "strategy_score": 0.88,
            "market_volatility": 0.31,
            "execution_quality_score": 93.0,
        },
    )
    assert signal["status"] == "signal_ingested"
    cycle = execute_cycle(
        ARTIFACTS,
        {
            "liquidity_score": 0.77,
            "slippage_drift_bps": 4.2,
            "latency_drift_ms": 95,
            "fill_rate_delta": -0.01,
            "drift_triggered": False,
        },
    )
    assert cycle["status"] == "cycle_executed"
    assert cycle["order"]["selected_venue"] in {"lit_nyse", "lit_nasdaq"}
    assert cycle["order"]["quantity"] > 0
    dispatched = dispatch_cycle(ARTIFACTS, {})
    assert dispatched["status"] == "cycle_dispatched"
    status = build_status(ARTIFACTS)
    alloc = allocator_status(ARTIFACTS)
    policy = policy_status(ARTIFACTS)
    assert status["order_count"] >= 1
    assert alloc["decision_count"] >= 1
    assert policy["decision_count"] >= 1
    print("QNT30381 smoke test passed")


if __name__ == "__main__":
    run()
