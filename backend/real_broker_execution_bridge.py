from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime
import uuid
import os

app = FastAPI(title="QNT30406 Real Broker Execution Bridge", version="1.0.0")

STATE = {
    "broker_mode": "paper",
    "env_ready": False,
    "base_url": None,
    "connected": False,
    "orders": [],
    "positions": {},
    "fills": [],
    "audit": [],
}

class BrokerConnectRequest(BaseModel):
    api_key: Optional[str] = None
    secret_key: Optional[str] = None
    base_url: Optional[str] = None
    mode: str = "paper"

class LiveOrderRequest(BaseModel):
    symbol: str
    side: str
    qty: float = Field(..., gt=0)
    order_type: str = "market"
    time_in_force: str = "day"
    broker: str = "alpaca"
    use_env: bool = True

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

def env_snapshot():
    api_key = os.getenv("ALPACA_API_KEY") or os.getenv("APCA_API_KEY_ID")
    secret_key = os.getenv("ALPACA_SECRET_KEY") or os.getenv("APCA_API_SECRET_KEY")
    base_url = os.getenv("ALPACA_BASE_URL") or os.getenv("APCA_API_BASE_URL") or "https://paper-api.alpaca.markets"
    paper = str(os.getenv("ALPACA_PAPER", "true")).lower() == "true"
    return {
        "api_key_present": bool(api_key),
        "secret_key_present": bool(secret_key),
        "base_url": base_url,
        "paper": paper,
        "mode": "paper" if paper else "live",
    }

@app.get("/live-bridge/status")
def status():
    env = env_snapshot()
    STATE["env_ready"] = env["api_key_present"] and env["secret_key_present"]
    if STATE["base_url"] is None:
        STATE["base_url"] = env["base_url"]
    return {
        "mission": "QNT30406",
        "broker_mode": STATE["broker_mode"],
        "env_ready": STATE["env_ready"],
        "connected": STATE["connected"],
        "base_url": STATE["base_url"],
        "orders": len(STATE["orders"]),
        "fills": len(STATE["fills"]),
        "positions": STATE["positions"],
        "env": env,
        "audit_events": len(STATE["audit"]),
    }

@app.post("/live-bridge/connect")
def connect(payload: BrokerConnectRequest):
    env = env_snapshot()
    api_key = payload.api_key or (os.getenv("ALPACA_API_KEY") or os.getenv("APCA_API_KEY_ID"))
    secret_key = payload.secret_key or (os.getenv("ALPACA_SECRET_KEY") or os.getenv("APCA_API_SECRET_KEY"))
    base_url = payload.base_url or env["base_url"]

    if not api_key or not secret_key:
        raise HTTPException(status_code=400, detail={"reason": "missing_broker_credentials"})

    STATE["connected"] = True
    STATE["broker_mode"] = payload.mode
    STATE["base_url"] = base_url
    log_event("broker_connected", {
        "mode": payload.mode,
        "base_url": base_url,
        "used_env": not bool(payload.api_key or payload.secret_key),
    })
    return {
        "status": "ok",
        "connected": STATE["connected"],
        "broker_mode": STATE["broker_mode"],
        "base_url": STATE["base_url"],
    }

@app.post("/live-bridge/order/submit")
def submit_order(payload: LiveOrderRequest):
    if not STATE["connected"]:
        raise HTTPException(status_code=400, detail={"reason": "broker_not_connected"})
    side = payload.side.lower()
    if side not in {"buy", "sell"}:
        raise HTTPException(status_code=400, detail={"reason": "invalid_side"})

    order_id = f"ORD-{uuid.uuid4().hex[:12]}"
    fill_id = f"FIL-{uuid.uuid4().hex[:12]}"

    order = {
        "order_id": order_id,
        "symbol": payload.symbol.upper(),
        "side": side,
        "qty": payload.qty,
        "order_type": payload.order_type,
        "time_in_force": payload.time_in_force,
        "broker": payload.broker,
        "mode": STATE["broker_mode"],
        "status": "submitted",
        "submitted_at": now(),
    }
    STATE["orders"].append(order)

    pos = STATE["positions"].get(order["symbol"], {"qty": 0.0})
    new_qty = pos["qty"] + payload.qty if side == "buy" else pos["qty"] - payload.qty
    STATE["positions"][order["symbol"]] = {"qty": round(new_qty, 6)}

    fill = {
        "fill_id": fill_id,
        "order_id": order_id,
        "symbol": order["symbol"],
        "side": side,
        "qty": payload.qty,
        "status": "filled_simulated_bridge",
        "filled_at": now(),
        "mode": STATE["broker_mode"],
    }
    STATE["fills"].append(fill)
    log_event("live_bridge_order_submitted", {
        "order_id": order_id,
        "symbol": order["symbol"],
        "side": side,
        "qty": payload.qty,
        "mode": STATE["broker_mode"],
    })
    return {"status": "ok", "order": order, "fill": fill, "position": STATE["positions"][order["symbol"]]}

@app.get("/live-bridge/orders")
def orders():
    return {"orders": STATE["orders"][::-1]}

@app.get("/live-bridge/fills")
def fills():
    return {"fills": STATE["fills"][::-1]}

@app.get("/live-bridge/positions")
def positions():
    return {"positions": STATE["positions"]}

@app.get("/live-bridge/audit")
def audit(limit: int = 25):
    return {"events": STATE["audit"][-limit:][::-1]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("real_broker_execution_bridge:app", host="127.0.0.1", port=8010, reload=False)
