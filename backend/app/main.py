
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
import json, uuid

APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
PROJECT_DIR = BACKEND_DIR.parent
ARTIFACTS_DIR = BACKEND_DIR / "artifacts"
FRONTEND_DIR = PROJECT_DIR / "frontend"

app = FastAPI(title="Quantora QNT30302", version="30302")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

def load_json(filename: str, fallback):
    path = ARTIFACTS_DIR / filename
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return fallback

def save_json(filename: str, data):
    (ARTIFACTS_DIR / filename).write_text(json.dumps(data, indent=2), encoding="utf-8")

class RegisterRequest(BaseModel):
    email: str
    password: str
    display_name: str

class LoginRequest(BaseModel):
    email: str
    password: str

def build_passport(operator_id: str):
    return {
        "operator_id": operator_id,
        "passport_status": "ACTIVE",
        "deployment_stage": "STAGE_2_MICRO_LIVE",
        "score_last_updated": "2026-03-20T23:20:00Z",
        "discipline_score": 84,
        "risk_score": 79,
        "consistency_score": 81,
        "trust_score": 82,
        "violation_count": 0,
        "audit_status": "VALID"
    }

def build_score():
    return {
        "trust_score": 82,
        "discipline_score": 84,
        "risk_score": 79,
        "consistency_score": 81,
        "performance_score": 80,
        "audit_integrity_score": 100
    }

def build_violations(operator_id: str):
    return {
        "operator_id": operator_id,
        "violation_count": 0,
        "critical_violation_count": 0,
        "violations": []
    }

def build_audit():
    return {
        "status": "VALID",
        "checked_files": 5,
        "failed_files": [],
        "details": {
            "passport.json": "OK",
            "passport_score.json": "OK",
            "violation_registry.json": "OK",
            "audit_report.json": "OK",
            "capital_decision.json": "OK"
        },
        "timestamp": "2026-03-20T23:20:00Z"
    }

def compute_capital_decision(passport, score, violations):
    trust_score = score.get("trust_score", passport.get("trust_score", 0))
    risk_score = passport.get("risk_score", score.get("risk_score", 50))
    violation_count = violations.get("violation_count", passport.get("violation_count", 0))
    critical_count = violations.get("critical_violation_count", 0)
    approved = True
    reasons = []
    if trust_score < 70:
        approved = False
        reasons.append("Trust score below threshold")
    else:
        reasons.append("Trust score acceptable")
    if critical_count > 0:
        approved = False
        reasons.append("Critical violations present")
    else:
        reasons.append("No critical violations")
    if risk_score < 60:
        approved = False
        reasons.append("Risk score too low")
    else:
        reasons.append("Risk score acceptable")
    confidence = round(max(0.0, min(0.99, (trust_score / 100.0) - (violation_count * 0.03))), 2)
    base_capital = max(0, int(trust_score * 250))
    risk_adjustment = max(0.4, min(1.0, risk_score / 100.0))
    violation_penalty = max(0.0, 1.0 - (violation_count * 0.15))
    capital_allocated = int(base_capital * risk_adjustment * violation_penalty) if approved else 0
    return {
        "approved": approved,
        "capital_allocated": capital_allocated,
        "confidence": confidence,
        "reason": " / ".join(reasons),
        "inputs": {
            "trust_score": trust_score,
            "risk_score": risk_score,
            "violation_count": violation_count,
            "critical_violation_count": critical_count
        }
    }

def build_allocator_profile(operator_id: str, display_name: str, capital_decision: dict):
    return {
        "allocator_id": "allocator_demo_001",
        "operator_id": operator_id,
        "operator_name": display_name,
        "trust_score": capital_decision["inputs"]["trust_score"],
        "risk_tier": "TIER_2_MODERATE",
        "deployment_stage": "STAGE_2_MICRO_LIVE",
        "passport_status": "ACTIVE",
        "capital_decision": capital_decision,
        "available_reports": ["allocator_report.json"]
    }

def build_allocator_report(operator_id: str, capital_decision: dict):
    return {
        "report_id": "report_demo_001",
        "operator_id": operator_id,
        "generated_at": "2026-03-20T23:20:00Z",
        "summary": {
            "trust_score": capital_decision["inputs"]["trust_score"],
            "audit_status": "VALID",
            "violation_count": capital_decision["inputs"]["violation_count"],
            "deployment_stage": "STAGE_2_MICRO_LIVE"
        },
        "capital": {
            "approved": capital_decision["approved"],
            "requested": 25000,
            "allocated": capital_decision["capital_allocated"],
            "confidence": capital_decision["confidence"],
            "risk_tier": "TIER_2_MODERATE",
            "reason": capital_decision["reason"]
        }
    }

def ensure_user_state(user):
    operator_id = user["operator_id"]
    passport = build_passport(operator_id)
    score = build_score()
    violations = build_violations(operator_id)
    capital = compute_capital_decision(passport, score, violations)
    save_json("passport.json", passport)
    save_json("passport_score.json", score)
    save_json("violation_registry.json", violations)
    save_json("audit_report.json", build_audit())
    save_json("capital_decision.json", capital)
    save_json("allocator_profile.json", build_allocator_profile(operator_id, user["display_name"], capital))
    save_json("allocator_report.json", build_allocator_report(operator_id, capital))

def get_session():
    return load_json("session.json", {"logged_in": False, "display_name": None, "operator_id": None, "email": None})

def require_auth():
    session = get_session()
    if not session.get("logged_in"):
        raise HTTPException(status_code=401, detail="Authentication required")
    return session

@app.get("/health")
def health():
    return {"status": "ok", "layer": "QNT30302"}

@app.post("/auth/register")
def auth_register(payload: RegisterRequest):
    users = load_json("users.json", {"users": []})
    if any(u["email"].lower() == payload.email.lower() for u in users["users"]):
        raise HTTPException(status_code=400, detail="Email already registered")
    operator_id = f"operator_{uuid.uuid4().hex[:8].upper()}"
    user = {"email": payload.email, "password": payload.password, "display_name": payload.display_name, "operator_id": operator_id}
    users["users"].append(user)
    save_json("users.json", users)
    save_json("session.json", {"email": payload.email, "operator_id": operator_id, "display_name": payload.display_name, "logged_in": True})
    ensure_user_state(user)
    return {"status": "registered", "operator_id": operator_id, "display_name": payload.display_name}

@app.post("/auth/login")
def auth_login(payload: LoginRequest):
    users = load_json("users.json", {"users": []})
    user = next((u for u in users["users"] if u["email"].lower() == payload.email.lower() and u["password"] == payload.password), None)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    save_json("session.json", {"email": user["email"], "operator_id": user["operator_id"], "display_name": user["display_name"], "logged_in": True})
    ensure_user_state(user)
    return {"status": "logged_in", "operator_id": user["operator_id"], "display_name": user["display_name"]}

@app.post("/auth/logout")
def auth_logout():
    save_json("session.json", {"logged_in": False, "display_name": None, "operator_id": None, "email": None})
    return {"status": "logged_out"}

@app.get("/auth/me")
def auth_me():
    return get_session()

@app.get("/passport/current")
def passport_current(session = Depends(require_auth)):
    return load_json("passport.json", {})

@app.get("/passport/score")
def passport_score(session = Depends(require_auth)):
    return load_json("passport_score.json", {})

@app.get("/passport/violations")
def passport_violations(session = Depends(require_auth)):
    return load_json("violation_registry.json", {})

@app.get("/audit/current")
def audit_current(session = Depends(require_auth)):
    return load_json("audit_report.json", {})

@app.get("/system/trust-summary")
def trust_summary(session = Depends(require_auth)):
    passport = load_json("passport.json", {})
    score = load_json("passport_score.json", {})
    audit = load_json("audit_report.json", {})
    violations = load_json("violation_registry.json", {})
    return {
        "status": "ok",
        "layer": "QNT30302",
        "operator_id": passport.get("operator_id", session.get("operator_id")),
        "trust_score": score.get("trust_score", passport.get("trust_score", 0)),
        "audit_status": audit.get("status", "UNKNOWN"),
        "violation_count": violations.get("violation_count", 0),
        "deployment_stage": passport.get("deployment_stage", "STAGE_0_BLOCKED"),
        "passport_status": passport.get("passport_status", "UNKNOWN"),
        "display_name": session.get("display_name")
    }

@app.get("/capital/decision")
def capital_decision(session = Depends(require_auth)):
    return load_json("capital_decision.json", {})

@app.get("/allocator/profile")
def allocator_profile(session = Depends(require_auth)):
    return load_json("allocator_profile.json", {})

@app.get("/allocator/report")
def allocator_report(session = Depends(require_auth)):
    return load_json("allocator_report.json", {})

@app.post("/allocator/request-access")
def allocator_request_access(session = Depends(require_auth)):
    return {
        "status": "accepted",
        "layer": "QNT30302",
        "request_id": "alloc_req_demo_001",
        "message": "Allocator access request recorded.",
        "operator_id": session.get("operator_id")
    }

@app.get("/")
def root():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return JSONResponse({"status": "ok", "message": "Quantora backend live", "docs": "/docs", "health": "/health"})

@app.get("/{page_name}")
def static_pages(page_name: str):
    page = FRONTEND_DIR / page_name
    if page.suffix == "" and not page_name.endswith(".html"):
        page = FRONTEND_DIR / f"{page_name}.html"
    if page.exists() and page.is_file():
        return FileResponse(page)
    return JSONResponse({"error": "not found", "page": page_name}, status_code=404)
