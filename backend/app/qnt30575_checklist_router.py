from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["investor-checklist"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
CHECKLIST_DIR = ARTIFACTS_DIR / "investor_onboarding_checklists"

DEFAULT_TASKS = [
    {"task_id": "create_account", "title": "Create account", "category": "identity"},
    {"task_id": "complete_kyc", "title": "Complete KYC", "category": "compliance"},
    {"task_id": "add_funding_method", "title": "Add funding method", "category": "funding"},
    {"task_id": "create_deposit_intent", "title": "Create deposit intent", "category": "funding"},
    {"task_id": "first_deposit_complete", "title": "Complete first deposit", "category": "funding"},
    {"task_id": "review_statement", "title": "Review first statement", "category": "reporting"},
    {"task_id": "open_secure_thread", "title": "Open secure support thread", "category": "communications"},
]

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _fund():
    from backend.app import qnt30565_funding_router as fr
    return fr

def _rep():
    from backend.app import qnt30564_reporting_router as rr
    return rr

def _inbox():
    from backend.app import qnt30574_secure_inbox_router as ib
    return ib

def _safe(value: str) -> str:
    return hashlib.sha256((value or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _path(email: str) -> Path:
    CHECKLIST_DIR.mkdir(parents=True, exist_ok=True)
    return CHECKLIST_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {
            "email": email,
            "tasks": [
                {
                    **task,
                    "status": "pending",
                    "completed_at": None,
                    "notes": ""
                } for task in DEFAULT_TASKS
            ],
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

def _mark(data: dict, task_id: str, done: bool, notes: str = ""):
    task = next((t for t in data.get("tasks", []) if t.get("task_id") == task_id), None)
    if task:
        task["status"] = "completed" if done else "pending"
        task["completed_at"] = int(time.time()) if done else None
        if notes:
            task["notes"] = notes
    return task

def _auto_reconcile(email: str, data: dict) -> dict:
    mu = _mu()
    fund = _fund()
    rep = _rep()
    inbox = _inbox()

    _mark(data, "create_account", True)

    try:
        profile = fund._load_profile(email)
    except Exception:
        profile = {"kyc_status": "not_started", "payment_methods": []}
    try:
        intents = fund._load_intents(email)
    except Exception:
        intents = {"payment_intents": []}
    try:
        statements = rep._load_statement_store(email)
    except Exception:
        statements = {"statements": []}
    try:
        threads = inbox._load(email)
    except Exception:
        threads = {"threads": []}

    ledger = mu._load_ledger(email)

    _mark(data, "complete_kyc", str(profile.get("kyc_status") or "").lower() == "approved_simulated")
    _mark(data, "add_funding_method", len(profile.get("payment_methods", [])) > 0)
    _mark(data, "create_deposit_intent", len(intents.get("payment_intents", [])) > 0)
    _mark(data, "first_deposit_complete", float(ledger.get("balance", 0.0)) > 0)
    _mark(data, "review_statement", len(statements.get("statements", [])) > 0)
    _mark(data, "open_secure_thread", len(threads.get("threads", [])) > 0)

    return data

@router.get("/api/onboarding-checklist")
def onboarding_checklist():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    data = _auto_reconcile(email, data)
    _save(email, data)
    return data

@router.post("/api/onboarding-checklist/task")
def onboarding_checklist_task(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    task_id = (payload.get("task_id") or "").strip()
    if not task_id:
        raise HTTPException(status_code=400, detail="task_id required")
    data = _load(email)
    task = _mark(data, task_id, bool(payload.get("completed", True)), str(payload.get("notes") or ""))
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    _save(email, data)
    return {"status": "updated", "task": task}

@router.get("/api/onboarding-checklist/summary")
def onboarding_checklist_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    data = _auto_reconcile(email, data)
    _save(email, data)
    tasks = data.get("tasks", [])
    completed = sum(1 for t in tasks if t.get("status") == "completed")
    total = len(tasks)
    progress = round((completed / total) * 100.0, 2) if total else 0.0
    return {
        "email": email,
        "total_tasks": total,
        "completed_tasks": completed,
        "pending_tasks": total - completed,
        "progress_pct": progress,
        "tasks": tasks,
    }
