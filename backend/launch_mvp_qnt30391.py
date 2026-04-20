
from fastapi import FastAPI
from pydantic import BaseModel
import uuid

app = FastAPI(title="QNT30391 Live Trading + Stripe + Deploy (Simulated)")

class Trade(BaseModel):
    symbol: str
    side: str
    qty: float

class Payment(BaseModel):
    user_id: str
    amount: float

STATE = {"trades": [], "payments": []}

@app.post("/live-trade")
def trade(t: Trade):
    rec = {"id": str(uuid.uuid4()), **t.dict(), "status": "executed_simulated"}
    STATE["trades"].append(rec)
    return rec

@app.post("/stripe/charge")
def charge(p: Payment):
    rec = {"id": str(uuid.uuid4()), **p.dict(), "status": "paid_simulated"}
    STATE["payments"].append(rec)
    return rec

@app.get("/status")
def status():
    return STATE
