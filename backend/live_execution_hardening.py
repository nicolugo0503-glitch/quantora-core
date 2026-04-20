from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

app = FastAPI(title="QNT30395 Live Execution Hardening", version="1.0.0")

STATE = {
    "mode": "paper_only",
    "live_enabled": False,
    "kill_switch": False,
    "require_dual_confirmation": True,
    "max_order_notional": 5000.0,
    "max_daily_notional": 25000.0,
    "max_position_qty": 100.0,
    "daily_notional_used": 0.0,
    "allowed_symbols": ["AAPL", "MSFT", "SPY", "TSLA", "NVDA"],
    "blocked_symbols": ["GME", "AMC"],
    "open_positions": {},
    "pending_confirmations": {},
    "orders": [],
    "guardrail_events": [],
    "audit": [],
}

class HardeningControls(BaseModel):
    live_enabled: Optional[bool] = None
    kill_switch: Optional[bool] = None
    require_dual_confirmation: Optional[bool] = None
    max_order_notional: Optional[float] = None
    max_daily_notional: Optional[float] = None
    max_position_qty: Optional[float] = None

class LiveTradeRequest(BaseModel):
    symbol: str
    side: str
    qty: float = Field(..., gt=0)
    price: float = Field(..., gt=0)
    strategy_id: Optional[str] = "live-execution"
    operator_id: Optional[str] = "governance-admin"
    reason: Optional[str] = "operator_submitted"

class ConfirmRequest(BaseModel):
    confirmation_id: str
    approver_id: str

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

def guardrail(kind: str, payload: Dict[str, Any]):
    event = {
        "id": str(uuid.uuid4()),
        "kind": kind,
        "timestamp": now(),
        "payload": payload,
    }
    STATE["guardrail_events"].append(event)
    STATE["guardrail_events"] = STATE["guardrail_events"][-500:]
    log_event(kind, payload)
    return event

def validate_trade(req: LiveTradeRequest):
    symbol = req.symbol.upper()
    side = req.side.lower()
    notional = req.qty * req.price

    if STATE["kill_switch"]:
        raise HTTPException(status_code=423, detail={"reason": "kill_switch_active"})
    if not STATE["live_enabled"]:
        raise HTTPException(status_code=403, detail={"reason": "live_execution_disabled"})
    if symbol in STATE["blocked_symbols"]:
        raise HTTPException(status_code=400, detail={"reason": "blocked_symbol", "symbol": symbol})
    if symbol not in STATE["allowed_symbols"]:
        raise HTTPException(status_code=400, detail={"reason": "symbol_not_allowlisted", "symbol": symbol})
    if side not in {"buy", "sell"}:
        raise HTTPException(status_code=400, detail={"reason": "invalid_side"})
    if notional > STATE["max_order_notional"]:
        raise HTTPException(status_code=400, detail={"reason": "max_order_notional_exceeded", "notional": notional, "limit": STATE["max_order_notional"]})
    if STATE["daily_notional_used"] + notional > STATE["max_daily_notional"]:
        raise HTTPException(status_code=400, detail={"reason": "max_daily_notional_exceeded", "requested": notional, "used": STATE["daily_notional_used"], "limit": STATE["max_daily_notional"]})

    pos = STATE["open_positions"].get(symbol, {"qty": 0.0})
    projected_qty = pos["qty"] + req.qty if side == "buy" else pos["qty"] - req.qty
    if abs(projected_qty) > STATE["max_position_qty"]:
        raise HTTPException(status_code=400, detail={"reason": "max_position_qty_exceeded", "projected_qty": projected_qty, "limit": STATE["max_position_qty"]})

    return {
        "status": "approved",
        "symbol": symbol,
        "side": side,
        "qty": req.qty,
        "price": req.price,
        "notional": round(notional, 2),
    }

@app.get("/live-hardening/status")
def status():
    return {
        "mission": "QNT30395",
        "mode": STATE["mode"],
        "live_enabled": STATE["live_enabled"],
        "kill_switch": STATE["kill_switch"],
        "require_dual_confirmation": STATE["require_dual_confirmation"],
        "max_order_notional": STATE["max_order_notional"],
        "max_daily_notional": STATE["max_daily_notional"],
        "daily_notional_used": round(STATE["daily_notional_used"], 2),
        "max_position_qty": STATE["max_position_qty"],
        "allowed_symbols": STATE["allowed_symbols"],
        "blocked_symbols": STATE["blocked_symbols"],
        "open_positions": STATE["open_positions"],
        "pending_confirmations": len(STATE["pending_confirmations"]),
        "orders": len(STATE["orders"]),
        "guardrail_events": len(STATE["guardrail_events"]),
        "audit_events": len(STATE["audit"]),
    }

@app.post("/live-hardening/controls/update")
def update_controls(payload: HardeningControls):
    data = payload.model_dump(exclude_none=True)
    for key, value in data.items():
        STATE[key] = value
    if STATE["live_enabled"]:
        STATE["mode"] = "live_armed"
    else:
        STATE["mode"] = "paper_only"
    log_event("hardening_controls_updated", data)
    return {"status": "ok", "controls": {
        "mode": STATE["mode"],
        "live_enabled": STATE["live_enabled"],
        "kill_switch": STATE["kill_switch"],
        "require_dual_confirmation": STATE["require_dual_confirmation"],
        "max_order_notional": STATE["max_order_notional"],
        "max_daily_notional": STATE["max_daily_notional"],
        "max_position_qty": STATE["max_position_qty"],
    }}

@app.post("/live-hardening/precheck")
def precheck(req: LiveTradeRequest):
    result = validate_trade(req)
    guardrail("live_precheck_passed", result)
    return result

@app.post("/live-hardening/request")
def request_live_trade(req: LiveTradeRequest):
    pre = validate_trade(req)
    confirmation_id = f"CNF-{uuid.uuid4().hex[:12]}"
    record = {
        "confirmation_id": confirmation_id,
        "symbol": req.symbol.upper(),
        "side": req.side.lower(),
        "qty": req.qty,
        "price": req.price,
        "notional": round(req.qty * req.price, 2),
        "strategy_id": req.strategy_id,
        "operator_id": req.operator_id,
        "reason": req.reason,
        "created_at": now(),
        "status": "pending_second_approval" if STATE["require_dual_confirmation"] else "approved_for_execution",
        "approvals": [req.operator_id],
    }
    STATE["pending_confirmations"][confirmation_id] = record
    guardrail("live_trade_requested", {"confirmation_id": confirmation_id, "symbol": record["symbol"], "notional": record["notional"]})
    return {"status": "ok", "request": record, "precheck": pre}

@app.post("/live-hardening/confirm")
def confirm(req: ConfirmRequest):
    record = STATE["pending_confirmations"].get(req.confirmation_id)
    if not record:
        raise HTTPException(status_code=404, detail={"reason": "confirmation_not_found"})
    if req.approver_id not in record["approvals"]:
        record["approvals"].append(req.approver_id)
    if STATE["require_dual_confirmation"] and len(record["approvals"]) < 2:
        record["status"] = "pending_second_approval"
    else:
        record["status"] = "approved_for_execution"
    guardrail("live_trade_confirmed", {"confirmation_id": req.confirmation_id, "approvals": record["approvals"]})
    return {"status": "ok", "request": record}

@app.post("/live-hardening/execute/{confirmation_id}")
def execute(confirmation_id: str):
    record = STATE["pending_confirmations"].get(confirmation_id)
    if not record:
        raise HTTPException(status_code=404, detail={"reason": "confirmation_not_found"})
    if STATE["require_dual_confirmation"] and len(record["approvals"]) < 2:
        raise HTTPException(status_code=400, detail={"reason": "dual_confirmation_required"})
    if record["status"] != "approved_for_execution":
        raise HTTPException(status_code=400, detail={"reason": "not_ready_for_execution", "status": record["status"]})

    order_id = f"LIVE-{uuid.uuid4().hex[:12]}"
    order = {
        "order_id": order_id,
        "confirmation_id": confirmation_id,
        "symbol": record["symbol"],
        "side": record["side"],
        "qty": record["qty"],
        "price": record["price"],
        "notional": record["notional"],
        "status": "executed_live_guarded",
        "executed_at": now(),
    }
    STATE["orders"].append(order)
    STATE["daily_notional_used"] += record["notional"]

    pos = STATE["open_positions"].get(record["symbol"], {"qty": 0.0, "avg_price": 0.0})
    if record["side"] == "buy":
        new_qty = pos["qty"] + record["qty"]
    else:
        new_qty = pos["qty"] - record["qty"]
    STATE["open_positions"][record["symbol"]] = {"qty": round(new_qty, 6), "avg_price": record["price"]}

    record["status"] = "executed"
    guardrail("live_trade_executed", {"order_id": order_id, "symbol": record["symbol"], "notional": record["notional"]})
    return {"status": "ok", "order": order, "position_after": STATE["open_positions"][record["symbol"]]}

@app.post("/live-hardening/kill-switch")
def trigger_kill_switch(enabled: bool = True):
    STATE["kill_switch"] = enabled
    if enabled:
        STATE["mode"] = "live_frozen"
    else:
        STATE["mode"] = "live_armed" if STATE["live_enabled"] else "paper_only"
    guardrail("kill_switch_toggled", {"enabled": enabled, "mode": STATE["mode"]})
    return {"status": "ok", "kill_switch": STATE["kill_switch"], "mode": STATE["mode"]}

@app.get("/live-hardening/guardrails")
def guardrails(limit: int = 50):
    return {"events": STATE["guardrail_events"][-limit:][::-1]}

@app.get("/live-hardening/orders")
def orders():
    return {"orders": STATE["orders"][-100:][::-1]}

@app.get("/live-hardening/pending")
def pending():
    return {"pending_confirmations": list(STATE["pending_confirmations"].values())}

@app.get("/live-hardening/audit")
def audit(limit: int = 25):
    return {"events": STATE["audit"][-limit:][::-1]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("live_execution_hardening:app", host="127.0.0.1", port=8010, reload=False)
