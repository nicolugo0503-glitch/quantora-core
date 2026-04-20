from pathlib import Path
try:
    from venue_selection_governor import build_status, ingest_venues, select_venue
except Exception:
    from backend.venue_selection_governor import build_status, ingest_venues, select_venue

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"

def run():
    ingest = ingest_venues(ARTIFACTS, {
        "venues": [
            {"venue_id":"alpaca_live","venue_name":"Alpaca Live","quality_score":91.2,"flagged":False,"avg_slippage_bps":11.5,"fill_rate":0.97,"reject_rate":0.02,"avg_latency_ms":380},
            {"venue_id":"venue_x","venue_name":"Venue X","quality_score":54.0,"flagged":True,"avg_slippage_bps":31.0,"fill_rate":0.82,"reject_rate":0.13,"avg_latency_ms":1020},
        ]
    })
    assert ingest["venue_count"] >= 2
    decision = select_venue(ARTIFACTS, {"order_id":"ord_1001","symbol":"AAPL","side":"buy"})
    assert decision["status"] == "venue_selected"
    assert decision["decision"]["selected_venue"] == "alpaca_live"
    status = build_status(ARTIFACTS)
    assert status["venue_count"] >= 2
    assert status["decision_count"] >= 1
    print("QNT30375 smoke test passed")

if __name__ == "__main__":
    run()
