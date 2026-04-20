from fastapi import FastAPI
from typing import Dict, Any
from datetime import datetime
import uuid

app = FastAPI(title="QNT30407 Unified Quantora Runtime Orchestrator", version="1.0.0")

STATE = {
    "runtime_mode": "active",
    "modules": {
        "execution": {"status": "online", "health": "green"},
        "strategy_competition": {"status": "online", "health": "green"},
        "capital_orchestrator": {"status": "online", "health": "green"},
        "multi_asset_routing": {"status": "online", "health": "green"},
        "cross_market_intelligence": {"status": "online", "health": "green"},
        "global_risk_mesh": {"status": "online", "health": "green"},
        "treasury": {"status": "online", "health": "green"},
        "governance": {"status": "online", "health": "green"},
        "control_tower": {"status": "online", "health": "green"},
        "broker_bridge": {"status": "online", "health": "green"},
    },
    "event_bus": [],
    "system_state": {
        "global_mode": "autonomous",
        "risk_state": "safe",
        "capital_state": "deployable",
        "broker_state": "paper_connected",
    },
    "audit": [],
}

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

def push_bus(topic: str, payload: Dict[str, Any]):
    event = {
        "event_id": f"BUS-{uuid.uuid4().hex[:12]}",
        "topic": topic,
        "timestamp": now(),
        "payload": payload,
    }
    STATE["event_bus"].append(event)
    STATE["event_bus"] = STATE["event_bus"][-1000:]
    log_event("event_bus_published", {"topic": topic, "payload": payload})
    return event

@app.get("/runtime-orchestrator/status")
def status():
    return {
        "mission": "QNT30407",
        "runtime_mode": STATE["runtime_mode"],
        "modules": STATE["modules"],
        "system_state": STATE["system_state"],
        "event_bus_depth": len(STATE["event_bus"]),
        "audit_events": len(STATE["audit"]),
    }

@app.get("/runtime-orchestrator/modules")
def modules():
    return {"modules": STATE["modules"]}

@app.post("/runtime-orchestrator/module/set")
def set_module(module: str, status: str = "online", health: str = "green"):
    if module not in STATE["modules"]:
        return {"status": "error", "reason": "unknown_module"}
    STATE["modules"][module]["status"] = status
    STATE["modules"][module]["health"] = health
    push_bus("module.state.changed", {"module": module, "status": status, "health": health})
    return {"status": "ok", "module": module, "state": STATE["modules"][module]}

@app.post("/runtime-orchestrator/system/set")
def set_system_state(global_mode: str = "autonomous", risk_state: str = "safe", capital_state: str = "deployable", broker_state: str = "paper_connected"):
    STATE["system_state"] = {
        "global_mode": global_mode,
        "risk_state": risk_state,
        "capital_state": capital_state,
        "broker_state": broker_state,
    }
    push_bus("system.state.updated", STATE["system_state"])
    return {"status": "ok", "system_state": STATE["system_state"]}

@app.post("/runtime-orchestrator/event/publish")
def publish_event(topic: str, message: str):
    event = push_bus(topic, {"message": message})
    return {"status": "ok", "event": event}

@app.post("/runtime-orchestrator/demo/run")
def run_demo():
    push_bus("strategy.champion.selected", {"strategy_id": "alpha-exec-01", "score": 94.2})
    push_bus("capital.rebalanced", {"deployed_capital": 500000, "reserve_capital": 500000})
    push_bus("risk.mesh.updated", {"global_risk_score": 0.41, "capital_defense_state": "normal"})
    push_bus("broker.bridge.connected", {"broker_mode": "paper", "base_url": "https://paper-api.alpaca.markets"})
    push_bus("control.tower.alert", {"message": "Unified runtime orchestration demo completed", "severity": "info"})
    return {
        "status": "ok",
        "summary": {
            "events_published": 5,
            "system_state": STATE["system_state"],
            "modules_online": len([m for m in STATE["modules"].values() if m["status"] == "online"]),
        }
    }

@app.get("/runtime-orchestrator/event-bus")
def event_bus(limit: int = 100):
    return {"events": STATE["event_bus"][-limit:][::-1]}

@app.get("/runtime-orchestrator/audit")
def audit(limit: int = 25):
    return {"events": STATE["audit"][-limit:][::-1]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("unified_quantora_runtime_orchestrator:app", host="127.0.0.1", port=8010, reload=False)
