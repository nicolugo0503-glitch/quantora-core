from pathlib import Path
try:
    from capital_committee_engine import upsert_committees, create_proposal, cast_vote, compile_allocation, build_status
except Exception:
    from backend.capital_committee_engine import upsert_committees, create_proposal, cast_vote, compile_allocation, build_status

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"

def run():
    upsert_committees(ARTIFACTS, {
        "committees": [{
            "committee_id": "capital_committee_primary",
            "name": "Primary Capital Committee",
            "quorum": 2,
            "approval_threshold": 0.6,
            "members": [
                {"member_id":"cio","role":"chair","weight":1.5},
                {"member_id":"risk","role":"risk","weight":1.0},
                {"member_id":"allocator","role":"allocator","weight":1.0},
            ],
        }]
    })
    created = create_proposal(ARTIFACTS, {
        "committee_id": "capital_committee_primary",
        "title": "Increase NVDA breakout capital",
        "requested_capital": 50000,
        "strategy_id": "nvda_breakout",
    })
    pid = created["proposal"]["proposal_id"]
    v1 = cast_vote(ARTIFACTS, {"proposal_id": pid, "member_id": "cio", "decision": "approve", "weight": 1.5})
    assert v1["proposal_status"] in ("voting", "approved")
    v2 = cast_vote(ARTIFACTS, {"proposal_id": pid, "member_id": "risk", "decision": "approve", "weight": 1.0})
    assert v2["proposal_status"] == "approved"
    comp = compile_allocation(ARTIFACTS, {"proposal_id": pid})
    assert comp["proposal"]["status"] == "approved"
    status = build_status(ARTIFACTS)
    assert status["committee_count"] >= 1
    print("QNT30363 smoke test passed")

if __name__ == "__main__":
    run()
