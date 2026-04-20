from fastapi import APIRouter, Body
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["distribution-console-investor-inbox"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
INBOX_DIR = ARTIFACTS_DIR / "investor_delivery_inbox"

DEFAULT_INBOX_SETTINGS = {
    "portal_access_enabled": True,
    "show_published_only": False
}

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _delivery():
    from backend.app import qnt30614_delivery_router as delivery
    return delivery

def _safe(v):
    return hashlib.sha256((v or "").strip().lower().encode()).hexdigest()[:24]

def _path(email):
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    return INBOX_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _load(email):
    p = _path(email)
    if not p.exists():
        d = {
            "email": email,
            "inbox_settings": DEFAULT_INBOX_SETTINGS,
            "inbox_items": [],
            "console_runs": [],
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

def _sync_inbox(email):
    data = _load(email)
    delivery_data = _delivery()._load(email)
    deliveries = delivery_data.get("deliveries", []) or []

    existing_ids = {x.get("delivery_id") for x in data.get("inbox_items", [])}
    new_items = []
    for d in deliveries:
        if d.get("delivery_id") in existing_ids:
            continue
        item = {
            "inbox_id": f"inbox_{int(time.time())}_{len(new_items)+1}",
            "delivery_id": d.get("delivery_id"),
            "channel": d.get("channel"),
            "title": d.get("title"),
            "packet_id": d.get("packet_id"),
            "report_id": d.get("report_id"),
            "delivery_status": d.get("status"),
            "published": True,
            "read_status": "unread",
            "starred": False,
            "archived": False,
            "received_at": d.get("delivered_at") or int(time.time()),
            "opened_at": None,
            "notes": d.get("notes", "")
        }
        data.setdefault("inbox_items", []).insert(0, item)
        new_items.append(item)

    data["inbox_items"] = data.get("inbox_items", [])[:500]
    run = {
        "run_id": f"console_{int(time.time())}",
        "timestamp": int(time.time()),
        "delivery_count": len(deliveries),
        "new_inbox_items": len(new_items),
        "status": "synced"
    }
    data.setdefault("console_runs", []).insert(0, run)
    data["console_runs"] = data.get("console_runs", [])[:200]
    _save(email, data)
    return run, new_items

@router.get("/api/distribution-console")
def distribution_console():
    session = _require_user()
    return _load(session.get("email"))

@router.post("/api/distribution-console/sync")
def distribution_console_sync(payload: dict = Body(None)):
    session = _require_user()
    email = session.get("email")
    run, items = _sync_inbox(email)
    return {"status": run["status"], "run": run, "new_items": items}

@router.post("/api/distribution-console/open")
def distribution_console_open(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    inbox_id = str(payload.get("inbox_id") or "")
    data = _load(email)
    item = next((x for x in data.get("inbox_items", []) if x.get("inbox_id") == inbox_id), None)
    if not item:
        return {"status": "not_found"}
    item["read_status"] = "read"
    item["opened_at"] = int(time.time())
    _save(email, data)
    return {"status": "opened", "item": item}

@router.post("/api/distribution-console/star")
def distribution_console_star(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    inbox_id = str(payload.get("inbox_id") or "")
    data = _load(email)
    item = next((x for x in data.get("inbox_items", []) if x.get("inbox_id") == inbox_id), None)
    if not item:
        return {"status": "not_found"}
    item["starred"] = bool(payload.get("starred", True))
    _save(email, data)
    return {"status": "updated", "item": item}

@router.post("/api/distribution-console/archive")
def distribution_console_archive(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    inbox_id = str(payload.get("inbox_id") or "")
    data = _load(email)
    item = next((x for x in data.get("inbox_items", []) if x.get("inbox_id") == inbox_id), None)
    if not item:
        return {"status": "not_found"}
    item["archived"] = True
    _save(email, data)
    return {"status": "archived", "item": item}

@router.get("/api/distribution-console/summary")
def distribution_console_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    if not data.get("console_runs"):
        _sync_inbox(email)
        data = _load(email)
    items = data.get("inbox_items", [])
    unread = sum(1 for x in items if x.get("read_status") == "unread" and not x.get("archived"))
    starred = sum(1 for x in items if x.get("starred") and not x.get("archived"))
    archived = sum(1 for x in items if x.get("archived"))
    latest = items[0] if items else None
    return {
        "email": email,
        "inbox_count": len(items),
        "unread_count": unread,
        "starred_count": starred,
        "archived_count": archived,
        "latest_item": latest,
        "inbox_items": items[:100],
        "console_runs": data.get("console_runs", [])[:50],
        "inbox_settings": data.get("inbox_settings", DEFAULT_INBOX_SETTINGS)
    }
