from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["capital-activity-control"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ACTIVITY_DIR = ARTIFACTS_DIR / "investor_capital_activity_control"

def _main():
    from backend.app import main as app_main
    return app_main

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _safe(value: str) -> str:
    return hashlib.sha256((value or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _path(email: str) -> Path:
    ACTIVITY_DIR.mkdir(parents=True, exist_ok=True)
    return ACTIVITY_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _require_admin():
    return _main().require_admin()

def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {
            "email": email,
            "requests": [],
            "history": [],
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

def _find_request(data: dict, request_id: str):
    return next((r for r in data.get("requests", []) if r.get("request_id") == request_id), None)

@router.get("/api/capital-activity")
def capital_activity():
    session = _require_user()
    return _load(session.get("email"))

@router.post("/api/capital-activity/request")
def capital_activity_request(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    activity_type = (payload.get("activity_type") or "").strip().lower()
    amount = round(float(payload.get("amount") or 0.0), 2)
    if activity_type not in {"subscription", "redemption"} or amount <= 0:
        raise HTTPException(status_code=400, detail="valid activity_type and positive amount required")
    data = _load(email)
    item = {
        "request_id": f"capreq_{int(time.time())}",
        "activity_type": activity_type,
        "amount": amount,
        "currency": "USD",
        "status": "pending_review",
        "created_at": int(time.time()),
        "reviewed_at": None,
        "processed_at": None,
        "notes": (payload.get("notes") or "").strip(),
    }
    data.setdefault("requests", []).insert(0, item)
    data.setdefault("history", []).insert(0, {
        "type": "request_created",
        "request_id": item["request_id"],
        "activity_type": activity_type,
        "amount": amount,
        "timestamp": int(time.time()),
    })
    data["requests"] = data["requests"][:300]
    data["history"] = data["history"][:500]
    _save(email, data)
    return {"status": "submitted", "request": item}

@router.post("/api/capital-activity/review")
def capital_activity_review(payload: dict = Body(...)):
    _require_admin()
    email = (payload.get("email") or "").strip().lower()
    request_id = (payload.get("request_id") or "").strip()
    decision = (payload.get("decision") or "").strip().lower()
    if not email or not request_id or decision not in {"approved", "rejected"}:
        raise HTTPException(status_code=400, detail="email, request_id, approved/rejected required")
    data = _load(email)
    item = _find_request(data, request_id)
    if not item:
        raise HTTPException(status_code=404, detail="request not found")
    item["status"] = decision
    item["reviewed_at"] = int(time.time())
    if payload.get("notes"):
        item["notes"] = str(payload.get("notes"))
    data.setdefault("history", []).insert(0, {
        "type": "request_reviewed",
        "request_id": request_id,
        "decision": decision,
        "timestamp": int(time.time()),
    })
    data["history"] = data["history"][:500]
    _save(email, data)
    return {"status": decision, "request": item}

@router.post("/api/capital-activity/process")
def capital_activity_process(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    request_id = (payload.get("request_id") or "").strip()
    data = _load(email)
    item = _find_request(data, request_id)
    if not item:
        raise HTTPException(status_code=404, detail="request not found")
    if item.get("status") != "approved":
        raise HTTPException(status_code=400, detail="request must be approved before processing")
    item["status"] = "processed"
    item["processed_at"] = int(time.time())
    if payload.get("notes"):
        item["notes"] = str(payload.get("notes"))

    mu = _mu()
    ledger = mu._load_ledger(email)
    amt = round(float(item.get("amount") or 0.0), 2)
    if item.get("activity_type") == "subscription":
        ledger["balance"] = float(ledger.get("balance", 0.0)) + amt
        ledger["available"] = float(ledger.get("available", 0.0)) + amt
    else:
        ledger["balance"] = float(ledger.get("balance", 0.0)) - amt
        ledger["available"] = float(ledger.get("available", 0.0)) - amt
    ledger.setdefault("history", []).insert(0, {
        "type": f"capital_activity_{item.get('activity_type')}",
        "amount": amt,
        "timestamp": int(time.time()),
        "source": "capital_activity_control"
    })
    saved = mu._save_ledger(email, ledger)

    data.setdefault("history", []).insert(0, {
        "type": "request_processed",
        "request_id": request_id,
        "activity_type": item.get("activity_type"),
        "amount": amt,
        "timestamp": int(time.time()),
    })
    data["history"] = data["history"][:500]
    _save(email, data)
    return {"status": "processed", "request": item, "capital": saved}

@router.get("/api/capital-activity/summary")
def capital_activity_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    requests = data.get("requests", [])
    pending = sum(1 for r in requests if r.get("status") == "pending_review")
    approved = sum(1 for r in requests if r.get("status") == "approved")
    processed = sum(1 for r in requests if r.get("status") == "processed")
    total_subscriptions = round(sum(float(r.get("amount", 0.0)) for r in requests if r.get("activity_type") == "subscription"), 2)
    total_redemptions = round(sum(float(r.get("amount", 0.0)) for r in requests if r.get("activity_type") == "redemption"), 2)
    return {
        "email": email,
        "request_count": len(requests),
        "pending_count": pending,
        "approved_count": approved,
        "processed_count": processed,
        "total_subscriptions": total_subscriptions,
        "total_redemptions": total_redemptions,
        "requests": requests[:200],
        "history": data.get("history", [])[:100],
    }
