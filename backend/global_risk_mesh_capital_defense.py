from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

app = FastAPI(title="QNT30403 Autonomous Global Risk Mesh & Capital Defense System", version="1.0.0")
STATE = {"risk_mesh_mode":"active","global_risk_score":0.38,"capital_defense_state":"normal",
"risk_nodes":{"portfolio_drawdown":{"value":0.06,"threshold":0.12,"severity":"normal"},"execution_drift":{"value":0.08,"threshold":0.15,"severity":"normal"},"market_stress":{"value":0.42,"threshold":0.70,"severity":"normal"},"liquidity_fragility":{"value":0.31,"threshold":0.65,"severity":"normal"}},
"defense_policies":{"risk_score_alert":0.55,"risk_score_throttle":0.70,"risk_score_freeze":0.85,"reserve_raise_ratio":0.15,"capital_throttle_ratio":0.50},"defense_actions":[],"mesh_events":[],"audit":[]}

class RiskNodeUpdate(BaseModel):
    node:str; value:float=Field(..., ge=0.0); threshold:float=Field(..., gt=0.0); severity:Optional[str]=None; context:Optional[Dict[str, Any]]=None
class RiskBatch(BaseModel):
    nodes: List[RiskNodeUpdate]
class DefensePolicyUpdate(BaseModel):
    risk_score_alert: Optional[float]=None; risk_score_throttle: Optional[float]=None; risk_score_freeze: Optional[float]=None; reserve_raise_ratio: Optional[float]=None; capital_throttle_ratio: Optional[float]=None

def now(): return datetime.utcnow().isoformat()+"Z"
def log_event(kind,payload):
    STATE["audit"].append({"id":str(uuid.uuid4()),"kind":kind,"timestamp":now(),"payload":payload}); STATE["audit"]=STATE["audit"][-500:]
def push_mesh_event(kind,payload):
    evt={"id":str(uuid.uuid4()),"kind":kind,"timestamp":now(),"payload":payload}; STATE["mesh_events"].append(evt); STATE["mesh_events"]=STATE["mesh_events"][-500:]; log_event(kind,payload); return evt
def compute_global_risk():
    nodes=STATE["risk_nodes"]; 
    if not nodes: STATE["global_risk_score"]=0.0; return 0.0
    normalized=[]
    for _, node in nodes.items():
        threshold=max(node.get("threshold",1.0),1e-9); ratio=min(node.get("value",0.0)/threshold,2.0); normalized.append(ratio/2.0)
    score=round(sum(normalized)/len(normalized),6); STATE["global_risk_score"]=score; return score
def apply_capital_defense():
    score=compute_global_risk(); policies=STATE["defense_policies"]
    if score>=policies["risk_score_freeze"]:
        STATE["capital_defense_state"]="freeze"; action={"action_id":f"DEF-{uuid.uuid4().hex[:12]}","action":"global_freeze","risk_score":score,"reserve_raise_ratio":policies["reserve_raise_ratio"],"capital_throttle_ratio":1.0,"timestamp":now()}
    elif score>=policies["risk_score_throttle"]:
        STATE["capital_defense_state"]="throttle"; action={"action_id":f"DEF-{uuid.uuid4().hex[:12]}","action":"capital_throttle","risk_score":score,"reserve_raise_ratio":policies["reserve_raise_ratio"],"capital_throttle_ratio":policies["capital_throttle_ratio"],"timestamp":now()}
    elif score>=policies["risk_score_alert"]:
        STATE["capital_defense_state"]="alert"; action={"action_id":f"DEF-{uuid.uuid4().hex[:12]}","action":"defense_alert","risk_score":score,"reserve_raise_ratio":0.0,"capital_throttle_ratio":0.0,"timestamp":now()}
    else:
        STATE["capital_defense_state"]="normal"; action={"action_id":f"DEF-{uuid.uuid4().hex[:12]}","action":"normal_state","risk_score":score,"reserve_raise_ratio":0.0,"capital_throttle_ratio":0.0,"timestamp":now()}
    STATE["defense_actions"].append(action); STATE["defense_actions"]=STATE["defense_actions"][-500:]; push_mesh_event("capital_defense_evaluated",action); return action

@app.get("/global-risk-mesh/status")
def status():
    compute_global_risk()
    return {"mission":"QNT30403","risk_mesh_mode":STATE["risk_mesh_mode"],"global_risk_score":STATE["global_risk_score"],"capital_defense_state":STATE["capital_defense_state"],"risk_nodes":STATE["risk_nodes"],"defense_policies":STATE["defense_policies"],"defense_action_count":len(STATE["defense_actions"]),"mesh_event_count":len(STATE["mesh_events"]),"audit_events":len(STATE["audit"])}

@app.post("/global-risk-mesh/node/update")
def update_node(payload: RiskNodeUpdate):
    severity=payload.severity
    if severity is None:
        ratio=payload.value/max(payload.threshold,1e-9); severity="critical" if ratio>=1.2 else "warning" if ratio>=1.0 else "normal"
    record={"value":payload.value,"threshold":payload.threshold,"severity":severity,"context":payload.context or {},"updated_at":now()}
    STATE["risk_nodes"][payload.node]=record; push_mesh_event("risk_node_updated",{"node":payload.node,**record}); action=apply_capital_defense()
    return {"status":"ok","node":payload.node,"record":record,"defense_action":action}

@app.post("/global-risk-mesh/nodes/update")
def update_nodes(payload: RiskBatch):
    updated=[]
    for node in payload.nodes:
        severity=node.severity
        if severity is None:
            ratio=node.value/max(node.threshold,1e-9); severity="critical" if ratio>=1.2 else "warning" if ratio>=1.0 else "normal"
        record={"value":node.value,"threshold":node.threshold,"severity":severity,"context":node.context or {},"updated_at":now()}
        STATE["risk_nodes"][node.node]=record; updated.append({"node":node.node,**record})
    push_mesh_event("risk_batch_updated",{"count":len(updated)}); action=apply_capital_defense(); return {"status":"ok","updated":updated,"defense_action":action}

@app.post("/global-risk-mesh/policies/update")
def update_policies(payload: DefensePolicyUpdate):
    data=payload.model_dump(exclude_none=True); STATE["defense_policies"].update(data); push_mesh_event("defense_policies_updated",data); action=apply_capital_defense(); return {"status":"ok","defense_policies":STATE["defense_policies"],"defense_action":action}

@app.post("/global-risk-mesh/defense/evaluate")
def evaluate_defense():
    action=apply_capital_defense(); return {"status":"ok","defense_action":action,"global_risk_score":STATE["global_risk_score"]}

@app.get("/global-risk-mesh/nodes")
def nodes(): return {"risk_nodes":STATE["risk_nodes"]}
@app.get("/global-risk-mesh/defense-actions")
def defense_actions(): return {"defense_actions":STATE["defense_actions"][::-1]}
@app.get("/global-risk-mesh/events")
def events(): return {"mesh_events":STATE["mesh_events"][::-1]}
@app.get("/global-risk-mesh/audit")
def audit(limit:int=25): return {"events":STATE["audit"][-limit:][::-1]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("global_risk_mesh_capital_defense:app", host="127.0.0.1", port=8010, reload=False)
