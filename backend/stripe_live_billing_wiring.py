from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

app = FastAPI(title="QNT30393 Stripe Live Billing Wiring", version="1.0.0")
STATE = {"mode":"test","stripe_env_ready":False,"publishable_key_present":False,"secret_key_present":False,"webhook_secret_present":False,"customers":{},"checkout_sessions":{},"subscriptions":{},"payments":{},"webhooks":[],"audit":[]}
PLANS={"starter":{"price_usd":99.0,"interval":"month"},"pro":{"price_usd":299.0,"interval":"month"},"institutional":{"price_usd":2500.0,"interval":"month"}}

class StripeEnvUpdate(BaseModel):
    mode:str="test"; publishable_key_present:bool=False; secret_key_present:bool=False; webhook_secret_present:bool=False
class CustomerCreate(BaseModel):
    customer_id:str; email:str; full_name:str; plan:str="starter"; metadata:Optional[Dict[str, Any]]=None
class CheckoutSessionCreate(BaseModel):
    customer_id:str; plan:str; success_url:str="https://example.com/success"; cancel_url:str="https://example.com/cancel"
class SubscriptionActivate(BaseModel):
    customer_id:str; plan:str; stripe_customer_ref:Optional[str]=None; stripe_subscription_ref:Optional[str]=None
class PaymentIntentCreate(BaseModel):
    customer_id:str; amount:float=Field(..., gt=0); currency:str="USD"; description:Optional[str]=None
class WebhookEvent(BaseModel):
    event_type:str; customer_id:Optional[str]=None; stripe_ref:Optional[str]=None; payload:Optional[Dict[str, Any]]=None

def now(): return datetime.utcnow().isoformat()+"Z"
def log_event(kind,payload):
    STATE["audit"].append({"id":str(uuid.uuid4()),"kind":kind,"timestamp":now(),"payload":payload}); STATE["audit"]=STATE["audit"][-500:]
def refresh_env_ready():
    STATE["stripe_env_ready"] = bool(STATE["publishable_key_present"] and STATE["secret_key_present"] and STATE["webhook_secret_present"])

@app.get("/stripe-billing/status")
def status():
    refresh_env_ready()
    return {"mission":"QNT30393","mode":STATE["mode"],"stripe_env_ready":STATE["stripe_env_ready"],"publishable_key_present":STATE["publishable_key_present"],"secret_key_present":STATE["secret_key_present"],"webhook_secret_present":STATE["webhook_secret_present"],"customer_count":len(STATE["customers"]),"checkout_session_count":len(STATE["checkout_sessions"]),"subscription_count":len(STATE["subscriptions"]),"payment_count":len(STATE["payments"]),"webhook_count":len(STATE["webhooks"]),"audit_events":len(STATE["audit"])}
@app.get("/stripe-billing/plans")
def plans(): return {"plans": PLANS}
@app.post("/stripe-billing/env/update")
def update_env(payload: StripeEnvUpdate):
    STATE["mode"]=payload.mode; STATE["publishable_key_present"]=payload.publishable_key_present; STATE["secret_key_present"]=payload.secret_key_present; STATE["webhook_secret_present"]=payload.webhook_secret_present; refresh_env_ready(); log_event("stripe_env_updated",{"mode":STATE["mode"],"stripe_env_ready":STATE["stripe_env_ready"]}); return {"status":"ok","stripe_env_ready":STATE["stripe_env_ready"],"mode":STATE["mode"]}
@app.post("/stripe-billing/customer/create")
def create_customer(payload: CustomerCreate):
    if payload.plan not in PLANS: return {"status":"error","message":"unknown plan"}
    record=payload.model_dump(); record["created_at"]=now(); record["stripe_customer_ref"]=record.get("customer_id"); STATE["customers"][payload.customer_id]=record; log_event("stripe_customer_created",{"customer_id":payload.customer_id,"plan":payload.plan}); return {"status":"ok","customer":record}
@app.get("/stripe-billing/customers")
def list_customers(): return {"customers": list(STATE["customers"].values())}
@app.post("/stripe-billing/checkout-session/create")
def create_checkout_session(payload: CheckoutSessionCreate):
    if payload.customer_id not in STATE["customers"]: return {"status":"error","message":"customer not found"}
    if payload.plan not in PLANS: return {"status":"error","message":"unknown plan"}
    session={"checkout_session_id":f"cs_{uuid.uuid4().hex[:18]}","customer_id":payload.customer_id,"plan":payload.plan,"price_usd":PLANS[payload.plan]["price_usd"],"interval":PLANS[payload.plan]["interval"],"success_url":payload.success_url,"cancel_url":payload.cancel_url,"status":"open","mode":STATE["mode"],"created_at":now(),"checkout_url":f"https://checkout.stripe.mock/{payload.customer_id}/{payload.plan}"}
    STATE["checkout_sessions"][session["checkout_session_id"]]=session; log_event("checkout_session_created",{"checkout_session_id":session["checkout_session_id"],"customer_id":payload.customer_id,"plan":payload.plan}); return {"status":"ok","checkout_session":session}
@app.get("/stripe-billing/checkout-sessions")
def list_checkout_sessions(): return {"checkout_sessions": list(STATE["checkout_sessions"].values())}
@app.post("/stripe-billing/subscription/activate")
def activate_subscription(payload: SubscriptionActivate):
    if payload.customer_id not in STATE["customers"]: return {"status":"error","message":"customer not found"}
    if payload.plan not in PLANS: return {"status":"error","message":"unknown plan"}
    sub={"subscription_id":f"sub_{uuid.uuid4().hex[:18]}","customer_id":payload.customer_id,"plan":payload.plan,"price_usd":PLANS[payload.plan]["price_usd"],"interval":PLANS[payload.plan]["interval"],"status":"active","stripe_customer_ref":payload.stripe_customer_ref or STATE["customers"][payload.customer_id]["stripe_customer_ref"],"stripe_subscription_ref":payload.stripe_subscription_ref or f"stripe_sub_{uuid.uuid4().hex[:12]}","activated_at":now()}
    STATE["subscriptions"][sub["subscription_id"]]=sub; log_event("subscription_activated",{"subscription_id":sub["subscription_id"],"customer_id":payload.customer_id}); return {"status":"ok","subscription":sub}
@app.get("/stripe-billing/subscriptions")
def list_subscriptions(): return {"subscriptions": list(STATE["subscriptions"].values())}
@app.post("/stripe-billing/payment-intent/create")
def create_payment_intent(payload: PaymentIntentCreate):
    if payload.customer_id not in STATE["customers"]: return {"status":"error","message":"customer not found"}
    payment={"payment_intent_id":f"pi_{uuid.uuid4().hex[:18]}","customer_id":payload.customer_id,"amount":round(payload.amount,2),"currency":payload.currency,"description":payload.description or "Quantora billing payment","status":"requires_confirmation" if STATE["mode"]=="live" else "succeeded_test","created_at":now()}
    STATE["payments"][payment["payment_intent_id"]]=payment; log_event("payment_intent_created",{"payment_intent_id":payment["payment_intent_id"],"customer_id":payload.customer_id}); return {"status":"ok","payment_intent":payment}
@app.get("/stripe-billing/payments")
def list_payments(): return {"payments": list(STATE["payments"].values())}
@app.post("/stripe-billing/webhook/ingest")
def ingest_webhook(payload: WebhookEvent):
    event={"webhook_event_id":f"wh_{uuid.uuid4().hex[:18]}","event_type":payload.event_type,"customer_id":payload.customer_id,"stripe_ref":payload.stripe_ref,"payload":payload.payload or {},"received_at":now()}
    STATE["webhooks"].append(event); STATE["webhooks"]=STATE["webhooks"][-300:]; log_event("stripe_webhook_ingested",{"event_type":payload.event_type,"customer_id":payload.customer_id})
    if payload.event_type=="checkout.session.completed" and payload.customer_id and payload.customer_id in STATE["customers"]:
        plan=STATE["customers"][payload.customer_id]["plan"]; activate_subscription(SubscriptionActivate(customer_id=payload.customer_id, plan=plan))
    return {"status":"ok","webhook_event":event}
@app.get("/stripe-billing/webhooks")
def list_webhooks(): return {"webhooks": STATE["webhooks"][::-1]}
@app.get("/stripe-billing/dashboard/{customer_id}")
def dashboard(customer_id:str):
    customer=STATE["customers"].get(customer_id)
    if not customer: return {"status":"not_found"}
    subs=[x for x in STATE["subscriptions"].values() if x["customer_id"]==customer_id]
    invs=[x for x in STATE["payments"].values() if x["customer_id"]==customer_id]
    hooks=[x for x in STATE["webhooks"] if x.get("customer_id")==customer_id]
    return {"customer":customer,"subscriptions":subs,"payments":invs,"webhooks":hooks,"summary":{"stripe_env_ready":STATE["stripe_env_ready"],"mode":STATE["mode"],"active_subscriptions":len([x for x in subs if x["status"]=="active"]),"successful_payments":len([x for x in invs if "succeeded" in x["status"]])}}
@app.get("/stripe-billing/audit")
def audit(limit:int=25): return {"events": STATE["audit"][-limit:][::-1]}
