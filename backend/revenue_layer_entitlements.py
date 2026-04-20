from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import sqlite3, os, uuid
from datetime import datetime

app = FastAPI(title="QNT30416 Revenue Layer + SaaS Entitlements", version="1.0.0")

BASE_DIR = os.path.dirname(__file__)
STATE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "state"))
DB_PATH = os.path.join(STATE_DIR, "quantora.db")

PLAN_FEATURES = {
    "free": ["dashboard_basic", "paper_trading", "account_view"],
    "pro": ["dashboard_basic", "paper_trading", "account_view", "performance_engine", "strategy_competition", "runtime_orchestrator"],
    "institutional": [
        "dashboard_basic", "paper_trading", "account_view", "performance_engine",
        "strategy_competition", "runtime_orchestrator", "live_bridge",
        "state_fabric", "api_gateway", "governance", "treasury", "multi_asset_routing"
    ],
}

def now():
    return datetime.utcnow().isoformat() + "Z"

def conn():
    os.makedirs(STATE_DIR, exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    c = conn()
    cur = c.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS user_plans (user_id TEXT PRIMARY KEY, plan TEXT, status TEXT, started_at TEXT, expires_at TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS entitlement_audit (id TEXT PRIMARY KEY, kind TEXT, payload TEXT, created_at TEXT)")
    c.commit()
    c.close()

init_db()

def audit(kind: str, payload: str):
    c = conn()
    cur = c.cursor()
    cur.execute("INSERT INTO entitlement_audit VALUES (?,?,?,?)", (str(uuid.uuid4()), kind, payload, now()))
    c.commit()
    c.close()

class PlanAssign(BaseModel):
    user_id: str
    plan: str
    status: str = "active"
    expires_at: Optional[str] = None

class FeatureCheck(BaseModel):
    user_id: str
    feature: str

@app.get("/entitlements/status")
def status():
    c = conn()
    cur = c.cursor()
    cur.execute("SELECT COUNT(*) FROM user_plans")
    count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM entitlement_audit")
    audit_count = cur.fetchone()[0]
    c.close()
    return {
        "mission": "QNT30416",
        "plans_supported": list(PLAN_FEATURES.keys()),
        "assigned_users": count,
        "audit_events": audit_count,
    }

@app.get("/entitlements/plans")
def plans():
    return {"plans": PLAN_FEATURES}

@app.post("/entitlements/assign")
def assign_plan(payload: PlanAssign):
    if payload.plan not in PLAN_FEATURES:
        raise HTTPException(status_code=400, detail={"reason": "unknown_plan"})
    c = conn()
    cur = c.cursor()
    cur.execute(
        "INSERT INTO user_plans(user_id, plan, status, started_at, expires_at) VALUES (?,?,?,?,?) "
        "ON CONFLICT(user_id) DO UPDATE SET plan=excluded.plan, status=excluded.status, started_at=excluded.started_at, expires_at=excluded.expires_at",
        (payload.user_id, payload.plan, payload.status, now(), payload.expires_at)
    )
    c.commit()
    c.close()
    audit("plan_assigned", f"user_id={payload.user_id};plan={payload.plan};status={payload.status}")
    return {"status": "ok", "user_id": payload.user_id, "plan": payload.plan, "features": PLAN_FEATURES[payload.plan]}

@app.get("/entitlements/user/{user_id}")
def user_plan(user_id: str):
    c = conn()
    cur = c.cursor()
    cur.execute("SELECT plan, status, started_at, expires_at FROM user_plans WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    c.close()
    if not row:
        return {"status": "not_found", "user_id": user_id, "plan": "free", "features": PLAN_FEATURES["free"]}
    plan, status, started_at, expires_at = row
    return {
        "status": "ok",
        "user_id": user_id,
        "plan": plan,
        "plan_status": status,
        "started_at": started_at,
        "expires_at": expires_at,
        "features": PLAN_FEATURES.get(plan, PLAN_FEATURES["free"])
    }

@app.post("/entitlements/check")
def check_feature(payload: FeatureCheck):
    info = user_plan(payload.user_id)
    features = info.get("features", PLAN_FEATURES["free"])
    allowed = payload.feature in features
    audit("feature_checked", f"user_id={payload.user_id};feature={payload.feature};allowed={allowed}")
    return {
        "status": "ok",
        "user_id": payload.user_id,
        "feature": payload.feature,
        "allowed": allowed,
        "plan": info.get("plan", "free")
    }

@app.get("/entitlements/audit")
def entitlement_audit(limit: int = 50):
    c = conn()
    cur = c.cursor()
    cur.execute("SELECT id, kind, payload, created_at FROM entitlement_audit ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    c.close()
    return {"events": [{"id": r[0], "kind": r[1], "payload": r[2], "created_at": r[3]} for r in rows]}
