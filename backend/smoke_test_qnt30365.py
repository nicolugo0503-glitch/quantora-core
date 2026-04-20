from pathlib import Path
try:
    from strategy_factory import upsert_templates, generate_candidates, backtest_candidates, promote_candidates, build_status
except Exception:
    from backend.strategy_factory import upsert_templates, generate_candidates, backtest_candidates, promote_candidates, build_status

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"

def run():
    upsert_templates(ARTIFACTS, {
        "templates": [
            {"name":"Momentum Core","market":"equities","signal_family":"momentum","timeframe":"1h","mutation_bias":"balanced"},
            {"name":"Mean Reversion Core","market":"equities","signal_family":"mean_reversion","timeframe":"15m","mutation_bias":"conservative"}
        ]
    })
    gen = generate_candidates(ARTIFACTS, {"batch_size": 4, "generation_mode": "mutation"})
    assert len(gen["generated"]) == 4
    bt = backtest_candidates(ARTIFACTS, {"candidate_ids": []})
    assert len(bt["evaluated"]) >= 4
    promo = promote_candidates(ARTIFACTS, {"promotion_score_threshold": 67.5})
    assert promo["status"] == "promotion_completed"
    status = build_status(ARTIFACTS)
    assert status["template_count"] >= 2
    assert status["candidate_count"] >= 4
    print("QNT30365 smoke test passed")

if __name__ == "__main__":
    run()
