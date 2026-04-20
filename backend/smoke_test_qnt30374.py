from pathlib import Path
try:
    from execution_quality_scoreboard import build_status, ingest_venue_metrics, refresh_scores
except Exception:
    from backend.execution_quality_scoreboard import build_status, ingest_venue_metrics, refresh_scores

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"

def run():
    ingest = ingest_venue_metrics(ARTIFACTS, {
        "venues": [
            {"venue_id":"alpaca_live","venue_name":"Alpaca Live","avg_slippage_bps":12.5,"fill_rate":0.96,"reject_rate":0.03,"avg_latency_ms":420,"orders":120},
            {"venue_id":"venue_x","venue_name":"Venue X","avg_slippage_bps":28.0,"fill_rate":0.84,"reject_rate":0.11,"avg_latency_ms":980,"orders":60},
        ]
    })
    assert ingest["venue_count"] >= 2
    scores = refresh_scores(ARTIFACTS)
    assert len(scores["scores"]) >= 1
    status = build_status(ARTIFACTS)
    assert status["venue_count"] >= 2
    assert status["score_count"] >= 1
    print("QNT30374 smoke test passed")

if __name__ == "__main__":
    run()
