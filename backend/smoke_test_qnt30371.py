from pathlib import Path
try:
    from reallocation_opportunity_queue import build_status, refresh_queue, reallocate_capital
except Exception:
    from backend.reallocation_opportunity_queue import build_status, refresh_queue, reallocate_capital

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"

def run():
    refreshed = refresh_queue(ARTIFACTS, {
        "candidates": [
            {"candidate_id":"cand_2001","strategy_name":"Momentum Expansion A","verdict":"APPROVED","opportunity_score":82.5,"edge_score":71.0,"confidence":0.78,"reclaimed_capital_pool":30000,"priority":True},
            {"candidate_id":"cand_2002","strategy_name":"Reversion Recovery B","verdict":"WATCHLIST","opportunity_score":74.0,"edge_score":63.5,"confidence":0.66,"reclaimed_capital_pool":18000,"priority":False},
        ]
    })
    assert len(refreshed["opportunities"]) >= 1
    executed = reallocate_capital(ARTIFACTS, {"candidate_id":"cand_2001","available_capital":22000})
    assert executed["status"] == "capital_reallocated"
    status = build_status(ARTIFACTS)
    assert status["opportunity_count"] >= 1
    assert status["reallocation_event_count"] >= 1
    print("QNT30371 smoke test passed")

if __name__ == "__main__":
    run()
