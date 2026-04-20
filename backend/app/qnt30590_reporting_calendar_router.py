from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["reporting-calendar"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
CAL_DIR = ARTIFACTS_DIR / "investor_reporting_calendar"

DEFAULT_EVENTS = [
    {"name": "Monthly Statement Pack", "frequency": "monthly"},
    {"name": "Quarterly LP Update", "frequency": "quarterly"},
]

def _main():
    from backend.app import main as app_main
    return app_main

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _safe(value: str) -> str:
    return hashlib.sha256((value or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _path(email: str) -> Path:
    CAL_DIR.mkdir(parents=True, exist_ok=True)
    return CAL_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _require_admin():
    return _main().require_admin()

def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {
            "email": email,
            "events": [
                {
                    "event_id": f"evt_seed_{i}",
                    "name": e["name"],
                    "frequency": e["frequency"],
                    "next_run_at": None,
                    "status": "scheduled",
                    "channel": "portal_simulated",
                    "created_at": int(time.time()),
                    "last_run_at": None,
                } for i, e in enumerate(DEFAULT_EVENTS, start=1)
            ],
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

@router.get("/api/reporting-calendar")
def reporting_calendar():
    session = _require_user()
    return _load(session.get("email"))

@router.post("/api/reporting-calendar/schedule")
def reporting_calendar_schedule(payload: dict = Body(...)):
    _require_admin()
    email = (payload.get("email") or "").strip().lower()
    name = (payload.get("name") or "").strip()
    frequency = (payload.get("frequency") or "").strip().lower()
    channel = (payload.get("channel") or "portal_simulated").strip().lower()
    next_run_at = payload.get("next_run_at")
    if not email or not name or not frequency:
        raise HTTPException(status_code=400, detail="email, name, frequency required")
    data = _load(email)
    event = {
        "event_id": f"evt_{int(time.time())}",
        "name": name,
        "frequency": frequency,
        "next_run_at": next_run_at,
        "status": "scheduled",
        "channel": channel,
        "created_at": int(time.time()),
        "last_run_at": None,
    }
    data.setdefault("events", []).insert(0, event)
    data["events"] = data["events"][:200]
    _save(email, data)
    return {"status": "scheduled", "event": event}

@router.post("/api/reporting-calendar/run")
def reporting_calendar_run(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    event_id = (payload.get("event_id") or "").strip()
    data = _load(email)
    event = next((e for e in data.get("events", []) if e.get("event_id") == event_id), None)
    if not event:
        raise HTTPException(status_code=404, detail="event not found")
    event["last_run_at"] = int(time.time())
    event["status"] = "executed"
    data.setdefault("history", []).insert(0, {
        "history_id": f"hist_{int(time.time())}",
        "event_id": event_id,
        "name": event.get("name"),
        "channel": event.get("channel"),
        "executed_at": int(time.time()),
    })
    data["history"] = data["history"][:500]
    _save(email, data)
    return {"status": "executed", "event": event}

@router.get("/api/reporting-calendar/summary")
def reporting_calendar_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    events = data.get("events", [])
    scheduled = sum(1 for e in events if e.get("status") == "scheduled")
    executed = sum(1 for e in events if e.get("status") == "executed")
    latest = data.get("history", [None])[0] if data.get("history") else None
    return {
        "email": email,
        "event_count": len(events),
        "scheduled_count": scheduled,
        "executed_count": executed,
        "latest_history": latest,
        "events": events[:100],
        "history": data.get("history", [])[:100],
    }
