from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

app = FastAPI(title="QNT30396 Full End-to-End Trade Lifecycle Integration", version="1.0.0")

STATE = {
    "trade_ideas": {},
    "allocations": {},
    "execution_requests": {},
    "orders": {},
    "fills": {},
    "positions": {},
    "performance": {},
    "lifecycle_events": [],
    "audit": [],
}

class TradeIdea(BaseModel):
    strategy_id: str
    symbol: str
    side: str
    conviction: float = Field(..., ge=0.0, le=1.0)
    signal_strength: float = Field(..., ge=0.0, le=1.0)
    requested_qty: float = Field(..., gt=0)
    reference_price: float = Field(..., gt=0)
    metadata: Optional[Dict[str, Any]] = None

class AllocationDecision(BaseModel):
    trade_id: str
    capital_allocated: float = Field(..., gt=0)
    approved_qty: float = Field(..., gt=0)
    regime: str = "normal"
    execution_policy: Optional[Dict[str, Any]] = None

class ExecutionRequest(BaseModel):
    trade_id: str
    broker: str = "alpaca"
    order_type: str = "market"
    time_in_force: str = "day"

class FillReport(BaseModel):
    trade_id: str
    filled_qty: float = Field(..., gt=0)
    fill_price: float = Field(..., gt=0)
    venue: str = "alpaca_paper"
    fees: float = 0.0

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

def lifecycle(trade_id: str, stage: str, payload: Dict[str, Any]):
    evt = {
        "id": str(uuid.uuid4()),
        "trade_id": trade_id,
        "stage": stage,
        "timestamp": now(),
        "payload": payload,
    }
    STATE["lifecycle_events"].append(evt)
    STATE["lifecycle_events"] = STATE["lifecycle_events"][-2000:]
    return evt

@app.get("/trade-lifecycle/status")
def status():
    return {
        "mission": "QNT30396",
        "trade_ideas": len(STATE["trade_ideas"]),
        "allocations": len(STATE["allocations"]),
        "execution_requests": len(STATE["execution_requests"]),
        "orders": len(STATE["orders"]),
        "fills": len(STATE["fills"]),
        "positions": len(STATE["positions"]),
        "performance_records": len(STATE["performance"]),
        "lifecycle_events": len(STATE["lifecycle_events"]),
        "audit_events": len(STATE["audit"]),
    }

@app.post("/trade-lifecycle/idea")
def create_trade_idea(payload: TradeIdea):
    trade_id = f"TRD-{uuid.uuid4().hex[:12]}"
    record = payload.model_dump()
    record.update({
        "trade_id": trade_id,
        "status": "idea_created",
        "created_at": now(),
    })
    STATE["trade_ideas"][trade_id] = record
    lifecycle(trade_id, "idea_created", record)
    log_event("trade_idea_created", {"trade_id": trade_id, "symbol": payload.symbol, "strategy_id": payload.strategy_id})
    return {"status": "ok", "trade": record}

@app.post("/trade-lifecycle/allocation")
def allocate_trade(payload: AllocationDecision):
    if payload.trade_id not in STATE["trade_ideas"]:
        raise HTTPException(status_code=404, detail={"reason": "trade_not_found"})
    alloc = payload.model_dump()
    alloc["allocated_at"] = now()
    alloc["status"] = "allocated"
    STATE["allocations"][payload.trade_id] = alloc
    STATE["trade_ideas"][payload.trade_id]["status"] = "allocated"
    lifecycle(payload.trade_id, "allocation_approved", alloc)
    log_event("trade_allocated", {"trade_id": payload.trade_id, "capital_allocated": payload.capital_allocated})
    return {"status": "ok", "allocation": alloc}

@app.post("/trade-lifecycle/execution-request")
def request_execution(payload: ExecutionRequest):
    if payload.trade_id not in STATE["allocations"]:
        raise HTTPException(status_code=400, detail={"reason": "allocation_required"})
    req = payload.model_dump()
    req.update({
        "execution_request_id": f"EXR-{uuid.uuid4().hex[:12]}",
        "requested_at": now(),
        "status": "execution_requested",
    })
    STATE["execution_requests"][payload.trade_id] = req
    lifecycle(payload.trade_id, "execution_requested", req)
    log_event("execution_requested", {"trade_id": payload.trade_id, "broker": payload.broker})
    return {"status": "ok", "execution_request": req}

@app.post("/trade-lifecycle/order-submit/{trade_id}")
def submit_order(trade_id: str):
    if trade_id not in STATE["execution_requests"]:
        raise HTTPException(status_code=400, detail={"reason": "execution_request_required"})
    idea = STATE["trade_ideas"][trade_id]
    alloc = STATE["allocations"][trade_id]
    req = STATE["execution_requests"][trade_id]
    order = {
        "order_id": f"ORD-{uuid.uuid4().hex[:12]}",
        "trade_id": trade_id,
        "symbol": idea["symbol"],
        "side": idea["side"],
        "qty": alloc["approved_qty"],
        "reference_price": idea["reference_price"],
        "broker": req["broker"],
        "order_type": req["order_type"],
        "time_in_force": req["time_in_force"],
        "status": "submitted",
        "submitted_at": now(),
    }
    STATE["orders"][trade_id] = order
    STATE["trade_ideas"][trade_id]["status"] = "order_submitted"
    lifecycle(trade_id, "order_submitted", order)
    log_event("order_submitted", {"trade_id": trade_id, "order_id": order["order_id"]})
    return {"status": "ok", "order": order}

@app.post("/trade-lifecycle/fill")
def report_fill(payload: FillReport):
    trade_id = payload.trade_id
    if trade_id not in STATE["orders"]:
        raise HTTPException(status_code=400, detail={"reason": "order_required"})
    idea = STATE["trade_ideas"][trade_id]
    fill = payload.model_dump()
    fill.update({
        "fill_id": f"FIL-{uuid.uuid4().hex[:12]}",
        "filled_at": now(),
        "status": "filled",
    })
    STATE["fills"][trade_id] = fill
    STATE["trade_ideas"][trade_id]["status"] = "filled"

    side_mult = 1 if idea["side"].lower() == "buy" else -1
    pos = STATE["positions"].get(idea["symbol"], {"qty": 0.0, "avg_price": 0.0})
    new_qty = pos["qty"] + (payload.filled_qty * side_mult)
    new_avg = payload.fill_price if new_qty != 0 else 0.0
    STATE["positions"][idea["symbol"]] = {"qty": round(new_qty, 6), "avg_price": round(new_avg, 6)}

    perf = {
        "trade_id": trade_id,
        "symbol": idea["symbol"],
        "filled_qty": payload.filled_qty,
        "fill_price": payload.fill_price,
        "fees": payload.fees,
        "estimated_notional": round(payload.filled_qty * payload.fill_price, 2),
        "slippage_vs_reference": round(payload.fill_price - idea["reference_price"], 6),
        "venue": payload.venue,
        "recorded_at": now(),
    }
    STATE["performance"][trade_id] = perf

    lifecycle(trade_id, "fill_reported", fill)
    lifecycle(trade_id, "position_updated", STATE["positions"][idea["symbol"]])
    lifecycle(trade_id, "performance_recorded", perf)
    log_event("fill_reported", {"trade_id": trade_id, "fill_id": fill["fill_id"], "venue": payload.venue})
    return {"status": "ok", "fill": fill, "position": STATE["positions"][idea["symbol"]], "performance": perf}

@app.get("/trade-lifecycle/trade/{trade_id}")
def get_trade(trade_id: str):
    if trade_id not in STATE["trade_ideas"]:
        raise HTTPException(status_code=404, detail={"reason": "trade_not_found"})
    return {
        "trade": STATE["trade_ideas"].get(trade_id),
        "allocation": STATE["allocations"].get(trade_id),
        "execution_request": STATE["execution_requests"].get(trade_id),
        "order": STATE["orders"].get(trade_id),
        "fill": STATE["fills"].get(trade_id),
        "performance": STATE["performance"].get(trade_id),
    }

@app.get("/trade-lifecycle/positions")
def get_positions():
    return {"positions": STATE["positions"]}

@app.get("/trade-lifecycle/lifecycle")
def get_lifecycle(limit: int = 100):
    return {"events": STATE["lifecycle_events"][-limit:][::-1]}

@app.post("/trade-lifecycle/run-demo")
def run_demo():
    trade = create_trade_idea(TradeIdea(
        strategy_id="alpha-exec-01",
        symbol="AAPL",
        side="buy",
        conviction=0.82,
        signal_strength=0.76,
        requested_qty=10,
        reference_price=100.0
    ))["trade"]
    trade_id = trade["trade_id"]
    allocate_trade(AllocationDecision(
        trade_id=trade_id,
        capital_allocated=1000.0,
        approved_qty=10,
        regime="normal",
        execution_policy={"mode": "adaptive"}
    ))
    request_execution(ExecutionRequest(trade_id=trade_id, broker="alpaca"))
    submit_order(trade_id)
    report_fill(FillReport(trade_id=trade_id, filled_qty=10, fill_price=100.2, venue="alpaca_paper", fees=1.25))
    return get_trade(trade_id)

@app.get("/trade-lifecycle/audit")
def audit(limit: int = 25):
    return {"events": STATE["audit"][-limit:][::-1]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("trade_lifecycle_integration:app", host="127.0.0.1", port=8010, reload=False)
