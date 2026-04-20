import json
from pathlib import Path

try:
    from adaptive_execution_policy_brain import build_status, ingest_context, decide_policy, dispatch_override
except Exception:
    from backend.adaptive_execution_policy_brain import build_status, ingest_context, decide_policy, dispatch_override

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"


def seed_dependencies():
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / "execution_quality_scoreboard.json").write_text(
        json.dumps(
            {
                "scores": [
                    {"venue_id": "lit_nyse", "quality_score": 92.0, "flagged": False},
                    {"venue_id": "dark_pool_x", "quality_score": 58.0, "flagged": True},
                    {"venue_id": "lit_nasdaq", "quality_score": 88.0, "flagged": False},
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (ARTIFACTS / "venue_selection_governor.json").write_text(
        json.dumps({"policy": {"mode": "adaptive", "max_venues": 1, "min_score": 65.0, "avoid_flagged": True, "fallback_enabled": True, "fallback_venue_id": ""}}, indent=2),
        encoding="utf-8",
    )
    (ARTIFACTS / "smart_order_router.json").write_text(
        json.dumps({"rules": {"max_child_orders": 3, "min_venue_score": 60.0, "prefer_lower_slippage": True, "prefer_lower_latency": True, "reserve_liquidity_buffer_pct": 0.1}}, indent=2),
        encoding="utf-8",
    )


def run():
    seed_dependencies()
    ingested = ingest_context(
        ARTIFACTS,
        {
            "symbol": "AAPL",
            "side": "buy",
            "order_quantity": 1500,
            "urgency": "high",
            "market_volatility": 0.47,
            "regime_shift": 0.21,
            "liquidity_score": 0.28,
            "slippage_drift_bps": 18.5,
            "latency_drift_ms": 410,
            "fill_rate_delta": -0.14,
            "drift_triggered": True,
        },
    )
    assert ingested["status"] == "context_ingested"
    decision = decide_policy(ARTIFACTS, {})
    assert decision["status"] == "policy_decided"
    assert decision["decision"]["mode"] in {"defensive", "halt"}
    dispatched = dispatch_override(ARTIFACTS, {})
    assert dispatched["status"] == "override_dispatched"
    status = build_status(ARTIFACTS)
    assert status["decision_count"] >= 1
    assert status["dispatch_count"] >= 1
    governor = json.loads((ARTIFACTS / "venue_selection_governor.json").read_text(encoding="utf-8"))
    sor = json.loads((ARTIFACTS / "smart_order_router.json").read_text(encoding="utf-8"))
    assert governor["policy"]["min_score"] >= 70.0
    assert sor["rules"]["max_child_orders"] <= 2
    print("QNT30379 smoke test passed")


if __name__ == "__main__":
    run()
