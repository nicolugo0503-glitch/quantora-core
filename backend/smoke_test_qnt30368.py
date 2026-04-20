from pathlib import Path
try:
    from capital_promotion_router import build_status, route_candidate, execution_gate_decision
except Exception:
    from backend.capital_promotion_router import build_status, route_candidate, execution_gate_decision

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"

def run():
    routed = route_candidate(ARTIFACTS, {
        "candidate_id":"cand_1001",
        "strategy_name":"Momentum Core Variant 1",
        "verdict":"APPROVED",
        "requested_capital":50000,
    })
    assert routed["route"]["target"] == "funded_live"

    sandbox = route_candidate(ARTIFACTS, {
        "candidate_id":"cand_1002",
        "strategy_name":"Mean Reversion Core Variant 2",
        "verdict":"WATCHLIST",
        "requested_capital":20000,
    })
    assert sandbox["route"]["execution_mode"] == "sandbox"

    blocked = execution_gate_decision(ARTIFACTS, {
        "candidate_id":"cand_1003",
        "strategy_name":"Crypto Breakout Variant 3",
        "verdict":"REJECTED",
        "requested_order_notional":9000,
    })
    assert blocked["decision"]["allow_execution"] is False

    released = execution_gate_decision(ARTIFACTS, {
        "candidate_id":"cand_1001",
        "strategy_name":"Momentum Core Variant 1",
        "verdict":"APPROVED",
        "requested_order_notional":12000,
    })
    assert released["decision"]["allow_execution"] is True

    status = build_status(ARTIFACTS)
    assert status["route_count"] >= 2
    assert status["execution_decision_count"] >= 2
    print("QNT30368 smoke test passed")

if __name__ == "__main__":
    run()
