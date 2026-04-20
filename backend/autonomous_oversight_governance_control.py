from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

app = FastAPI(title="QNT30398 Autonomous Oversight & Governance Control Layer", version="1.0.0")

STATE = {
    "governance_mode": "active",
    "autonomous_oversight_enabled": True,
    "global_freeze": False,
    "risk_thresholds": {
        "max_drawdown": 0.10,
        "max_daily_loss": 25000.0,
        "max_execution_drift": 0.15,
        "max_policy_breach_count": 3,
    },
    "watchlist": [],
    "breaches": [],
    "approvals": [],
    "policy_overrides": {},
    "decisions": [],
    "control_actions": [],
    "audit": [],
}

class ThresholdUpdate(BaseModel):
    max_drawdown: Optional[float] = None
    max_daily_loss: Optional[float] = None
    max_execution_drift: Optional[float] = None
    max_policy_breach_count: Optional[int] = None

class OversightSignal(BaseModel):
    source: str
    metric: str
    value: float
    threshold: float
    severity: str = "warning"
    context: Optional[Dict[str, Any]] = None

class ApprovalRequest(BaseModel):
    action_type: str
    requested_by: str
    summary: str
    payload: Optional[Dict[str, Any]] = None

class ApprovalDecision(BaseModel):
    approval_id: str
    decided_by: str
    decision: str
    note: Optional[str] = None

class OverrideRequest(BaseModel):
    key: str
    value: Any
    reason: str
    operator_id: str

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

def add_control_action(action: str, payload: Dict[str, Any]):
    entry = {
        "id": str(uuid.uuid4()),
        "action": action,
        "timestamp": now(),
        "payload": payload,
    }
    STATE["control_actions"].append(entry)
    STATE["control_actions"] = STATE["control_actions"][-500:]
    log_event(action, payload)
    return entry

@app.get("/governance/status")
def status():
    return {
        "mission": "QNT30398",
        "governance_mode": STATE["governance_mode"],
        "autonomous_oversight_enabled": STATE["autonomous_oversight_enabled"],
        "global_freeze": STATE["global_freeze"],
        "risk_thresholds": STATE["risk_thresholds"],
        "watchlist_count": len(STATE["watchlist"]),
        "breach_count": len(STATE["breaches"]),
        "approval_count": len(STATE["approvals"]),
        "override_count": len(STATE["policy_overrides"]),
        "decision_count": len(STATE["decisions"]),
        "control_action_count": len(STATE["control_actions"]),
        "audit_events": len(STATE["audit"]),
    }

@app.post("/governance/thresholds/update")
def update_thresholds(payload: ThresholdUpdate):
    data = payload.model_dump(exclude_none=True)
    STATE["risk_thresholds"].update(data)
    add_control_action("thresholds_updated", data)
    return {"status": "ok", "risk_thresholds": STATE["risk_thresholds"]}

@app.post("/governance/signal/ingest")
def ingest_signal(payload: OversightSignal):
    signal = payload.model_dump()
    signal["signal_id"] = f"SIG-{uuid.uuid4().hex[:12]}"
    signal["ingested_at"] = now()

    breached = payload.value > payload.threshold
    signal["breached"] = breached

    if breached:
        breach = {
            "breach_id": f"BRH-{uuid.uuid4().hex[:12]}",
            "source": payload.source,
            "metric": payload.metric,
            "value": payload.value,
            "threshold": payload.threshold,
            "severity": payload.severity,
            "context": payload.context or {},
            "created_at": now(),
            "status": "open",
        }
        STATE["breaches"].append(breach)
        if payload.source not in STATE["watchlist"]:
            STATE["watchlist"].append(payload.source)

        decision = {
            "decision_id": f"DEC-{uuid.uuid4().hex[:12]}",
            "source": payload.source,
            "metric": payload.metric,
            "decision": "freeze_source" if payload.severity == "critical" else "watch_source",
            "reason": "threshold_breach_detected",
            "timestamp": now(),
        }
        STATE["decisions"].append(decision)
        add_control_action("oversight_breach_detected", {
            "breach_id": breach["breach_id"],
            "source": payload.source,
            "metric": payload.metric,
            "decision": decision["decision"],
        })

        if payload.severity == "critical":
            STATE["global_freeze"] = True
            add_control_action("global_freeze_enabled", {"reason": "critical_oversight_breach", "source": payload.source})

        return {"status": "breach_detected", "signal": signal, "breach": breach, "decision": decision}

    add_control_action("oversight_signal_clear", {"source": payload.source, "metric": payload.metric, "value": payload.value})
    return {"status": "clear", "signal": signal}

@app.get("/governance/watchlist")
def watchlist():
    return {"watchlist": STATE["watchlist"]}

@app.get("/governance/breaches")
def breaches():
    return {"breaches": STATE["breaches"][::-1]}

@app.post("/governance/approval/request")
def request_approval(payload: ApprovalRequest):
    approval = {
        "approval_id": f"APR-{uuid.uuid4().hex[:12]}",
        "action_type": payload.action_type,
        "requested_by": payload.requested_by,
        "summary": payload.summary,
        "payload": payload.payload or {},
        "status": "pending",
        "requested_at": now(),
    }
    STATE["approvals"].append(approval)
    add_control_action("approval_requested", {"approval_id": approval["approval_id"], "action_type": payload.action_type})
    return {"status": "ok", "approval": approval}

@app.post("/governance/approval/decide")
def decide_approval(payload: ApprovalDecision):
    for approval in STATE["approvals"]:
        if approval["approval_id"] == payload.approval_id:
            if payload.decision not in {"approved", "rejected"}:
                raise HTTPException(status_code=400, detail={"reason": "invalid_decision"})
            approval["status"] = payload.decision
            approval["decided_by"] = payload.decided_by
            approval["note"] = payload.note or ""
            approval["decided_at"] = now()
            add_control_action("approval_decided", {
                "approval_id": payload.approval_id,
                "decision": payload.decision,
                "decided_by": payload.decided_by,
            })
            return {"status": "ok", "approval": approval}
    raise HTTPException(status_code=404, detail={"reason": "approval_not_found"})

@app.post("/governance/override/set")
def set_override(payload: OverrideRequest):
    override = {
        "key": payload.key,
        "value": payload.value,
        "reason": payload.reason,
        "operator_id": payload.operator_id,
        "updated_at": now(),
    }
    STATE["policy_overrides"][payload.key] = override
    add_control_action("policy_override_set", {"key": payload.key, "operator_id": payload.operator_id})
    return {"status": "ok", "override": override}

@app.post("/governance/freeze")
def freeze(enabled: bool = True, reason: str = "manual_governance_action"):
    STATE["global_freeze"] = enabled
    add_control_action("global_freeze_toggled", {"enabled": enabled, "reason": reason})
    return {"status": "ok", "global_freeze": STATE["global_freeze"]}

@app.get("/governance/decisions")
def decisions():
    return {"decisions": STATE["decisions"][::-1]}

@app.get("/governance/control-actions")
def control_actions():
    return {"control_actions": STATE["control_actions"][::-1]}

@app.get("/governance/audit")
def audit(limit: int = 25):
    return {"events": STATE["audit"][-limit:][::-1]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("autonomous_oversight_governance_control.py", host="127.0.0.1", port=8010, reload=False)
