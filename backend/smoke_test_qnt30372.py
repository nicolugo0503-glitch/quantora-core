from pathlib import Path
try:
    from opportunity_auction_engine import build_status, run_auction, award_capital
except Exception:
    from backend.opportunity_auction_engine import build_status, run_auction, award_capital

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"

def run():
    auction = run_auction(ARTIFACTS, {
        "candidates": [
            {"candidate_id":"cand_3001","strategy_name":"Momentum Auction A","verdict":"APPROVED","opportunity_score":84.0,"edge_score":73.0,"confidence":0.79,"requested_capital":40000,"priority":True},
            {"candidate_id":"cand_3002","strategy_name":"Reversion Auction B","verdict":"WATCHLIST","opportunity_score":76.0,"edge_score":66.0,"confidence":0.68,"requested_capital":22000,"priority":False},
            {"candidate_id":"cand_3003","strategy_name":"Breakout Auction C","verdict":"APPROVED","opportunity_score":81.0,"edge_score":70.0,"confidence":0.74,"requested_capital":30000,"priority":False},
        ]
    })
    assert len(auction["bids"]) >= 2
    awards = award_capital(ARTIFACTS, {"available_capital": 55000})
    assert awards["status"] == "capital_awarded"
    assert len(awards["winners"]) >= 1
    status = build_status(ARTIFACTS)
    assert status["award_count"] >= 1
    print("QNT30372 smoke test passed")

if __name__ == "__main__":
    run()
