from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["data-room"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
DATA_ROOM_DIR = ARTIFACTS_DIR / "allocator_data_room"
ACCESS_DIR = ARTIFACTS_DIR / "allocator_data_room_access"

def _main():
    from backend.app import main as app_main
    return app_main

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _rep():
    from backend.app import qnt30564_reporting_router as rep
    return rep

def _safe(value: str) -> str:
    return hashlib.sha256((value or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _room_path() -> Path:
    DATA_ROOM_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_ROOM_DIR / "room_index.json"

def _access_path(email: str) -> Path:
    ACCESS_DIR.mkdir(parents=True, exist_ok=True)
    return ACCESS_DIR / f"{_safe(email)}.json"

def _load_room() -> dict:
    path = _room_path()
    if not path.exists():
        data = {
            "documents": [
                {"doc_id": "ddq_overview", "title": "DDQ Overview", "category": "due_diligence", "status": "available", "updated_at": int(time.time())},
                {"doc_id": "investor_reporting_sample", "title": "Investor Reporting Sample", "category": "reporting", "status": "available", "updated_at": int(time.time())},
                {"doc_id": "funding_process", "title": "Funding Process", "category": "operations", "status": "available", "updated_at": int(time.time())},
                {"doc_id": "reconciliation_controls", "title": "Reconciliation Controls", "category": "risk", "status": "available", "updated_at": int(time.time())},
            ],
            "notes": [],
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))

def _save_room(data: dict) -> dict:
    _room_path().write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data

def _load_access(email: str) -> dict:
    path = _access_path(email)
    if not path.exists():
        data = {"email": email, "requests": [], "grants": [], "activity": []}
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))

def _save_access(email: str, data: dict) -> dict:
    _access_path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data

def _require_user():
    return _mu()._require_session()

def _require_admin():
    return _main().require_admin()

@router.get("/api/data-room/index")
def data_room_index():
    _require_user()
    return _load_room()

@router.post("/api/data-room/request")
def data_room_request(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    doc_id = (payload.get("doc_id") or "").strip()
    if not doc_id:
        raise HTTPException(status_code=400, detail="doc_id required")
    access = _load_access(email)
    req = {
        "request_id": f"drreq_{int(time.time())}",
        "doc_id": doc_id,
        "status": "pending",
        "requested_at": int(time.time()),
        "notes": (payload.get("notes") or "").strip(),
    }
    access.setdefault("requests", []).insert(0, req)
    access["requests"] = access["requests"][:100]
    access.setdefault("activity", []).insert(0, {"type": "request", "doc_id": doc_id, "timestamp": int(time.time())})
    _save_access(email, access)
    return {"status": "requested", "request": req}

@router.get("/api/data-room/access")
def data_room_access():
    session = _require_user()
    email = session.get("email")
    return _load_access(email)

@router.post("/api/data-room/admin/grant")
def data_room_admin_grant(payload: dict = Body(...)):
    _require_admin()
    email = (payload.get("email") or "").strip().lower()
    doc_id = (payload.get("doc_id") or "").strip()
    if not email or not doc_id:
        raise HTTPException(status_code=400, detail="email and doc_id required")
    access = _load_access(email)
    grant = {
        "grant_id": f"drgrant_{int(time.time())}",
        "doc_id": doc_id,
        "granted_at": int(time.time()),
        "status": "active",
    }
    access.setdefault("grants", []).insert(0, grant)
    access["grants"] = access["grants"][:100]
    access.setdefault("activity", []).insert(0, {"type": "grant", "doc_id": doc_id, "timestamp": int(time.time())})
    _save_access(email, access)
    return {"status": "granted", "grant": grant}

@router.post("/api/data-room/admin/note")
def data_room_admin_note(payload: dict = Body(...)):
    _require_admin()
    room = _load_room()
    note = {
        "note_id": f"drnote_{int(time.time())}",
        "title": (payload.get("title") or "Data room note").strip(),
        "body": (payload.get("body") or "").strip(),
        "created_at": int(time.time()),
    }
    room.setdefault("notes", []).insert(0, note)
    room["notes"] = room["notes"][:100]
    _save_room(room)
    return {"status": "saved", "note": note}

@router.get("/api/data-room/packet")
def data_room_packet():
    session = _require_user()
    email = session.get("email")
    access = _load_access(email)
    room = _load_room()
    statements = _rep()._load_statement_store(email)
    granted_ids = {g.get("doc_id") for g in access.get("grants", []) if g.get("status") == "active"}
    packet_docs = [d for d in room.get("documents", []) if d.get("doc_id") in granted_ids]
    return {
        "email": email,
        "documents": packet_docs,
        "notes": room.get("notes", [])[:20],
        "statement_count": len(statements.get("statements", [])),
        "access": access,
    }
