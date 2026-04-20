from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

app = FastAPI(title="QNT30385 User Product Layer", version="1.0.0")

STATE = {
    "users": {},
    "portfolios": {},
    "service_plans": {
        "starter": {"monthly_price": 99, "risk_presets": ["conservative"], "features": ["dashboard", "signals", "paper access"]},
        "pro": {"monthly_price": 299, "risk_presets": ["conservative", "balanced", "aggressive"], "features": ["dashboard", "signals", "paper access", "automation insights"]},
        "institutional": {"monthly_price": 2500, "risk_presets": ["custom"], "features": ["dashboard", "execution analytics", "portfolio controls", "priority support"]},
    },
    "audit": [],
}

class UserProfile(BaseModel):
    user_id: str
    full_name: str
    email: str
    plan: str = "starter"
    risk_preset: str = "conservative"
    status: str = "active"
    metadata: Optional[Dict[str, Any]] = None

class PortfolioIntent(BaseModel):
    user_id: str
    target_capital: float = Field(..., gt=0)
    risk_preset: str
    market_access: List[str] = []
    automation_enabled: bool = False

class ServiceRequest(BaseModel):
    user_id: str
    action: str
    payload: Optional[Dict[str, Any]] = None

def log_event(kind: str, payload: Dict[str, Any]):
    STATE["audit"].append({
        "id": str(uuid.uuid4()),
        "kind": kind,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "payload": payload,
    })
    STATE["audit"] = STATE["audit"][-500:]

@app.get("/product/status")
def status():
    return {
        "mission": "QNT30385",
        "user_count": len(STATE["users"]),
        "portfolio_count": len(STATE["portfolios"]),
        "service_plans": STATE["service_plans"],
        "audit_events": len(STATE["audit"]),
    }

@app.get("/product/plans")
def plans():
    return {"plans": STATE["service_plans"]}

@app.post("/product/user/register")
def register_user(profile: UserProfile):
    if profile.plan not in STATE["service_plans"]:
        return {"status": "error", "message": "unknown plan"}
    STATE["users"][profile.user_id] = profile.model_dump()
    log_event("user_registered", {"user_id": profile.user_id, "plan": profile.plan})
    return {"status": "ok", "user": STATE["users"][profile.user_id]}

@app.get("/product/users")
def list_users():
    return {"users": list(STATE["users"].values())}

@app.get("/product/user/{user_id}")
def get_user(user_id: str):
    return STATE["users"].get(user_id, {"status": "not_found"})

@app.post("/product/portfolio/configure")
def configure_portfolio(intent: PortfolioIntent):
    if intent.user_id not in STATE["users"]:
        return {"status": "error", "message": "user not found"}
    record = intent.model_dump()
    record["configured_at"] = datetime.utcnow().isoformat() + "Z"
    record["service_state"] = "ready"
    STATE["portfolios"][intent.user_id] = record
    log_event("portfolio_configured", {"user_id": intent.user_id, "risk_preset": intent.risk_preset})
    return {"status": "ok", "portfolio": record}

@app.get("/product/portfolio/{user_id}")
def get_portfolio(user_id: str):
    return STATE["portfolios"].get(user_id, {"status": "not_found"})

@app.post("/product/service/request")
def service_request(req: ServiceRequest):
    if req.user_id not in STATE["users"]:
        return {"status": "error", "message": "user not found"}
    response = {
        "request_id": f"REQ-{uuid.uuid4().hex[:10]}",
        "user_id": req.user_id,
        "action": req.action,
        "payload": req.payload or {},
        "status": "accepted",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    log_event("service_request", response)
    return response

@app.get("/product/dashboard/{user_id}")
def dashboard(user_id: str):
    user = STATE["users"].get(user_id)
    portfolio = STATE["portfolios"].get(user_id, {})
    if not user:
        return {"status": "not_found"}
    return {
        "user": user,
        "portfolio": portfolio,
        "summary": {
            "service_tier": user["plan"],
            "risk_preset": user["risk_preset"],
            "automation_enabled": portfolio.get("automation_enabled", False),
            "target_capital": portfolio.get("target_capital", 0),
            "markets": portfolio.get("market_access", []),
        }
    }

@app.get("/product/audit")
def audit(limit: int = 25):
    return {"events": STATE["audit"][-limit:][::-1]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("user_product_layer:app", host="127.0.0.1", port=8010, reload=False)
