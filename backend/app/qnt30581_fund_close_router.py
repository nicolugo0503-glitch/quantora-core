from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["fund-close-ledger"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
CLOSE_DIR = ARTIFACTS_DIR / "fund_close_ledger"

def _main():
    from backend.app import main as app_main
    return app_main

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _safe(value: str) -> str:
    return hashlib.sha256((value or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _path(email: str) -> Path:
    CLOSE_DIR.mkdir(parents=True, exist_ok=True)
    return CLOSE_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _require_admin():
    return _main().require_admin()

def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {"email": email, "fund_close_entries": []}
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))

def _save(email: str, data: dict) -> dict:
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data

@router.get("/api/fund-close")
def fund_close_entries():
    session = _require_user()
    return _load(session.get("email"))

@router.post("/api/fund-close/create")
def fund_close_create(payload: dict = Body(...)):
    _require_admin()
    email = (payload.get("email") or "").strip().lower()
    admitted_capital = round(float(payload.get("admitted_capital") or 0.0), 2)
    if not email or admitted_capital <= 0:
        raise HTTPException(status_code=400, detail="email and positive admitted_capital required")
    data = _load(email)
    entry = {
        "entry_id": f"close_{int(time.time())}",
        "title": (payload.get("title") or "Fund Close Admission").strip(),
        "admitted_capital": admitted_capital,
        "currency": "USD",
        "status": "pending_admission",
        "created_at": int(time.time()),
        "admitted_at": None,
        "notes": (payload.get("notes") or "").strip(),
    }
    data.setdefault("fund_close_entries", []).insert(0, entry)
    data["fund_close_entries"] = data["fund_close_entries"][:100]
    _save(email, data)
    return {"status": "created", "entry": entry}

@router.post("/api/fund-close/admit")
def fund_close_admit(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    entry_id = payload.get("entry_id")
    data = _load(email)
    entry = next((e for e in data.get("fund_close_entries", []) if e.get("entry_id") == entry_id), None)
    if not entry:
        raise HTTPException(status_code=404, detail="entry not found")
    entry["status"] = "admitted"
    entry["admitted_at"] = int(time.time())
    if payload.get("notes"):
        entry["notes"] = str(payload.get("notes"))
    _save(email, data)
    return {"status": "admitted", "entry": entry}

@router.get("/api/fund-close/summary")
def fund_close_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    items = data.get("fund_close_entries", [])
    pending = sum(1 for x in items if x.get("status") == "pending_admission")
    admitted = sum(1 for x in items if x.get("status") == "admitted")
    total = round(sum(float(x.get("admitted_capital") or 0.0) for x in items), 2)
    admitted_total = round(sum(float(x.get("admitted_capital") or 0.0) for x in items if x.get("status") == "admitted"), 2)
    return {
        "email": email,
        "total_entries": len(items),
        "pending_entries": pending,
        "admitted_entries": admitted,
        "total_capital": total,
        "admitted_capital": admitted_total,
        "entries": items,
    }
