from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
import json, time, hashlib, datetime as dt

router = APIRouter(tags=["dealing-day-nav-cutoff"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
DEAL_DIR = ARTIFACTS_DIR / "investor_dealing_day_control"

def _main():
    from backend.app import main as app_main
    return app_main

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _activity():
    from backend.app import qnt30595_capital_activity_router as activity
    return activity

def _safe(value: str) -> str:
    return hashlib.sha256((value or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _path(email: str) -> Path:
    DEAL_DIR.mkdir(parents=True, exist_ok=True)
    return DEAL_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _require_admin():
    return _main().require_admin()

def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {
            "email": email,
            "cutoff_policy": {
                "cutoff_hour_utc": 17,
                "dealing_frequency": "daily",
                "same_day_processing": True,
            },
            "dealing_days": [],
            "created_at": int(time.time()),
            "updated_at": int(time.time()),
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))

def _save(email: str, data: dict) -> dict:
    data["updated_at"] = int(time.time())
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data

def _find_day(data: dict, day_id: str):
    return next((d for d in data.get("dealing_days", []) if d.get("day_id") == day_id), None)

def _default_date_string():
    return dt.datetime.utcnow().strftime("%Y-%m-%d")

def _pending_requests(email: str):
    data = _activity()._load(email)
    return [r for r in data.get("requests", []) if r.get("status") in {"pending_review", "approved"}]

def _build_day(email: str, dealing_date: str):
    pending = _pending_requests(email)
    subs = round(sum(float(r.get("amount", 0.0)) for r in pending if r.get("activity_type") == "subscription"), 2)
    reds = round(sum(float(r.get("amount", 0.0)) for r in pending if r.get("activity_type") == "redemption"), 2)
    return {
        "day_id": f"deal_{int(time.time())}",
        "dealing_date": dealing_date,
        "cutoff_status": "open",
        "cutoff_applied_at": None,
        "pending_request_count": len(pending),
        "pending_subscription_amount": subs,
        "pending_redemption_amount": reds,
        "net_pending_flow": round(subs - reds, 2),
        "status": "scheduled",
        "notes": "",
        "created_at": int(time.time()),
    }

@router.get("/api/dealing-day")
def dealing_day():
    session = _require_user()
    return _load(session.get("email"))

@router.post("/api/dealing-day/policy")
def dealing_day_policy(payload: dict = Body(...)):
    _require_admin()
    email = (payload.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="email required")
    data = _load(email)
    policy = data.get("cutoff_policy", {})
    if "cutoff_hour_utc" in payload:
        policy["cutoff_hour_utc"] = int(payload.get("cutoff_hour_utc"))
    if "dealing_frequency" in payload:
        policy["dealing_frequency"] = str(payload.get("dealing_frequency"))
    if "same_day_processing" in payload:
        policy["same_day_processing"] = bool(payload.get("same_day_processing"))
    data["cutoff_policy"] = policy
    _save(email, data)
    return {"status": "updated", "cutoff_policy": policy}

@router.post("/api/dealing-day/create")
def dealing_day_create(payload: dict = Body(None)):
    session = _require_user()
    email = session.get("email")
    dealing_date = ((payload or {}).get("dealing_date") or _default_date_string()).strip()
    data = _load(email)
    item = _build_day(email, dealing_date)
    data.setdefault("dealing_days", []).insert(0, item)
    data["dealing_days"] = data["dealing_days"][:120]
    _save(email, data)
    return {"status": "created", "dealing_day": item}

@router.post("/api/dealing-day/apply-cutoff")
def dealing_day_apply_cutoff(payload: dict = Body(...)):
    _require_admin()
    email = (payload.get("email") or "").strip().lower()
    day_id = (payload.get("day_id") or "").strip()
    if not email or not day_id:
        raise HTTPException(status_code=400, detail="email and day_id required")
    data = _load(email)
    item = _find_day(data, day_id)
    if not item:
        raise HTTPException(status_code=404, detail="dealing day not found")
    pending = _pending_requests(email)
    subs = round(sum(float(r.get("amount", 0.0)) for r in pending if r.get("activity_type") == "subscription"), 2)
    reds = round(sum(float(r.get("amount", 0.0)) for r in pending if r.get("activity_type") == "redemption"), 2)
    item["cutoff_status"] = "applied"
    item["cutoff_applied_at"] = int(time.time())
    item["pending_request_count"] = len(pending)
    item["pending_subscription_amount"] = subs
    item["pending_redemption_amount"] = reds
    item["net_pending_flow"] = round(subs - reds, 2)
    item["status"] = "cutoff_locked"
    if payload.get("notes"):
        item["notes"] = str(payload.get("notes"))
    _save(email, data)
    return {"status": "cutoff_applied", "dealing_day": item}

@router.get("/api/dealing-day/summary")
def dealing_day_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    if not data.get("dealing_days"):
        item = _build_day(email, _default_date_string())
        data.setdefault("dealing_days", []).insert(0, item)
        _save(email, data)
    latest = data["dealing_days"][0]
    locked = sum(1 for d in data.get("dealing_days", []) if d.get("status") == "cutoff_locked")
    open_days = sum(1 for d in data.get("dealing_days", []) if d.get("cutoff_status") == "open")
    return {
        "email": email,
        "dealing_day_count": len(data.get("dealing_days", [])),
        "locked_count": locked,
        "open_count": open_days,
        "cutoff_policy": data.get("cutoff_policy", {}),
        "latest_dealing_day": latest,
        "dealing_days": data.get("dealing_days", [])[:50],
    }
