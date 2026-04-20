from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
import uuid

app = FastAPI(title="QNT30390 Payments Integration & Billing Orchestration")

STATE = {"customers": {}, "payment_methods": {}, "charges": {}, "subscriptions": {}, "audit": []}

class PaymentMethod(BaseModel):
    customer_id: str
    provider: str = "stripe"
    last4: str = "4242"

class ChargeRequest(BaseModel):
    customer_id: str
    amount: float
    currency: str = "USD"

class Subscription(BaseModel):
    customer_id: str
    plan: str
    price: float

def log(event, data):
    STATE["audit"].append({
        "id": str(uuid.uuid4()),
        "event": event,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data": data
    })

@app.get("/payments/status")
def status():
    return {"charges": len(STATE["charges"]), "subs": len(STATE["subscriptions"]), "payment_methods": len(STATE["payment_methods"])}

@app.post("/payments/method/add")
def add_method(pm: PaymentMethod):
    STATE["payment_methods"][pm.customer_id] = pm.model_dump()
    log("payment_method_added", pm.model_dump())
    return {"status": "ok", "payment_method": pm.model_dump()}

@app.post("/payments/charge")
def charge(req: ChargeRequest):
    cid = str(uuid.uuid4())
    record = {"id": cid, "customer": req.customer_id, "amount": req.amount, "currency": req.currency, "status": "paid_simulated"}
    STATE["charges"][cid] = record
    log("charge_created", record)
    return record

@app.post("/payments/subscription/create")
def sub_create(s: Subscription):
    sid = str(uuid.uuid4())
    record = {"id": sid, "customer": s.customer_id, "plan": s.plan, "price": s.price, "status": "active"}
    STATE["subscriptions"][sid] = record
    log("subscription_created", record)
    return record
