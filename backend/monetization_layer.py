from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

app = FastAPI(title="QNT30386 Monetization Layer", version="1.0.0")

STATE = {
    "plans": {
        "starter": {
            "monthly_price": 99.0,
            "setup_fee": 0.0,
            "performance_fee_bps": 0,
            "features": ["dashboard", "signals", "paper access"]
        },
        "pro": {
            "monthly_price": 299.0,
            "setup_fee": 49.0,
            "performance_fee_bps": 500,
            "features": ["dashboard", "signals", "automation insights", "paper access"]
        },
        "institutional": {
            "monthly_price": 2500.0,
            "setup_fee": 1000.0,
            "performance_fee_bps": 1500,
            "features": ["dashboard", "execution analytics", "portfolio controls", "priority support"]
        }
    },
    "customers": {},
    "subscriptions": {},
    "invoices": {},
    "performance_fee_accruals": {},
    "audit": [],
}

class CustomerProfile(BaseModel):
    customer_id: str
    full_name: str
    email: str
    company: Optional[str] = None
    plan: str = "starter"
    status: str = "active"
    metadata: Optional[Dict[str, Any]] = None

class SubscriptionRequest(BaseModel):
    customer_id: str
    plan: str
    billing_cycle: str = "monthly"
    autopay: bool = True

class InvoiceRequest(BaseModel):
    customer_id: str
    amount: float = Field(..., gt=0)
    currency: str = "USD"
    kind: str = "subscription"
    description: Optional[str] = None

class PerformanceFeeRequest(BaseModel):
    customer_id: str
    gross_profit: float
    fee_bps: Optional[int] = None
    high_water_mark: Optional[float] = 0.0

class ApiAccessRequest(BaseModel):
    customer_id: str
    tier: str = "standard"
    scopes: List[str] = []

def log_event(kind: str, payload: Dict[str, Any]):
    STATE["audit"].append({
        "id": str(uuid.uuid4()),
        "kind": kind,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "payload": payload
    })
    STATE["audit"] = STATE["audit"][-500:]

def mk_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"

@app.get("/monetization/status")
def status():
    return {
        "mission": "QNT30386",
        "plan_count": len(STATE["plans"]),
        "customer_count": len(STATE["customers"]),
        "subscription_count": len(STATE["subscriptions"]),
        "invoice_count": len(STATE["invoices"]),
        "accrual_count": len(STATE["performance_fee_accruals"]),
        "audit_events": len(STATE["audit"]),
    }

@app.get("/monetization/plans")
def plans():
    return {"plans": STATE["plans"]}

@app.post("/monetization/customer/register")
def register_customer(profile: CustomerProfile):
    if profile.plan not in STATE["plans"]:
        return {"status": "error", "message": "unknown plan"}
    record = profile.model_dump()
    record["registered_at"] = datetime.utcnow().isoformat() + "Z"
    STATE["customers"][profile.customer_id] = record
    log_event("customer_registered", {"customer_id": profile.customer_id, "plan": profile.plan})
    return {"status": "ok", "customer": record}

@app.get("/monetization/customers")
def customers():
    return {"customers": list(STATE["customers"].values())}

@app.post("/monetization/subscription/create")
def create_subscription(req: SubscriptionRequest):
    if req.customer_id not in STATE["customers"]:
        return {"status": "error", "message": "customer not found"}
    if req.plan not in STATE["plans"]:
        return {"status": "error", "message": "unknown plan"}
    sub_id = mk_id("SUB")
    plan = STATE["plans"][req.plan]
    record = {
        "subscription_id": sub_id,
        "customer_id": req.customer_id,
        "plan": req.plan,
        "billing_cycle": req.billing_cycle,
        "autopay": req.autopay,
        "monthly_price": plan["monthly_price"],
        "status": "active",
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    STATE["subscriptions"][sub_id] = record
    log_event("subscription_created", record)
    return {"status": "ok", "subscription": record}

@app.get("/monetization/subscriptions")
def subscriptions():
    return {"subscriptions": list(STATE["subscriptions"].values())}

@app.post("/monetization/invoice/create")
def create_invoice(req: InvoiceRequest):
    if req.customer_id not in STATE["customers"]:
        return {"status": "error", "message": "customer not found"}
    inv_id = mk_id("INV")
    record = {
        "invoice_id": inv_id,
        "customer_id": req.customer_id,
        "amount": round(req.amount, 2),
        "currency": req.currency,
        "kind": req.kind,
        "description": req.description or req.kind,
        "status": "issued",
        "issued_at": datetime.utcnow().isoformat() + "Z"
    }
    STATE["invoices"][inv_id] = record
    log_event("invoice_created", record)
    return {"status": "ok", "invoice": record}

@app.get("/monetization/invoices")
def invoices():
    return {"invoices": list(STATE["invoices"].values())}

@app.post("/monetization/performance-fee/accrue")
def accrue_performance_fee(req: PerformanceFeeRequest):
    if req.customer_id not in STATE["customers"]:
        return {"status": "error", "message": "customer not found"}
    plan = STATE["customers"][req.customer_id]["plan"]
    fee_bps = req.fee_bps if req.fee_bps is not None else STATE["plans"][plan]["performance_fee_bps"]
    fee_amount = round(max(req.gross_profit, 0.0) * (fee_bps / 10000.0), 2)
    accrual_id = mk_id("PFA")
    record = {
        "accrual_id": accrual_id,
        "customer_id": req.customer_id,
        "gross_profit": req.gross_profit,
        "fee_bps": fee_bps,
        "fee_amount": fee_amount,
        "high_water_mark": req.high_water_mark,
        "status": "accrued",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    STATE["performance_fee_accruals"][accrual_id] = record
    log_event("performance_fee_accrued", record)
    return {"status": "ok", "accrual": record}

@app.get("/monetization/performance-fees")
def performance_fees():
    return {"accruals": list(STATE["performance_fee_accruals"].values())}

@app.post("/monetization/api-access/provision")
def provision_api_access(req: ApiAccessRequest):
    if req.customer_id not in STATE["customers"]:
        return {"status": "error", "message": "customer not found"}
    token = mk_id("API")
    record = {
        "access_id": token,
        "customer_id": req.customer_id,
        "tier": req.tier,
        "scopes": req.scopes,
        "status": "active",
        "provisioned_at": datetime.utcnow().isoformat() + "Z"
    }
    log_event("api_access_provisioned", record)
    return {"status": "ok", "api_access": record}

@app.get("/monetization/dashboard/{customer_id}")
def dashboard(customer_id: str):
    customer = STATE["customers"].get(customer_id)
    if not customer:
        return {"status": "not_found"}
    subs = [x for x in STATE["subscriptions"].values() if x["customer_id"] == customer_id]
    invs = [x for x in STATE["invoices"].values() if x["customer_id"] == customer_id]
    fees = [x for x in STATE["performance_fee_accruals"].values() if x["customer_id"] == customer_id]
    return {
        "customer": customer,
        "subscriptions": subs,
        "invoices": invs,
        "performance_fees": fees,
        "summary": {
            "plan": customer["plan"],
            "active_subscriptions": len([x for x in subs if x["status"] == "active"]),
            "outstanding_invoices": len([x for x in invs if x["status"] == "issued"]),
            "total_accrued_fees": round(sum(x["fee_amount"] for x in fees), 2)
        }
    }

@app.get("/monetization/audit")
def audit(limit: int = 25):
    return {"events": STATE["audit"][-limit:][::-1]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("monetization_layer:app", host="127.0.0.1", port=8010, reload=False)
