from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

app = FastAPI(title="QNT30387 Production Readiness and Control Plane", version="1.0.0")

STATE = {
    "environment": "staging",
    "release_version": "qnt30387-v1",
    "global_trading_enabled": False,
    "maintenance_mode": False,
    "service_registry": {
        "qnt30379_adaptive_execution_brain": {"healthy": True, "required": True},
        "qnt30380_regime_allocation": {"healthy": True, "required": True},
        "qnt30381_trade_execution_engine": {"healthy": True, "required": True},
        "qnt30382_broker_integration": {"healthy": True, "required": True},
        "qnt30383_performance_engine": {"healthy": True, "required": True},
        "qnt30384_portfolio_manager": {"healthy": True, "required": True},
        "qnt30385_user_product_layer": {"healthy": True, "required": True},
        "qnt30386_monetization_layer": {"healthy": True, "required": True},
    },
    "controls": {
        "kill_switch": False,
        "max_notional_per_order": 100000.0,
        "max_daily_loss": 25000.0,
        "max_open_positions": 25,
        "live_execution_mode": False,
        "paper_mode_only": True,
    },
    "observability": {
        "logging": True,
        "metrics": True,
        "alerts": True,
        "trace_sampling": 0.25,
        "last_incident": None,
    },
    "deployments": [],
    "incidents": [],
    "audit": [],
}

class ControlUpdate(BaseModel):
    global_trading_enabled: Optional[bool] = None
    maintenance_mode: Optional[bool] = None
    kill_switch: Optional[bool] = None
    max_notional_per_order: Optional[float] = None
    max_daily_loss: Optional[float] = None
    max_open_positions: Optional[int] = None
    live_execution_mode: Optional[bool] = None
    paper_mode_only: Optional[bool] = None

class ServiceHeartbeat(BaseModel):
    service_name: str
    healthy: bool
    required: bool = True
    details: Optional[Dict[str, Any]] = None

class DeploymentRequest(BaseModel):
    actor: str
    release_version: str
    environment: str = "staging"
    notes: Optional[str] = None

class IncidentRequest(BaseModel):
    title: str
    severity: str
    service_name: str
    summary: Optional[str] = None

class IncidentResolveRequest(BaseModel):
    incident_id: str
    resolution: str

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

def release_gate_report():
    services = STATE["service_registry"]
    unhealthy_required = [name for name, meta in services.items() if meta.get("required") and not meta.get("healthy")]
    controls = STATE["controls"]
    blockers = []
    if STATE["maintenance_mode"]:
        blockers.append("maintenance_mode_enabled")
    if controls["kill_switch"]:
        blockers.append("kill_switch_enabled")
    if controls["live_execution_mode"] and controls["paper_mode_only"]:
        blockers.append("conflicting_execution_modes")
    blockers.extend([f"service_unhealthy:{x}" for x in unhealthy_required])
    ready = len(blockers) == 0
    return {
        "ready": ready,
        "blockers": blockers,
        "required_services": len([1 for x in services.values() if x.get("required")]),
        "healthy_required_services": len([1 for x in services.values() if x.get("required") and x.get("healthy")]),
        "global_trading_enabled": STATE["global_trading_enabled"],
        "live_execution_mode": controls["live_execution_mode"],
        "paper_mode_only": controls["paper_mode_only"],
    }

@app.get("/control-plane/health")
def health():
    return {
        "status": "ok",
        "mission": "QNT30387",
        "environment": STATE["environment"],
        "release_version": STATE["release_version"],
        "timestamp": now(),
    }

@app.get("/control-plane/readiness")
def readiness():
    report = release_gate_report()
    return {
        "mission": "QNT30387",
        "environment": STATE["environment"],
        "release_gate": report,
        "services": STATE["service_registry"],
        "controls": STATE["controls"],
    }

@app.get("/control-plane/status")
def status():
    return {
        "mission": "QNT30387",
        "environment": STATE["environment"],
        "release_version": STATE["release_version"],
        "global_trading_enabled": STATE["global_trading_enabled"],
        "maintenance_mode": STATE["maintenance_mode"],
        "deployments": len(STATE["deployments"]),
        "incidents": len(STATE["incidents"]),
        "audit_events": len(STATE["audit"]),
    }

@app.post("/control-plane/controls/update")
def update_controls(payload: ControlUpdate):
    data = payload.model_dump(exclude_none=True)
    for key, value in data.items():
        if key in ("global_trading_enabled", "maintenance_mode"):
            STATE[key] = value
        else:
            STATE["controls"][key] = value
    log_event("controls_updated", data)
    return {
        "status": "ok",
        "global": {
            "global_trading_enabled": STATE["global_trading_enabled"],
            "maintenance_mode": STATE["maintenance_mode"],
        },
        "controls": STATE["controls"],
        "readiness": release_gate_report(),
    }

@app.post("/control-plane/service/heartbeat")
def service_heartbeat(payload: ServiceHeartbeat):
    record = payload.model_dump()
    record["last_seen"] = now()
    STATE["service_registry"][payload.service_name] = record
    log_event("service_heartbeat", {"service_name": payload.service_name, "healthy": payload.healthy})
    return {"status": "ok", "service": STATE["service_registry"][payload.service_name]}

@app.get("/control-plane/services")
def services():
    return {"services": STATE["service_registry"]}

@app.post("/control-plane/deployment/register")
def deployment_register(payload: DeploymentRequest):
    deployment = {
        "deployment_id": f"DEP-{uuid.uuid4().hex[:10]}",
        "actor": payload.actor,
        "release_version": payload.release_version,
        "environment": payload.environment,
        "notes": payload.notes or "",
        "registered_at": now(),
        "readiness_snapshot": release_gate_report(),
    }
    STATE["release_version"] = payload.release_version
    STATE["environment"] = payload.environment
    STATE["deployments"].append(deployment)
    log_event("deployment_registered", deployment)
    return {"status": "ok", "deployment": deployment}

@app.get("/control-plane/deployments")
def deployments():
    return {"deployments": STATE["deployments"][-100:][::-1]}

@app.post("/control-plane/incident/create")
def incident_create(payload: IncidentRequest):
    incident = {
        "incident_id": f"INC-{uuid.uuid4().hex[:10]}",
        "title": payload.title,
        "severity": payload.severity,
        "service_name": payload.service_name,
        "summary": payload.summary or "",
        "status": "open",
        "created_at": now(),
        "resolved_at": None,
        "resolution": None,
    }
    STATE["incidents"].append(incident)
    STATE["observability"]["last_incident"] = incident["incident_id"]
    if payload.service_name in STATE["service_registry"]:
        STATE["service_registry"][payload.service_name]["healthy"] = False
    log_event("incident_created", incident)
    return {"status": "ok", "incident": incident, "readiness": release_gate_report()}

@app.post("/control-plane/incident/resolve")
def incident_resolve(payload: IncidentResolveRequest):
    for incident in STATE["incidents"]:
        if incident["incident_id"] == payload.incident_id:
            incident["status"] = "resolved"
            incident["resolved_at"] = now()
            incident["resolution"] = payload.resolution
            service_name = incident["service_name"]
            if service_name in STATE["service_registry"]:
                STATE["service_registry"][service_name]["healthy"] = True
            log_event("incident_resolved", {"incident_id": payload.incident_id, "resolution": payload.resolution})
            return {"status": "ok", "incident": incident, "readiness": release_gate_report()}
    return {"status": "error", "message": "incident not found"}

@app.get("/control-plane/incidents")
def incidents():
    return {"incidents": STATE["incidents"][-100:][::-1]}

@app.get("/control-plane/observability")
def observability():
    return {"observability": STATE["observability"], "audit_events": len(STATE["audit"])}

@app.get("/control-plane/audit")
def audit(limit: int = 25):
    return {"events": STATE["audit"][-limit:][::-1]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("production_control_plane:app", host="127.0.0.1", port=8010, reload=False)
