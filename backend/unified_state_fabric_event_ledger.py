from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
import json
import os

app = FastAPI(title="QNT30408 Unified Quantora State Fabric & Persistent Event Ledger", version="1.0.0")

BASE_DIR = os.path.dirname(__file__)
STATE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "state"))
LEDGER_FILE = os.path.join(STATE_DIR, "event_ledger.json")
FABRIC_FILE = os.path.join(STATE_DIR, "state_fabric.json")

DEFAULT_FABRIC = {
    "global_state": {
        "runtime_mode": "active",
        "risk_state": "safe",
        "capital_state": "deployable",
        "broker_state": "paper_connected",
        "governance_state": "active",
    },
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
    "snapshots": [],
}

def now():
    return datetime.utcnow().isoformat() + "Z"

def ensure_files():
    os.makedirs(STATE_DIR, exist_ok=True)
    if not os.path.exists(LEDGER_FILE):
        with open(LEDGER_FILE, "w", encoding="utf-8") as f:
            json.dump({"events": []}, f, indent=2)
    if not os.path.exists(FABRIC_FILE):
        with open(FABRIC_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_FABRIC, f, indent=2)

def load_ledger():
    ensure_files()
    with open(LEDGER_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_ledger(data):
    with open(LEDGER_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def load_fabric():
    ensure_files()
    with open(FABRIC_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_fabric(data):
    with open(FABRIC_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def append_event(topic: str, payload: Dict[str, Any]):
    ledger = load_ledger()
    event = {
        "event_id": f"EVT-{uuid.uuid4().hex[:12]}",
        "topic": topic,
        "timestamp": now(),
        "payload": payload,
    }
    ledger["events"].append(event)
    ledger["events"] = ledger["events"][-5000:]
    save_ledger(ledger)
    return event

class FabricStateUpdate(BaseModel):
    runtime_mode: Optional[str] = None
    risk_state: Optional[str] = None
    capital_state: Optional[str] = None
    broker_state: Optional[str] = None
    governance_state: Optional[str] = None

class ModuleStateUpdate(BaseModel):
    module: str
    status: str = "online"
    health: str = "green"

class EventPublish(BaseModel):
    topic: str
    payload: Dict[str, Any]

@app.get("/state-fabric/status")
def status():
    fabric = load_fabric()
    ledger = load_ledger()
    return {
        "mission": "QNT30408",
        "global_state": fabric["global_state"],
        "module_count": len(fabric["modules"]),
        "snapshot_count": len(fabric["snapshots"]),
        "ledger_event_count": len(ledger["events"]),
        "fabric_file": FABRIC_FILE,
        "ledger_file": LEDGER_FILE,
    }

@app.get("/state-fabric/global")
def global_state():
    return load_fabric()["global_state"]

@app.post("/state-fabric/global/update")
def update_global_state(payload: FabricStateUpdate):
    fabric = load_fabric()
    data = payload.model_dump(exclude_none=True)
    fabric["global_state"].update(data)
    save_fabric(fabric)
    event = append_event("state.global.updated", data)
    return {"status": "ok", "global_state": fabric["global_state"], "event": event}

@app.get("/state-fabric/modules")
def modules():
    return {"modules": load_fabric()["modules"]}

@app.post("/state-fabric/module/update")
def update_module(payload: ModuleStateUpdate):
    fabric = load_fabric()
    if payload.module not in fabric["modules"]:
        fabric["modules"][payload.module] = {}
    fabric["modules"][payload.module] = {"status": payload.status, "health": payload.health}
    save_fabric(fabric)
    event = append_event("state.module.updated", payload.model_dump())
    return {"status": "ok", "module": payload.module, "state": fabric["modules"][payload.module], "event": event}

@app.post("/state-fabric/event/publish")
def publish_event(payload: EventPublish):
    event = append_event(payload.topic, payload.payload)
    return {"status": "ok", "event": event}

@app.get("/state-fabric/ledger")
def ledger(limit: int = 100):
    data = load_ledger()
    return {"events": data["events"][-limit:][::-1]}

@app.post("/state-fabric/snapshot")
def snapshot():
    fabric = load_fabric()
    snap = {
        "snapshot_id": f"SNP-{uuid.uuid4().hex[:12]}",
        "timestamp": now(),
        "global_state": fabric["global_state"],
        "modules": fabric["modules"],
    }
    fabric["snapshots"].append(snap)
    fabric["snapshots"] = fabric["snapshots"][-500:]
    save_fabric(fabric)
    event = append_event("state.snapshot.created", {"snapshot_id": snap["snapshot_id"]})
    return {"status": "ok", "snapshot": snap, "event": event}

@app.get("/state-fabric/snapshots")
def snapshots():
    return {"snapshots": load_fabric()["snapshots"][::-1]}

@app.post("/state-fabric/demo/run")
def demo_run():
    update_global_state(FabricStateUpdate(runtime_mode="active", risk_state="safe", capital_state="deployable", broker_state="paper_connected", governance_state="active"))
    update_module(ModuleStateUpdate(module="execution", status="online", health="green"))
    update_module(ModuleStateUpdate(module="broker_bridge", status="online", health="green"))
    append_event("strategy.champion.selected", {"strategy_id": "alpha-exec-01", "score": 94.2})
    append_event("capital.rebalanced", {"deployed_capital": 500000, "reserve_capital": 500000})
    append_event("risk.mesh.updated", {"global_risk_score": 0.41, "capital_defense_state": "normal"})
    snap = snapshot()
    return {
        "status": "ok",
        "summary": {
            "demo_events_written": 5,
            "snapshot_id": snap["snapshot"]["snapshot_id"],
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("unified_state_fabric_event_ledger:app", host="127.0.0.1", port=8010, reload=False)
