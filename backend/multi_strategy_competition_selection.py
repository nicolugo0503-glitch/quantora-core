from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

app = FastAPI(title="QNT30399 Autonomous Multi-Strategy Competition & Selection Engine", version="1.0.0")

STATE = {
    "competition_mode": "active",
    "strategies": {},
    "matches": [],
    "selection_history": [],
    "capital_queue": [],
    "champion": None,
    "audit": [],
}

class StrategyProfile(BaseModel):
    strategy_id: str
    name: str
    regime_fit: float = Field(..., ge=0.0, le=1.0)
    sharpe: float = 0.0
    realized_pnl: float = 0.0
    drawdown: float = 0.0
    win_rate: float = Field(0.0, ge=0.0, le=1.0)
    execution_quality: float = Field(1.0, ge=0.0, le=1.0)
    status: str = "active"
    metadata: Optional[Dict[str, Any]] = None

class StrategyBatch(BaseModel):
    strategies: List[StrategyProfile]

class CompetitionRequest(BaseModel):
    regime: str = "normal"
    capital_budget: float = Field(..., gt=0)
    max_selected: int = 3

def now():
    return datetime.utcnow().isoformat() + "Z"

def log_event(kind: str, payload: Dict[str, Any]):
    STATE["audit"].append({
        "id": str(uuid.uuid4()),
        "kind": kind,
        "timestamp": now(),
        "payload": payload,
    })
    STATE["audit"] = STATE["audit"][-500:]

def score_strategy(s: Dict[str, Any]) -> float:
    score = (
        s["regime_fit"] * 30.0 +
        s["sharpe"] * 20.0 +
        s["win_rate"] * 20.0 +
        s["execution_quality"] * 20.0 +
        (s["realized_pnl"] / 10000.0) * 10.0 -
        abs(s["drawdown"]) * 10.0
    )
    if s.get("status") != "active":
        score -= 999.0
    return round(score, 6)

@app.get("/strategy-competition/status")
def status():
    ranked = sorted(
        [{"strategy_id": sid, "score": score_strategy(s), **s} for sid, s in STATE["strategies"].items()],
        key=lambda x: x["score"],
        reverse=True,
    )
    return {
        "mission": "QNT30399",
        "competition_mode": STATE["competition_mode"],
        "strategy_count": len(STATE["strategies"]),
        "champion": STATE["champion"],
        "latest_rankings": ranked[:10],
        "selection_runs": len(STATE["selection_history"]),
        "audit_events": len(STATE["audit"]),
    }

@app.post("/strategy-competition/strategies/upsert")
def upsert_strategies(payload: StrategyBatch):
    for strategy in payload.strategies:
        STATE["strategies"][strategy.strategy_id] = strategy.model_dump()
    log_event("strategies_upserted", {"count": len(payload.strategies)})
    return {"status": "ok", "strategy_count": len(STATE["strategies"])}

@app.get("/strategy-competition/strategies")
def list_strategies():
    ranked = sorted(
        [{"strategy_id": sid, "score": score_strategy(s), **s} for sid, s in STATE["strategies"].items()],
        key=lambda x: x["score"],
        reverse=True,
    )
    return {"strategies": ranked}

@app.post("/strategy-competition/run")
def run_competition(payload: CompetitionRequest):
    ranked = sorted(
        [{"strategy_id": sid, "score": score_strategy(s), **s} for sid, s in STATE["strategies"].items()],
        key=lambda x: x["score"],
        reverse=True,
    )
    selected = ranked[:payload.max_selected]
    if not selected:
        return {"status": "error", "message": "no active strategies available"}

    total_score = sum(max(x["score"], 0.01) for x in selected)
    allocations = []
    for s in selected:
        weight = max(s["score"], 0.01) / total_score
        allocations.append({
            "strategy_id": s["strategy_id"],
            "name": s["name"],
            "score": s["score"],
            "weight": round(weight, 6),
            "capital_allocated": round(payload.capital_budget * weight, 2),
            "regime": payload.regime,
        })

    champion = allocations[0]
    STATE["champion"] = champion
    match = {
        "match_id": f"MCH-{uuid.uuid4().hex[:12]}",
        "regime": payload.regime,
        "capital_budget": payload.capital_budget,
        "selected": allocations,
        "champion": champion,
        "created_at": now(),
    }
    STATE["matches"].append(match)
    STATE["selection_history"].append(match)
    STATE["capital_queue"] = allocations
    log_event("competition_run_completed", {
        "match_id": match["match_id"],
        "regime": payload.regime,
        "champion": champion["strategy_id"],
        "selected_count": len(allocations),
    })
    return {"status": "ok", "match": match}

@app.get("/strategy-competition/champion")
def champion():
    return {"champion": STATE["champion"]}

@app.get("/strategy-competition/capital-queue")
def capital_queue():
    return {"capital_queue": STATE["capital_queue"]}

@app.get("/strategy-competition/history")
def history():
    return {"history": STATE["selection_history"][::-1]}

@app.get("/strategy-competition/audit")
def audit(limit: int = 25):
    return {"events": STATE["audit"][-limit:][::-1]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("multi_strategy_competition_selection.py", host="127.0.0.1", port=8010, reload=False)
