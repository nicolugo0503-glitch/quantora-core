from pathlib import Path
try:
    from smart_order_router import build_status, ingest_venues, route_order
except Exception:
    from backend.smart_order_router import build_status, ingest_venues, route_order

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"

def run():
    ingest = ingest_venues(ARTIFACTS, {
        "venues": [
            {"venue_id":"alpaca_live","venue_name":"Alpaca Live","quality_score":91.2,"avg_slippage_bps":11.5,"avg_latency_ms":380,"available_liquidity":120,"flagged":False},
            {"venue_id":"alpaca_paper","venue_name":"Alpaca Paper","quality_score":78.8,"avg_slippage_bps":18.0,"avg_latency_ms":510,"available_liquidity":80,"flagged":False},
            {"venue_id":"venue_y","venue_name":"Venue Y","quality_score":85.0,"avg_slippage_bps":13.2,"avg_latency_ms":430,"available_liquidity":60,"flagged":False},
        ]
    })
    assert ingest["venue_count"] >= 3
    routed = route_order(ARTIFACTS, {"order_id":"ord_2001","symbol":"AAPL","side":"buy","quantity":180})
    assert routed["status"] == "order_routed"
    assert len(routed["route"]["child_orders"]) >= 2
    status = build_status(ARTIFACTS)
    assert status["route_count"] >= 1
    print("QNT30376 smoke test passed")

if __name__ == "__main__":
    run()
