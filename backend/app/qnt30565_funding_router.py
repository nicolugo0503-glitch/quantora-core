from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["funding"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
FUNDING_DIR = ARTIFACTS_DIR / "user_funding_profiles"
PAYMENT_DIR = ARTIFACTS_DIR / "user_payment_intents"

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _safe_email(email: str) -> str:
    return hashlib.sha256((email or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _profile_path(email: str) -> Path:
    FUNDING_DIR.mkdir(parents=True, exist_ok=True)
    return FUNDING_DIR / f"{_safe_email(email)}.json"

def _intent_path(email: str) -> Path:
    PAYMENT_DIR.mkdir(parents=True, exist_ok=True)
    return PAYMENT_DIR / f"{_safe_email(email)}.json"

def _require_user():
    mu = _mu()
    return mu._require_session()

def _load_profile(email: str) -> dict:
    path = _profile_path(email)
    if not path.exists():
        data = {
            "email": email,
            "funding_status": "not_started",
            "default_method": None,
            "payment_methods": [],
            "kyc_status": "not_started",
            "created_at": int(time.time()),
            "updated_at": int(time.time()),
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))

def _save_profile(email: str, data: dict) -> dict:
    data["updated_at"] = int(time.time())
    _profile_path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data

def _load_intents(email: str) -> dict:
    path = _intent_path(email)
    if not path.exists():
        data = {"email": email, "payment_intents": []}
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))

def _save_intents(email: str, data: dict) -> dict:
    _intent_path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data

@router.get("/api/user-funding/profile")
def user_funding_profile():
    session = _require_user()
    email = session.get("email")
    return _load_profile(email)

@router.post("/api/user-funding/method")
def user_funding_add_method(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    profile = _load_profile(email)
    method_type = (payload.get("method_type") or "bank").strip().lower()
    if method_type not in {"bank", "card", "wire"}:
        raise HTTPException(status_code=400, detail="Unsupported funding method")
    nickname = (payload.get("nickname") or method_type.upper()).strip()
    method = {
        "method_id": f"pm_{int(time.time())}",
        "method_type": method_type,
        "nickname": nickname,
        "status": "verified_simulated",
        "added_at": int(time.time()),
    }
    profile.setdefault("payment_methods", []).append(method)
    if not profile.get("default_method"):
        profile["default_method"] = method["method_id"]
    profile["funding_status"] = "ready"
    _save_profile(email, profile)
    return {"status": "added", "method": method, "profile": profile}

@router.post("/api/user-funding/kyc/start")
def user_funding_kyc_start():
    session = _require_user()
    email = session.get("email")
    profile = _load_profile(email)
    profile["kyc_status"] = "in_review_simulated"
    _save_profile(email, profile)
    return {"status": "started", "profile": profile}

@router.post("/api/user-funding/kyc/approve")
def user_funding_kyc_approve():
    session = _require_user()
    email = session.get("email")
    profile = _load_profile(email)
    profile["kyc_status"] = "approved_simulated"
    _save_profile(email, profile)
    return {"status": "approved", "profile": profile}

@router.get("/api/user-funding/intents")
def user_funding_intents():
    session = _require_user()
    email = session.get("email")
    return _load_intents(email)

@router.post("/api/user-funding/deposit-intent")
def user_funding_deposit_intent(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    amount = round(float(payload.get("amount") or 0.0), 2)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")
    profile = _load_profile(email)
    if not profile.get("payment_methods"):
        raise HTTPException(status_code=400, detail="No payment method on file")
    intents = _load_intents(email)
    method_id = payload.get("method_id") or profile.get("default_method")
    intent = {
        "intent_id": f"pi_{int(time.time())}",
        "type": "deposit",
        "amount": amount,
        "currency": "USD",
        "method_id": method_id,
        "status": "pending_simulated",
        "created_at": int(time.time()),
    }
    intents.setdefault("payment_intents", []).insert(0, intent)
    intents["payment_intents"] = intents["payment_intents"][:100]
    _save_intents(email, intents)
    return {"status": "created", "intent": intent, "profile": profile}

@router.post("/api/user-funding/deposit-confirm")
def user_funding_deposit_confirm(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    intent_id = payload.get("intent_id")
    intents = _load_intents(email)
    intent = next((x for x in intents.get("payment_intents", []) if x.get("intent_id") == intent_id), None)
    if not intent:
        raise HTTPException(status_code=404, detail="Payment intent not found")
    if intent.get("status") == "completed":
        raise HTTPException(status_code=400, detail="Intent already completed")
    mu = _mu()
    ledger = mu._load_ledger(email)
    amount = round(float(intent.get("amount") or 0.0), 2)
    ledger["balance"] = float(ledger.get("balance", 0.0)) + amount
    ledger["available"] = float(ledger.get("available", 0.0)) + amount
    ledger.setdefault("history", []).insert(0, {
        "type": "deposit",
        "amount": amount,
        "timestamp": int(time.time()),
        "source": "funding_rail_simulated"
    })
    saved = mu._save_ledger(email, ledger)
    current, series = mu._perf_snapshot(email, saved)
    intent["status"] = "completed"
    intent["completed_at"] = int(time.time())
    _save_intents(email, intents)
    return {"status": "completed", "intent": intent, "capital": saved, "performance": current, "series_points": len(series)}

@router.get("/api/user-funding/summary")
def user_funding_summary():
    session = _require_user()
    email = session.get("email")
    profile = _load_profile(email)
    intents = _load_intents(email)
    completed = [x for x in intents.get("payment_intents", []) if x.get("status") == "completed"]
    pending = [x for x in intents.get("payment_intents", []) if x.get("status") != "completed"]
    total_completed = round(sum(float(x.get("amount") or 0.0) for x in completed), 2)
    return {
        "email": email,
        "profile": profile,
        "summary": {
            "payment_methods": len(profile.get("payment_methods", [])),
            "completed_deposits": len(completed),
            "pending_intents": len(pending),
            "total_completed_amount": total_completed,
        },
        "recent_intents": intents.get("payment_intents", [])[:20],
    }
