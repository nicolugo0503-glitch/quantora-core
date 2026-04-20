from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

app = FastAPI(title="QNT30382 Broker Integration Layer", version="1.0.0")

BROKERS = {
    "alpaca": {"enabled": True, "mode": "paper", "markets": ["equities", "crypto"]},
    "binance": {"enabled": True, "mode": "paper", "markets": ["crypto"]},
    "ibkr": {"enabled": True, "mode": "paper", "markets": ["equities", "options", "futures", "fx"]},
}

STATE = {"kill_switch": False, "last_order": None, "orders": [], "routes": [], "audit": []}

class BrokerCredentials(BaseModel):
    api_key: str = Field(..., min_length=3)
    api_secret: str = Field(..., min_length=3)
    base_url: Optional[str] = None

class OrderRequest(BaseModel):
    broker: str
    symbol: str
    side: str
    qty: float = Field(..., gt=0)
    order_type: str = "market"
    time_in_force: str = "day"
    strategy_id: Optional[str] = "default-strategy"
    allocation_id: Optional[str] = "default-allocation"
    execution_policy: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class DispatchRequest(BaseModel):
    orders: List[OrderRequest]

def log_event(kind: str, payload: Dict[str, Any]):
    STATE["audit"].append({
        "id": str(uuid.uuid4()),
        "kind": kind,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "payload": payload,
    })
    STATE["audit"] = STATE["audit"][-200:]

@app.get("/broker-integration/status")
def status():
    return {
        "mission": "QNT30382",
        "brokers": BROKERS,
        "kill_switch": STATE["kill_switch"],
        "order_count": len(STATE["orders"]),
        "last_order": STATE["last_order"],
        "audit_events": len(STATE["audit"]),
    }

@app.post("/broker-integration/credentials/{broker}")
def update_credentials(broker: str, creds: BrokerCredentials):
    if broker not in BROKERS:
        raise HTTPException(status_code=404, detail="Broker not supported")
    BROKERS[broker]["credentials_loaded"] = True
    BROKERS[broker]["base_url"] = creds.base_url or "paper-endpoint"
    log_event("credentials_updated", {"broker": broker, "base_url": BROKERS[broker]["base_url"]})
    return {"status": "ok", "broker": broker, "mode": BROKERS[broker]["mode"]}

@app.post("/broker-integration/controls/kill-switch")
def set_kill_switch(enabled: bool):
    STATE["kill_switch"] = enabled
    log_event("kill_switch", {"enabled": enabled})
    return {"kill_switch": STATE["kill_switch"]}

@app.post("/broker-integration/order/validate")
def validate_order(order: OrderRequest):
    if order.broker not in BROKERS:
        raise HTTPException(status_code=404, detail="Broker not supported")
    if STATE["kill_switch"]:
        raise HTTPException(status_code=423, detail="Kill switch active")
    if order.side.lower() not in {"buy", "sell"}:
        raise HTTPException(status_code=400, detail="Invalid side")
    route = {
        "broker": order.broker,
        "symbol": order.symbol.upper(),
        "markets": BROKERS[order.broker]["markets"],
        "execution_policy": order.execution_policy or {"mode": "baseline"},
        "approved": True,
    }
    log_event("order_validated", route)
    return route

@app.post("/broker-integration/order/submit")
def submit_order(order: OrderRequest):
    if STATE["kill_switch"]:
        raise HTTPException(status_code=423, detail="Kill switch active")
    if order.broker not in BROKERS:
        raise HTTPException(status_code=404, detail="Broker not supported")
    record = {
        "order_id": f"{order.broker.upper()}-{uuid.uuid4().hex[:12]}",
        "broker": order.broker,
        "symbol": order.symbol.upper(),
        "side": order.side.lower(),
        "qty": order.qty,
        "order_type": order.order_type,
        "time_in_force": order.time_in_force,
        "strategy_id": order.strategy_id,
        "allocation_id": order.allocation_id,
        "execution_policy": order.execution_policy or {"mode": "adaptive"},
        "metadata": order.metadata or {},
        "status": "accepted-paper",
        "submitted_at": datetime.utcnow().isoformat() + "Z",
    }
    STATE["orders"].append(record)
    STATE["orders"] = STATE["orders"][-500:]
    STATE["last_order"] = record
    log_event("order_submitted", record)
    return record

@app.post("/broker-integration/dispatch")
def dispatch(batch: DispatchRequest):
    if STATE["kill_switch"]:
        raise HTTPException(status_code=423, detail="Kill switch active")
    dispatched = [submit_order(order) for order in batch.orders]
    dispatch_record = {
        "dispatch_id": f"DISP-{uuid.uuid4().hex[:10]}",
        "count": len(dispatched),
        "brokers": sorted(list({o["broker"] for o in dispatched})),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    STATE["routes"].append(dispatch_record)
    log_event("dispatch_completed", dispatch_record)
    return {"dispatch": dispatch_record, "orders": dispatched}

@app.get("/broker-integration/audit")
def audit(limit: int = 25):
    return {"events": STATE["audit"][-limit:][::-1]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("broker_integration_layer:app", host="127.0.0.1", port=8010, reload=False)
