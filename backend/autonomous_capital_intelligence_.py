from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

app = FastAPI(title="QNT30400 Autonomous Capital Intelligence Orchestrator", version="1.0.0")
STATE={"orchestrator_mode":"active","capital_base":1000000.0,"deployable_capital":850000.0,"reserve_capital":150000.0,"regime":"normal","selected_strategies":[],"capital_allocations":[],"policy_state":{"max_single_strategy_weight":0.35,"min_reserve_ratio":0.10,"drawdown_throttle_ratio":0.50,"execution_quality_floor":0.70},"capital_decisions":[],"rebalance_history":[],"audit":[]}

class RegimeUpdate(BaseModel):
    regime:str; volatility_score:float=Field(..., ge=0.0, le=1.0); drawdown_pressure:float=Field(..., ge=0.0, le=1.0); execution_quality:float=Field(..., ge=0.0, le=1.0)
class StrategyCandidate(BaseModel):
    strategy_id:str; name:str; score:float=Field(..., ge=0.0); expected_weight:float=Field(..., ge=0.0, le=1.0); execution_quality:float=Field(..., ge=0.0, le=1.0); drawdown:float=Field(..., ge=0.0, le=1.0); status:str="active"
class CandidateBatch(BaseModel):
    strategies: List[StrategyCandidate]
class RebalanceRequest(BaseModel):
    capital_budget: float=Field(..., gt=0); regime: Optional[str]=None; enforce_reserve: bool=True

def now(): return datetime.utcnow().isoformat()+"Z"
def log_event(kind,payload): STATE["audit"].append({"id":str(uuid.uuid4()),"kind":kind,"timestamp":now(),"payload":payload}); STATE["audit"]=STATE["audit"][-500:]
def effective_budget(requested_budget: float)->float:
    reserve_floor=STATE["capital_base"]*STATE["policy_state"]["min_reserve_ratio"]; max_budget=max(0.0, STATE["capital_base"]-reserve_floor); return round(min(requested_budget,max_budget),2)
def throttle_multiplier()->float:
    regime=STATE["regime"]
    return 0.45 if regime=="stress" else 0.70 if regime=="volatile" else 0.60 if regime=="defensive" else 1.0

@app.get("/capital-orchestrator/status")
def status():
    return {"mission":"QNT30400","orchestrator_mode":STATE["orchestrator_mode"],"capital_base":STATE["capital_base"],"deployable_capital":STATE["deployable_capital"],"reserve_capital":STATE["reserve_capital"],"regime":STATE["regime"],"policy_state":STATE["policy_state"],"selected_count":len(STATE["selected_strategies"]),"allocation_count":len(STATE["capital_allocations"]),"rebalance_runs":len(STATE["rebalance_history"]),"audit_events":len(STATE["audit"])}

@app.post("/capital-orchestrator/regime/update")
def update_regime(payload: RegimeUpdate):
    STATE["regime"]=payload.regime
    decision={"decision_id":f"REG-{uuid.uuid4().hex[:12]}","regime":payload.regime,"volatility_score":payload.volatility_score,"drawdown_pressure":payload.drawdown_pressure,"execution_quality":payload.execution_quality,"timestamp":now(),"throttle_multiplier":throttle_multiplier()}
    STATE["capital_decisions"].append(decision); log_event("regime_updated",decision); return {"status":"ok","decision":decision}
@app.post("/capital-orchestrator/strategies/upsert")
def upsert_strategies(payload: CandidateBatch):
    STATE["selected_strategies"]=[s.model_dump() for s in payload.strategies if s.status=="active"]; log_event("strategy_candidates_upserted",{"count":len(STATE["selected_strategies"])}); return {"status":"ok","candidate_count":len(STATE["selected_strategies"])}
@app.get("/capital-orchestrator/strategies")
def list_strategies(): return {"strategies":STATE["selected_strategies"]}
@app.post("/capital-orchestrator/rebalance")
def rebalance(payload: RebalanceRequest):
    candidates=[s for s in STATE["selected_strategies"] if s.get("status")=="active"]
    if not candidates: return {"status":"error","message":"no active strategies"}
    budget=effective_budget(payload.capital_budget) if payload.enforce_reserve else payload.capital_budget
    regime=payload.regime or STATE["regime"]; mult=throttle_multiplier(); adjusted_budget=round(budget*mult,2)
    eligible=[]
    for s in candidates:
        if s["execution_quality"]<STATE["policy_state"]["execution_quality_floor"]: continue
        raw_weight=min(s["expected_weight"], STATE["policy_state"]["max_single_strategy_weight"]); risk_penalty=max(0.25, 1.0-s["drawdown"]); composite=max(0.0001, s["score"]*raw_weight*risk_penalty); eligible.append((s, composite))
    if not eligible: return {"status":"error","message":"no eligible strategies after policy filters"}
    total=sum(x[1] for x in eligible); allocations=[]
    for s, comp in eligible:
        weight=comp/total; capital=round(adjusted_budget*weight,2)
        allocations.append({"strategy_id":s["strategy_id"],"name":s["name"],"weight":round(weight,6),"capital_allocated":capital,"score":s["score"],"execution_quality":s["execution_quality"],"drawdown":s["drawdown"],"regime":regime})
    allocations=sorted(allocations,key=lambda x:x["capital_allocated"], reverse=True); deployed=round(sum(x["capital_allocated"] for x in allocations),2); reserve=round(STATE["capital_base"]-deployed,2)
    STATE["capital_allocations"]=allocations; STATE["deployable_capital"]=deployed; STATE["reserve_capital"]=reserve
    run={"rebalance_id":f"REB-{uuid.uuid4().hex[:12]}","regime":regime,"requested_budget":payload.capital_budget,"effective_budget":budget,"throttled_budget":adjusted_budget,"deployed_capital":deployed,"reserve_capital":reserve,"allocations":allocations,"timestamp":now()}
    STATE["rebalance_history"].append(run); STATE["capital_decisions"].append({"decision_id":f"CAP-{uuid.uuid4().hex[:12]}","type":"rebalance","regime":regime,"deployed_capital":deployed,"reserve_capital":reserve,"timestamp":now()}); log_event("capital_rebalanced",{"rebalance_id":run["rebalance_id"],"regime":regime,"deployed_capital":deployed}); return {"status":"ok","rebalance":run}
@app.get("/capital-orchestrator/allocations")
def allocations(): return {"allocations":STATE["capital_allocations"]}
@app.get("/capital-orchestrator/history")
def history(): return {"history":STATE["rebalance_history"][::-1]}
@app.get("/capital-orchestrator/decisions")
def decisions(): return {"decisions":STATE["capital_decisions"][::-1]}
@app.get("/capital-orchestrator/audit")
def audit(limit:int=25): return {"events":STATE["audit"][-limit:][::-1]}
