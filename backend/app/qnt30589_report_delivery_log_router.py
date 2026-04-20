from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["report-delivery-log"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
LOG_DIR = ARTIFACTS_DIR / "investor_report_delivery_log"

def _main():
    from backend.app import main as app_main
    return app_main

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _packs():
    from backend.app import qnt30588_statement_pack_router as packs
    return packs

def _safe(value: str) -> str:
    return hashlib.sha256((value or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _path(email: str) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return LOG_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _require_admin():
    return _main().require_admin()

def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {
            "email": email,
            "events": [],
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

@router.get("/api/report-delivery-log")
def report_delivery_log():
    session = _require_user()
    return _load(session.get("email"))

@router.post("/api/report-delivery-log/log")
def report_delivery_log_add(payload: dict = Body(...)):
    _require_admin()
    email = (payload.get("email") or "").strip().lower()
    pack_id = (payload.get("pack_id") or "").strip()
    channel = (payload.get("channel") or "portal_simulated").strip().lower()
    if not email or not pack_id:
        raise HTTPException(status_code=400, detail="email and pack_id required")
    data = _load(email)
    event = {
        "event_id": f"rptlog_{int(time.time())}",
        "pack_id": pack_id,
        "channel": channel,
        "delivery_status": "delivered",
        "ack_status": "pending",
        "delivered_at": int(time.time()),
        "acknowledged_at": None,
        "notes": (payload.get("notes") or "").strip(),
    }
    data.setdefault("events", []).insert(0, event)
    data["events"] = data["events"][:500]
    _save(email, data)
    return {"status": "logged", "event": event}

@router.post("/api/report-delivery-log/ack")
def report_delivery_log_ack(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    event_id = (payload.get("event_id") or "").strip()
    data = _load(email)
    event = next((e for e in data.get("events", []) if e.get("event_id") == event_id), None)
    if not event:
        raise HTTPException(status_code=404, detail="event not found")
    event["ack_status"] = "acknowledged"
    event["acknowledged_at"] = int(time.time())
    if payload.get("notes"):
        event["notes"] = str(payload.get("notes"))
    _save(email, data)
    return {"status": "acknowledged", "event": event}

@router.post("/api/report-delivery-log/log-latest-pack")
def report_delivery_log_latest(payload: dict = Body(None)):
    session = _require_user()
    email = session.get("email")
    packs = _packs()._load(email)
    latest = (packs.get("packs") or [None])[0]
    if not latest:
        raise HTTPException(status_code=404, detail="no statement pack found")
    data = _load(email)
    event = {
        "event_id": f"rptlog_{int(time.time())}",
        "pack_id": latest.get("pack_id"),
        "channel": ((payload or {}).get("channel") or "portal_simulated").strip().lower(),
        "delivery_status": "delivered",
        "ack_status": "pending",
        "delivered_at": int(time.time()),
        "acknowledged_at": None,
        "notes": ((payload or {}).get("notes") or "").strip(),
    }
    data.setdefault("events", []).insert(0, event)
    data["events"] = data["events"][:500]
    _save(email, data)
    return {"status": "logged", "event": event, "pack": latest}

@router.get("/api/report-delivery-log/summary")
def report_delivery_log_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    events = data.get("events", [])
    delivered = sum(1 for e in events if e.get("delivery_status") == "delivered")
    acked = sum(1 for e in events if e.get("ack_status") == "acknowledged")
    pending = sum(1 for e in events if e.get("ack_status") == "pending")
    latest = events[0] if events else None
    return {
        "email": email,
        "delivery_count": len(events),
        "delivered_count": delivered,
        "acknowledged_count": acked,
        "pending_ack_count": pending,
        "latest_event": latest,
        "events": events[:100],
    }
