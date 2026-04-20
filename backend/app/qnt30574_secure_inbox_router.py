from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["secure-inbox"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
INBOX_DIR = ARTIFACTS_DIR / "investor_secure_inbox"

def _main():
    from backend.app import main as app_main
    return app_main

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _safe(value: str) -> str:
    return hashlib.sha256((value or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _path(email: str) -> Path:
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    return INBOX_DIR / f"{_safe(email)}.json"

def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {"email": email, "threads": []}
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))

def _save(email: str, data: dict) -> dict:
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data

def _require_user():
    return _mu()._require_session()

def _require_admin():
    return _main().require_admin()

def _find_thread(data: dict, thread_id: str):
    return next((t for t in data.get("threads", []) if t.get("thread_id") == thread_id), None)

@router.get("/api/inbox")
def inbox_list():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    return data

@router.post("/api/inbox/thread")
def inbox_create_thread(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    subject = (payload.get("subject") or "Secure Message").strip()
    message = (payload.get("message") or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="message required")
    data = _load(email)
    thread = {
        "thread_id": f"thr_{int(time.time())}",
        "subject": subject,
        "status": "open",
        "created_at": int(time.time()),
        "updated_at": int(time.time()),
        "messages": [
            {
                "message_id": f"msg_{int(time.time())}",
                "sender_role": "investor",
                "body": message,
                "timestamp": int(time.time()),
                "read": True,
            }
        ],
    }
    data.setdefault("threads", []).insert(0, thread)
    data["threads"] = data["threads"][:200]
    _save(email, data)
    return {"status": "created", "thread": thread}

@router.post("/api/inbox/reply")
def inbox_reply(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    thread_id = payload.get("thread_id")
    body = (payload.get("body") or "").strip()
    if not thread_id or not body:
        raise HTTPException(status_code=400, detail="thread_id and body required")
    data = _load(email)
    thread = _find_thread(data, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="thread not found")
    msg = {
        "message_id": f"msg_{int(time.time())}",
        "sender_role": "investor",
        "body": body,
        "timestamp": int(time.time()),
        "read": True,
    }
    thread.setdefault("messages", []).append(msg)
    thread["updated_at"] = int(time.time())
    _save(email, data)
    return {"status": "sent", "thread": thread}

@router.post("/api/inbox/admin/reply")
def inbox_admin_reply(payload: dict = Body(...)):
    _require_admin()
    email = (payload.get("email") or "").strip().lower()
    thread_id = payload.get("thread_id")
    body = (payload.get("body") or "").strip()
    if not email or not thread_id or not body:
        raise HTTPException(status_code=400, detail="email, thread_id and body required")
    data = _load(email)
    thread = _find_thread(data, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="thread not found")
    msg = {
        "message_id": f"msg_{int(time.time())}",
        "sender_role": "admin",
        "body": body,
        "timestamp": int(time.time()),
        "read": False,
    }
    thread.setdefault("messages", []).append(msg)
    thread["updated_at"] = int(time.time())
    _save(email, data)
    return {"status": "sent", "thread": thread}

@router.post("/api/inbox/thread/close")
def inbox_close_thread(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    thread_id = payload.get("thread_id")
    data = _load(email)
    thread = _find_thread(data, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="thread not found")
    thread["status"] = "closed"
    thread["updated_at"] = int(time.time())
    _save(email, data)
    return {"status": "closed", "thread": thread}
