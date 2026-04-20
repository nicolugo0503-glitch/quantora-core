from fastapi import APIRouter, Body
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["investor-access-control-permission-matrix"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ACL_DIR = ARTIFACTS_DIR / "investor_access_control"

DEFAULT_MATRIX = {
    "portal_view": True,
    "download_reports": True,
    "receive_email_simulated": True,
    "view_archived_items": False,
    "manage_starred_items": True,
}

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _console():
    from backend.app import qnt30615_distribution_console_router as console
    return console

def _safe(v):
    return hashlib.sha256((v or "").strip().lower().encode()).hexdigest()[:24]

def _path(email):
    ACL_DIR.mkdir(parents=True, exist_ok=True)
    return ACL_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _load(email):
    p = _path(email)
    if not p.exists():
        d = {
            "email": email,
            "permission_matrix": DEFAULT_MATRIX,
            "access_log": [],
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

def _log_access(data, event_type, payload):
    data.setdefault("access_log", []).insert(0, {
        "log_id": f"acl_{int(time.time())}_{len(data.get('access_log', []))+1}",
        "event_type": event_type,
        "payload": payload,
        "timestamp": int(time.time()),
    })
    data["access_log"] = data["access_log"][:1000]

@router.get("/api/access-control")
def access_control():
    session = _require_user()
    return _load(session.get("email"))

@router.post("/api/access-control/configure")
def access_control_configure(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    matrix = data.get("permission_matrix", DEFAULT_MATRIX.copy())
    for key, value in (payload.get("permission_matrix") or {}).items():
        matrix[key] = bool(value)
    data["permission_matrix"] = matrix
    _log_access(data, "permissions_updated", {"permission_matrix": matrix})
    _save(email, data)
    return {"status": "configured", "permission_matrix": matrix}

@router.post("/api/access-control/check")
def access_control_check(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    capability = str(payload.get("capability") or "")
    data = _load(email)
    matrix = data.get("permission_matrix", DEFAULT_MATRIX)
    allowed = bool(matrix.get(capability, False))
    _log_access(data, "capability_checked", {"capability": capability, "allowed": allowed})
    _save(email, data)
    return {"status": "checked", "capability": capability, "allowed": allowed}

@router.post("/api/access-control/filter-inbox")
def access_control_filter_inbox(payload: dict = Body(None)):
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    matrix = data.get("permission_matrix", DEFAULT_MATRIX)
    console_data = _console()._load(email)
    items = console_data.get("inbox_items", [])

    visible = []
    for item in items:
        if item.get("archived") and not matrix.get("view_archived_items", False):
            continue
        visible.append(item)

    _log_access(data, "inbox_filtered", {"visible_count": len(visible)})
    _save(email, data)
    return {
        "status": "filtered",
        "visible_count": len(visible),
        "permission_matrix": matrix,
        "inbox_items": visible[:200]
    }

@router.get("/api/access-control/summary")
def access_control_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    matrix = data.get("permission_matrix", DEFAULT_MATRIX)
    enabled_count = sum(1 for _, v in matrix.items() if bool(v))
    return {
        "email": email,
        "permission_count": len(matrix),
        "enabled_permission_count": enabled_count,
        "permission_matrix": matrix,
        "latest_access_event": data.get("access_log", [None])[0] if data.get("access_log") else None,
        "access_log": data.get("access_log", [])[:100]
    }
