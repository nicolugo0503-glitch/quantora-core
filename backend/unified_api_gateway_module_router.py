from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

app = FastAPI(title="QNT30409 Unified Quantora API Gateway & Module Router", version="1.0.0")

STATE = {
    "gateway_mode": "active",
    "routes": {
        "execution": "/execution-validation/status",
        "broker_bridge": "/live-bridge/status",
        "strategy_competition": "/strategy-competition/status",
        "capital_orchestrator": "/capital-orchestrator/status",
        "multi_asset_routing": "/multi-asset-routing/status",
        "cross_market_intelligence": "/cross-market-intelligence/status",
        "global_risk_mesh": "/global-risk-mesh/status",
        "treasury": "/treasury/status",
        "governance": "/governance/status",
        "control_tower": "/control-tower/status",
        "runtime_orchestrator": "/runtime-orchestrator/status",
        "state_fabric": "/state-fabric/status",
    },
    "module_health": {},
    "request_log": [],
    "audit": [],
}

class RouteUpsert(BaseModel):
    module: str
    path: str

class ModuleHealthUpdate(BaseModel):
    module: str
    status: str = "online"
    health: str = "green"
    details: Optional[Dict[str, Any]] = None

def now():
    return datetime.utcnow().isoformat() + "Z"

def log_event(kind: str, payload: Dict[str, Any]):
    evt = {
        "id": str(uuid.uuid4()),
        "kind": kind,
        "timestamp": now(),
        "payload": payload,
    }
    STATE["audit"].append(evt)
    STATE["audit"] = STATE["audit"][-500:]
    return evt

@app.get("/api-gateway/status")
def status():
    return {
        "mission": "QNT30409",
        "gateway_mode": STATE["gateway_mode"],
        "route_count": len(STATE["routes"]),
        "module_health_count": len(STATE["module_health"]),
        "request_log_count": len(STATE["request_log"]),
        "audit_events": len(STATE["audit"]),
    }

@app.get("/api-gateway/routes")
def routes():
    return {"routes": STATE["routes"]}

@app.post("/api-gateway/route/upsert")
def upsert_route(payload: RouteUpsert):
    STATE["routes"][payload.module] = payload.path
    evt = log_event("gateway_route_upserted", payload.model_dump())
    return {"status": "ok", "routes": STATE["routes"], "event": evt}

@app.post("/api-gateway/module-health/update")
def update_module_health(payload: ModuleHealthUpdate):
    STATE["module_health"][payload.module] = {
        "status": payload.status,
        "health": payload.health,
        "details": payload.details or {},
        "updated_at": now(),
    }
    evt = log_event("gateway_module_health_updated", {"module": payload.module, "status": payload.status, "health": payload.health})
    return {"status": "ok", "module_health": STATE["module_health"][payload.module], "event": evt}

@app.get("/api-gateway/module-health")
def module_health():
    return {"module_health": STATE["module_health"]}

@app.post("/api-gateway/request/log")
def request_log(module: str, path: Optional[str] = None, method: str = "GET"):
    rec = {
        "request_id": f"REQ-{uuid.uuid4().hex[:12]}",
        "module": module,
        "path": path or STATE["routes"].get(module),
        "method": method,
        "timestamp": now(),
    }
    STATE["request_log"].append(rec)
    STATE["request_log"] = STATE["request_log"][-1000:]
    evt = log_event("gateway_request_logged", rec)
    return {"status": "ok", "request": rec, "event": evt}

@app.post("/api-gateway/demo/run")
def demo():
    update_module_health(ModuleHealthUpdate(module="broker_bridge", status="online", health="green", details={"mode":"paper"}))
    update_module_health(ModuleHealthUpdate(module="global_risk_mesh", status="online", health="green", details={"risk_score":0.41}))
    request_log(module="capital_orchestrator", method="POST")
    request_log(module="state_fabric", method="POST")
    evt = log_event("gateway_demo_completed", {"modules_checked": 2, "requests_logged": 2})
    return {"status": "ok", "summary": {"modules_checked": 2, "requests_logged": 2}, "event": evt}

@app.get("/api-gateway/request-log")
def request_log_view(limit: int = 100):
    return {"requests": STATE["request_log"][-limit:][::-1]}

@app.get("/api-gateway/audit")
def audit(limit: int = 25):
    return {"events": STATE["audit"][-limit:][::-1]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("unified_api_gateway_module_router:app", host="127.0.0.1", port=8010, reload=False)
