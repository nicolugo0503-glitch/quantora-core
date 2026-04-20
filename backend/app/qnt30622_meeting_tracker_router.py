from fastapi import APIRouter, Body
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["investor-meeting-tracker-dd-room"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
DD_DIR = ARTIFACTS_DIR / "investor_meeting_dd_workflow"

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _pipeline():
    from backend.app import qnt30621_pipeline_router as pipeline
    return pipeline

def _safe(v):
    return hashlib.sha256((v or "").strip().lower().encode()).hexdigest()[:24]

def _path(email):
    DD_DIR.mkdir(parents=True, exist_ok=True)
    return DD_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _load(email):
    p = _path(email)
    if not p.exists():
        d = {
            "email": email,
            "meetings": [],
            "dd_rooms": [],
            "dd_items": [],
            "created_at": int(time.time()),
            "updated_at": int(time.time())
        }
        p.write_text(json.dumps(d, indent=2), encoding="utf-8")
        return d
    return json.loads(p.read_text(encoding="utf-8"))

def _save(email, d):
    d["updated_at"] = int(time.time())
    _path(email).write_text(json.dumps(d, indent=2), encoding="utf-8")
    return d

def _find_meeting(data, meeting_id):
    return next((m for m in data.get("meetings", []) if m.get("meeting_id") == meeting_id), None)

def _find_room(data, room_id):
    return next((r for r in data.get("dd_rooms", []) if r.get("room_id") == room_id), None)

@router.get("/api/dd-workflow")
def dd_workflow():
    session = _require_user()
    return _load(session.get("email"))

@router.post("/api/dd-workflow/meeting")
def create_meeting(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    item = {
        "meeting_id": f"meet_{int(time.time())}",
        "opportunity_id": str(payload.get("opportunity_id") or ""),
        "title": str(payload.get("title") or "Investor Meeting"),
        "meeting_type": str(payload.get("meeting_type") or "intro"),
        "scheduled_for": str(payload.get("scheduled_for") or ""),
        "owner": str(payload.get("owner") or "Unassigned"),
        "status": "scheduled",
        "location": str(payload.get("location") or "virtual"),
        "notes": str(payload.get("notes") or ""),
        "created_at": int(time.time())
    }
    data.setdefault("meetings", []).insert(0, item)
    data["meetings"] = data.get("meetings", [])[:1000]
    _save(email, data)
    return {"status": "created", "meeting": item}

@router.post("/api/dd-workflow/meeting/update")
def update_meeting(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    meeting_id = str(payload.get("meeting_id") or "")
    data = _load(email)
    item = _find_meeting(data, meeting_id)
    if not item:
        return {"status": "not_found"}
    for key in ["title", "meeting_type", "scheduled_for", "owner", "status", "location", "notes"]:
        if key in payload and payload.get(key) is not None:
            item[key] = str(payload.get(key))
    item["updated_at"] = int(time.time())
    _save(email, data)
    return {"status": "updated", "meeting": item}

@router.post("/api/dd-workflow/room")
def create_dd_room(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    item = {
        "room_id": f"room_{int(time.time())}",
        "opportunity_id": str(payload.get("opportunity_id") or ""),
        "room_name": str(payload.get("room_name") or "Due Diligence Room"),
        "status": "open",
        "owner": str(payload.get("owner") or "Unassigned"),
        "access_level": str(payload.get("access_level") or "controlled"),
        "created_at": int(time.time())
    }
    data.setdefault("dd_rooms", []).insert(0, item)
    data["dd_rooms"] = data.get("dd_rooms", [])[:1000]
    _save(email, data)
    return {"status": "created", "room": item}

@router.post("/api/dd-workflow/item")
def add_dd_item(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    room_id = str(payload.get("room_id") or "")
    data = _load(email)
    room = _find_room(data, room_id)
    if not room:
        return {"status": "room_not_found"}
    item = {
        "item_id": f"ddi_{int(time.time())}",
        "room_id": room_id,
        "opportunity_id": room.get("opportunity_id"),
        "title": str(payload.get("title") or "DD Item"),
        "item_type": str(payload.get("item_type") or "document_request"),
        "status": str(payload.get("status") or "requested"),
        "priority": str(payload.get("priority") or "normal"),
        "owner": str(payload.get("owner") or room.get("owner") or "Unassigned"),
        "detail": str(payload.get("detail") or ""),
        "created_at": int(time.time())
    }
    data.setdefault("dd_items", []).insert(0, item)
    data["dd_items"] = data.get("dd_items", [])[:2000]
    _save(email, data)
    return {"status": "created", "item": item}

@router.get("/api/dd-workflow/summary")
def dd_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    meetings = data.get("meetings", [])
    rooms = data.get("dd_rooms", [])
    items = data.get("dd_items", [])

    scheduled = sum(1 for m in meetings if m.get("status") == "scheduled")
    completed = sum(1 for m in meetings if m.get("status") == "completed")
    open_rooms = sum(1 for r in rooms if r.get("status") == "open")
    open_items = sum(1 for i in items if i.get("status") not in {"completed", "closed"})
    latest_meeting = meetings[0] if meetings else None
    latest_room = rooms[0] if rooms else None
    latest_item = items[0] if items else None

    return {
        "email": email,
        "meeting_count": len(meetings),
        "room_count": len(rooms),
        "item_count": len(items),
        "scheduled_meeting_count": scheduled,
        "completed_meeting_count": completed,
        "open_room_count": open_rooms,
        "open_item_count": open_items,
        "latest_meeting": latest_meeting,
        "latest_room": latest_room,
        "latest_item": latest_item,
        "meetings": meetings[:100],
        "dd_rooms": rooms[:100],
        "dd_items": items[:100]
    }
