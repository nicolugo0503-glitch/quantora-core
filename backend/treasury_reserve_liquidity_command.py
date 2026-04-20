from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

app = FastAPI(title="QNT30404 Autonomous Treasury, Reserve, and Liquidity Command Layer", version="1.0.0")

STATE = {
    "treasury_mode": "active",
    "capital_base": 1000000.0,
    "cash_balance": 420000.0,
    "reserve_balance": 180000.0,
    "deployable_balance": 400000.0,
    "liquidity_buffers": {
        "operating_buffer": 75000.0,
        "defense_buffer": 50000.0,
        "redemption_buffer": 55000.0,
    },
    "policy": {
        "min_reserve_ratio": 0.15,
        "min_cash_ratio": 0.20,
        "max_deployable_ratio": 0.70,
        "liquidity_alert_ratio": 0.12,
    },
    "treasury_actions": [],
    "liquidity_alerts": [],
    "sweeps": [],
    "audit": [],
}

class TreasuryPolicyUpdate(BaseModel):
    min_reserve_ratio: Optional[float] = None
    min_cash_ratio: Optional[float] = None
    max_deployable_ratio: Optional[float] = None
    liquidity_alert_ratio: Optional[float] = None

class TreasurySnapshotUpdate(BaseModel):
    capital_base: Optional[float] = None
    cash_balance: Optional[float] = None
    reserve_balance: Optional[float] = None
    deployable_balance: Optional[float] = None

class SweepRequest(BaseModel):
    amount: float = Field(..., gt=0)
    from_bucket: str
    to_bucket: str
    reason: str
    operator_id: str = "treasury-admin"

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

def ratios():
    capital = max(STATE["capital_base"], 1e-9)
    return {
        "cash_ratio": round(STATE["cash_balance"] / capital, 6),
        "reserve_ratio": round(STATE["reserve_balance"] / capital, 6),
        "deployable_ratio": round(STATE["deployable_balance"] / capital, 6),
    }

def evaluate_liquidity():
    r = ratios()
    alerts = []
    policy = STATE["policy"]

    if r["reserve_ratio"] < policy["min_reserve_ratio"]:
        alerts.append({
            "severity": "warning",
            "type": "reserve_below_minimum",
            "current": r["reserve_ratio"],
            "threshold": policy["min_reserve_ratio"],
        })
    if r["cash_ratio"] < policy["min_cash_ratio"]:
        alerts.append({
            "severity": "warning",
            "type": "cash_below_minimum",
            "current": r["cash_ratio"],
            "threshold": policy["min_cash_ratio"],
        })
    if r["deployable_ratio"] > policy["max_deployable_ratio"]:
        alerts.append({
            "severity": "critical",
            "type": "deployable_above_maximum",
            "current": r["deployable_ratio"],
            "threshold": policy["max_deployable_ratio"],
        })
    if r["cash_ratio"] < policy["liquidity_alert_ratio"]:
        alerts.append({
            "severity": "critical",
            "type": "liquidity_alert_triggered",
            "current": r["cash_ratio"],
            "threshold": policy["liquidity_alert_ratio"],
        })

    STATE["liquidity_alerts"] = alerts
    return alerts

def add_action(action: str, payload: Dict[str, Any]):
    entry = {
        "action_id": f"TRS-{uuid.uuid4().hex[:12]}",
        "action": action,
        "timestamp": now(),
        "payload": payload,
    }
    STATE["treasury_actions"].append(entry)
    STATE["treasury_actions"] = STATE["treasury_actions"][-500:]
    log_event(action, payload)
    return entry

@app.get("/treasury/status")
def status():
    alerts = evaluate_liquidity()
    return {
        "mission": "QNT30404",
        "treasury_mode": STATE["treasury_mode"],
        "capital_base": STATE["capital_base"],
        "cash_balance": STATE["cash_balance"],
        "reserve_balance": STATE["reserve_balance"],
        "deployable_balance": STATE["deployable_balance"],
        "liquidity_buffers": STATE["liquidity_buffers"],
        "policy": STATE["policy"],
        "ratios": ratios(),
        "liquidity_alerts": alerts,
        "treasury_action_count": len(STATE["treasury_actions"]),
        "audit_events": len(STATE["audit"]),
    }

@app.post("/treasury/policy/update")
def update_policy(payload: TreasuryPolicyUpdate):
    data = payload.model_dump(exclude_none=True)
    STATE["policy"].update(data)
    alerts = evaluate_liquidity()
    action = add_action("treasury_policy_updated", data)
    return {"status": "ok", "policy": STATE["policy"], "liquidity_alerts": alerts, "action": action}

@app.post("/treasury/snapshot/update")
def update_snapshot(payload: TreasurySnapshotUpdate):
    data = payload.model_dump(exclude_none=True)
    for k, v in data.items():
        STATE[k] = float(v)
    alerts = evaluate_liquidity()
    action = add_action("treasury_snapshot_updated", data)
    return {"status": "ok", "balances": {
        "capital_base": STATE["capital_base"],
        "cash_balance": STATE["cash_balance"],
        "reserve_balance": STATE["reserve_balance"],
        "deployable_balance": STATE["deployable_balance"],
    }, "ratios": ratios(), "liquidity_alerts": alerts, "action": action}

@app.post("/treasury/sweep")
def sweep(payload: SweepRequest):
    buckets = {"cash_balance", "reserve_balance", "deployable_balance"}
    if payload.from_bucket not in buckets or payload.to_bucket not in buckets:
        return {"status": "error", "message": "invalid bucket"}
    if payload.from_bucket == payload.to_bucket:
        return {"status": "error", "message": "from_bucket and to_bucket must differ"}
    if STATE[payload.from_bucket] < payload.amount:
        return {"status": "error", "message": "insufficient balance"}

    STATE[payload.from_bucket] -= payload.amount
    STATE[payload.to_bucket] += payload.amount

    record = {
        "sweep_id": f"SWP-{uuid.uuid4().hex[:12]}",
        "amount": payload.amount,
        "from_bucket": payload.from_bucket,
        "to_bucket": payload.to_bucket,
        "reason": payload.reason,
        "operator_id": payload.operator_id,
        "timestamp": now(),
    }
    STATE["sweeps"].append(record)
    STATE["sweeps"] = STATE["sweeps"][-500:]
    alerts = evaluate_liquidity()
    action = add_action("treasury_sweep_executed", record)
    return {"status": "ok", "sweep": record, "balances": {
        "cash_balance": STATE["cash_balance"],
        "reserve_balance": STATE["reserve_balance"],
        "deployable_balance": STATE["deployable_balance"],
    }, "liquidity_alerts": alerts, "action": action}

@app.post("/treasury/auto-balance")
def auto_balance():
    capital = max(STATE["capital_base"], 1e-9)
    target_reserve = capital * STATE["policy"]["min_reserve_ratio"]
    target_cash = capital * STATE["policy"]["min_cash_ratio"]

    actions = []

    if STATE["reserve_balance"] < target_reserve and STATE["deployable_balance"] > 0:
        needed = min(target_reserve - STATE["reserve_balance"], STATE["deployable_balance"])
        STATE["deployable_balance"] -= needed
        STATE["reserve_balance"] += needed
        actions.append({"move": "deployable_to_reserve", "amount": round(needed, 2)})

    if STATE["cash_balance"] < target_cash and STATE["deployable_balance"] > 0:
        needed = min(target_cash - STATE["cash_balance"], STATE["deployable_balance"])
        STATE["deployable_balance"] -= needed
        STATE["cash_balance"] += needed
        actions.append({"move": "deployable_to_cash", "amount": round(needed, 2)})

    alerts = evaluate_liquidity()
    action = add_action("treasury_auto_balance_run", {"moves": actions})
    return {"status": "ok", "moves": actions, "balances": {
        "cash_balance": STATE["cash_balance"],
        "reserve_balance": STATE["reserve_balance"],
        "deployable_balance": STATE["deployable_balance"],
    }, "liquidity_alerts": alerts, "action": action}

@app.get("/treasury/actions")
def actions():
    return {"treasury_actions": STATE["treasury_actions"][::-1]}

@app.get("/treasury/sweeps")
def sweeps():
    return {"sweeps": STATE["sweeps"][::-1]}

@app.get("/treasury/audit")
def audit(limit: int = 25):
    return {"events": STATE["audit"][-limit:][::-1]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("treasury_reserve_liquidity_command:app", host="127.0.0.1", port=8010, reload=False)
