from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["allocation-confirmation-contract-note"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
CONF_DIR = ARTIFACTS_DIR / "investor_allocation_confirmations"

def _main():
    from backend.app import main as app_main
    return app_main

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _nav():
    from backend.app import qnt30597_nav_strike_router as nav
    return nav

def _activity():
    from backend.app import qnt30595_capital_activity_router as activity
    return activity

def _safe(value: str) -> str:
    return hashlib.sha256((value or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _path(email: str) -> Path:
    CONF_DIR.mkdir(parents=True, exist_ok=True)
    return CONF_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _require_admin():
    return _main().require_admin()

def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {"email": email, "notes": [], "created_at": int(time.time()), "updated_at": int(time.time())}
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))

def _save(email: str, data: dict) -> dict:
    data["updated_at"] = int(time.time())
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data

def _build_note(email: str, title: str):
    nav_data = _nav()._load(email)
    latest_val = (nav_data.get("valuations") or [None])[0]
    activity_data = _activity()._load(email)
    processed = [r for r in activity_data.get("requests", []) if r.get("status") == "processed"]
    subs = round(sum(float(r.get("amount", 0.0)) for r in processed if r.get("activity_type") == "subscription"), 2)
    reds = round(sum(float(r.get("amount", 0.0)) for r in processed if r.get("activity_type") == "redemption"), 2)
    official_nav = round(float((latest_val or {}).get("official_nav", 0.0)), 2)
    net_capital_activity = round(subs - reds, 2)
    allocated_nav = round(official_nav + net_capital_activity, 2)
    return {
        "note_id": f"note_{int(time.time())}",
        "title": title,
        "generated_at": int(time.time()),
        "official_nav": official_nav,
        "processed_subscriptions": subs,
        "processed_redemptions": reds,
        "net_capital_activity": net_capital_activity,
        "allocated_nav": allocated_nav,
        "valuation_id": (latest_val or {}).get("valuation_id"),
        "status": "generated",
        "ack_status": "pending",
        "delivered_at": None,
        "acknowledged_at": None,
        "notes": "",
    }

@router.get("/api/allocation-confirmations")
def allocation_confirmations():
    session = _require_user()
    return _load(session.get("email"))

@router.post("/api/allocation-confirmations/generate")
def allocation_confirmations_generate(payload: dict = Body(None)):
    session = _require_user()
    email = session.get("email")
    title = ((payload or {}).get("title") or "Investor Allocation Confirmation").strip()
    data = _load(email)
    item = _build_note(email, title)
    data.setdefault("notes", []).insert(0, item)
    data["notes"] = data["notes"][:150]
    _save(email, data)
    return {"status": "generated", "note": item, "total_notes": len(data["notes"])}

@router.post("/api/allocation-confirmations/deliver")
def allocation_confirmations_deliver(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    note_id = (payload.get("note_id") or "").strip()
    data = _load(email)
    item = next((n for n in data.get("notes", []) if n.get("note_id") == note_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="note not found")
    item["status"] = "delivered"
    item["delivered_at"] = int(time.time())
    if payload.get("notes"):
        item["notes"] = str(payload.get("notes"))
    _save(email, data)
    return {"status": "delivered", "note": item}

@router.post("/api/allocation-confirmations/ack")
def allocation_confirmations_ack(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    note_id = (payload.get("note_id") or "").strip()
    data = _load(email)
    item = next((n for n in data.get("notes", []) if n.get("note_id") == note_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="note not found")
    item["ack_status"] = "acknowledged"
    item["acknowledged_at"] = int(time.time())
    _save(email, data)
    return {"status": "acknowledged", "note": item}

@router.get("/api/allocation-confirmations/summary")
def allocation_confirmations_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    if not data.get("notes"):
        item = _build_note(email, "Investor Allocation Confirmation")
        data.setdefault("notes", []).insert(0, item)
        _save(email, data)
    latest = data["notes"][0]
    delivered = sum(1 for n in data.get("notes", []) if n.get("status") == "delivered")
    acked = sum(1 for n in data.get("notes", []) if n.get("ack_status") == "acknowledged")
    return {
        "email": email,
        "note_count": len(data.get("notes", [])),
        "delivered_count": delivered,
        "acknowledged_count": acked,
        "latest_note": latest,
        "notes": data.get("notes", [])[:50],
    }
