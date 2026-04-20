from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["capital-call-engine"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
CALL_DIR = ARTIFACTS_DIR / "capital_call_notices"

def _main():
    from backend.app import main as app_main
    return app_main

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _safe(value: str) -> str:
    return hashlib.sha256((value or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _path(email: str) -> Path:
    CALL_DIR.mkdir(parents=True, exist_ok=True)
    return CALL_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _require_admin():
    return _main().require_admin()

def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {"email": email, "notices": []}
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))

def _save(email: str, data: dict) -> dict:
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data

@router.get("/api/capital-calls")
def capital_calls():
    session = _require_user()
    return _load(session.get("email"))

@router.post("/api/capital-calls/create")
def capital_calls_create(payload: dict = Body(...)):
    _require_admin()
    email = (payload.get("email") or "").strip().lower()
    amount = round(float(payload.get("amount") or 0.0), 2)
    due_date = (payload.get("due_date") or "").strip()
    if not email or amount <= 0:
        raise HTTPException(status_code=400, detail="email and positive amount required")
    data = _load(email)
    notice = {
        "notice_id": f"cc_{int(time.time())}",
        "title": (payload.get("title") or "Capital Call Notice").strip(),
        "amount": amount,
        "currency": "USD",
        "status": "issued",
        "issued_at": int(time.time()),
        "due_date": due_date,
        "notes": (payload.get("notes") or "").strip(),
        "paid_at": None,
    }
    data.setdefault("notices", []).insert(0, notice)
    data["notices"] = data["notices"][:100]
    _save(email, data)
    return {"status": "issued", "notice": notice}

@router.post("/api/capital-calls/pay")
def capital_calls_pay(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    notice_id = payload.get("notice_id")
    data = _load(email)
    notice = next((n for n in data.get("notices", []) if n.get("notice_id") == notice_id), None)
    if not notice:
        raise HTTPException(status_code=404, detail="notice not found")
    notice["status"] = "paid_simulated"
    notice["paid_at"] = int(time.time())
    _save(email, data)

    mu = _mu()
    ledger = mu._load_ledger(email)
    amt = round(float(notice.get("amount") or 0.0), 2)
    ledger["balance"] = float(ledger.get("balance", 0.0)) + amt
    ledger["available"] = float(ledger.get("available", 0.0)) + amt
    ledger.setdefault("history", []).insert(0, {
        "type": "capital_call_payment",
        "amount": amt,
        "timestamp": int(time.time()),
        "source": "capital_call_engine"
    })
    saved = mu._save_ledger(email, ledger)
    perf, series = mu._perf_snapshot(email, saved)
    return {"status": "paid", "notice": notice, "capital": saved, "performance": perf, "series_points": len(series)}

@router.get("/api/capital-calls/summary")
def capital_calls_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    notices = data.get("notices", [])
    issued = sum(1 for n in notices if n.get("status") == "issued")
    paid = sum(1 for n in notices if str(n.get("status")).startswith("paid"))
    total = round(sum(float(n.get("amount") or 0.0) for n in notices), 2)
    paid_total = round(sum(float(n.get("amount") or 0.0) for n in notices if str(n.get("status")).startswith("paid")), 2)
    return {
        "email": email,
        "total_notices": len(notices),
        "issued_notices": issued,
        "paid_notices": paid,
        "total_amount": total,
        "paid_amount": paid_total,
        "notices": notices,
    }
