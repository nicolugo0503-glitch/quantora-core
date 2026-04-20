from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

app = FastAPI(title="QNT30384 Autonomous Portfolio Manager", version="1.0.0")

STATE = {
    "capital_base": 1000000.0,
    "max_strategy_weight": 0.35,
    "min_strategy_weight": 0.00,
    "kill_threshold_drawdown": 25000.0,
    "rebalance_count": 0,
    "allocations": {},
    "strategies": {},
    "killed_strategies": [],
    "audit": [],
}

class StrategySnapshot(BaseModel):
    strategy_id: str
    realized_pnl: float = 0.0
    sharpe: float = 0.0
    drawdown: float = 0.0
    win_rate: float = Field(0.0, ge=0.0, le=1.0)
    trade_count: int = 0
    execution_quality: float = Field(1.0, ge=0.0, le=1.0)
    regime_score: float = 0.5
    active: bool = True
    metadata: Optional[Dict[str, Any]] = None

class StrategyBatch(BaseModel):
    strategies: List[StrategySnapshot]

class ControlsUpdate(BaseModel):
    capital_base: Optional[float] = None
    max_strategy_weight: Optional[float] = None
    min_strategy_weight: Optional[float] = None
    kill_threshold_drawdown: Optional[float] = None

def log_event(kind: str, payload: Dict[str, Any]):
    STATE["audit"].append({
        "id": str(uuid.uuid4()),
        "kind": kind,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "payload": payload,
    })
    STATE["audit"] = STATE["audit"][-500:]

def score_strategy(s: Dict[str, Any]) -> float:
    if not s.get("active", True):
        return -999999.0
    if s["drawdown"] >= STATE["kill_threshold_drawdown"]:
        return -999999.0
    score = (
        s["realized_pnl"] * 0.0008 +
        s["sharpe"] * 25.0 +
        s["win_rate"] * 30.0 +
        s["execution_quality"] * 20.0 +
        s["regime_score"] * 15.0 -
        s["drawdown"] * 0.0015
    )
    if s["trade_count"] < 3:
        score *= 0.75
    return round(score, 6)

def normalize_weights(scored: List[Dict[str, Any]]) -> Dict[str, float]:
    eligible = [x for x in scored if x["score"] > 0 and x["active"]]
    if not eligible:
        return {}
    total = sum(x["score"] for x in eligible)
    raw = {x["strategy_id"]: x["score"] / total for x in eligible}
    clipped = {}
    remaining = 1.0
    flexible = []
    for strategy_id, weight in raw.items():
        clipped_weight = min(weight, STATE["max_strategy_weight"])
        if clipped_weight <= STATE["min_strategy_weight"]:
            clipped_weight = 0.0
        clipped[strategy_id] = clipped_weight
    subtotal = sum(clipped.values())
    if subtotal > 0:
        factor = 1.0 / subtotal
        for k in list(clipped.keys()):
            clipped[k] = round(clipped[k] * factor, 6)
    return clipped

def recompute_allocations():
    scored = []
    killed = []
    for strategy_id, strategy in STATE["strategies"].items():
        strategy_score = score_strategy(strategy)
        is_killed = strategy["drawdown"] >= STATE["kill_threshold_drawdown"] or not strategy.get("active", True)
        if is_killed:
            killed.append(strategy_id)
        scored.append({
            "strategy_id": strategy_id,
            "score": strategy_score,
            "active": not is_killed,
        })
    weights = normalize_weights(scored)
    allocations = {}
    for strategy_id, weight in weights.items():
        allocations[strategy_id] = {
            "weight": weight,
            "capital": round(weight * STATE["capital_base"], 2),
            "status": "active",
        }
    for strategy_id in STATE["strategies"]:
        if strategy_id not in allocations:
            allocations[strategy_id] = {
                "weight": 0.0,
                "capital": 0.0,
                "status": "killed" if strategy_id in killed else "standby",
            }
    STATE["allocations"] = allocations
    STATE["killed_strategies"] = sorted(list(set(killed)))
    STATE["rebalance_count"] += 1
    log_event("portfolio_rebalanced", {
        "rebalance_count": STATE["rebalance_count"],
        "allocations": allocations,
        "killed_strategies": STATE["killed_strategies"],
    })
    return allocations

@app.get("/portfolio-manager/status")
def status():
    return {
        "mission": "QNT30384",
        "capital_base": STATE["capital_base"],
        "strategy_count": len(STATE["strategies"]),
        "rebalance_count": STATE["rebalance_count"],
        "killed_strategies": STATE["killed_strategies"],
        "allocations": STATE["allocations"],
        "audit_events": len(STATE["audit"]),
    }

@app.post("/portfolio-manager/controls/update")
def update_controls(payload: ControlsUpdate):
    data = payload.model_dump(exclude_none=True)
    for key, value in data.items():
        STATE[key] = value
    log_event("controls_updated", data)
    return {"status": "ok", "controls": {
        "capital_base": STATE["capital_base"],
        "max_strategy_weight": STATE["max_strategy_weight"],
        "min_strategy_weight": STATE["min_strategy_weight"],
        "kill_threshold_drawdown": STATE["kill_threshold_drawdown"],
    }}

@app.post("/portfolio-manager/strategy/upsert")
def upsert_strategy(strategy: StrategySnapshot):
    STATE["strategies"][strategy.strategy_id] = strategy.model_dump()
    log_event("strategy_upserted", {"strategy_id": strategy.strategy_id})
    allocations = recompute_allocations()
    return {"status": "ok", "strategy_id": strategy.strategy_id, "allocations": allocations}

@app.post("/portfolio-manager/strategies/batch")
def upsert_batch(batch: StrategyBatch):
    for strategy in batch.strategies:
        STATE["strategies"][strategy.strategy_id] = strategy.model_dump()
    log_event("strategy_batch_upserted", {"count": len(batch.strategies)})
    allocations = recompute_allocations()
    return {"status": "ok", "processed": len(batch.strategies), "allocations": allocations}

@app.post("/portfolio-manager/rebalance")
def rebalance():
    allocations = recompute_allocations()
    return {"status": "ok", "allocations": allocations, "killed_strategies": STATE["killed_strategies"]}

@app.get("/portfolio-manager/allocations")
def get_allocations():
    return {"allocations": STATE["allocations"]}

@app.get("/portfolio-manager/strategies")
def get_strategies():
    return {"strategies": list(STATE["strategies"].values())}

@app.get("/portfolio-manager/audit")
def audit(limit: int = 25):
    return {"events": STATE["audit"][-limit:][::-1]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("autonomous_portfolio_manager:app", host="127.0.0.1", port=8010, reload=False)
