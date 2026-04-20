from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["cash-ledger"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
CASH_DIR = ARTIFACTS_DIR / "investor_cash_ledger"

def _main():
    from backend.app import main as app_main
    return app_main

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _safe(value: str) -> str:
    return hashlib.sha256((value or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _path(email: str) -> Path:
    CASH_DIR.mkdir(parents=True, exist_ok=True)
    return CASH_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _require_admin():
    return _main().require_admin()

def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {
            "email": email,
            "entries": [],
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

@router.get("/api/cash-ledger")
def cash_ledger():
    session = _require_user()
    return _load(session.get("email"))

@router.post("/api/cash-ledger/distribution-notice")
def cash_distribution_notice(payload: dict = Body(...)):
    _require_admin()
    email = (payload.get("email") or "").strip().lower()
    amount = round(float(payload.get("amount") or 0.0), 2)
    if not email or amount <= 0:
        raise HTTPException(status_code=400, detail="email and positive amount required")
    data = _load(email)
    entry = {
        "entry_id": f"cash_{int(time.time())}",
        "type": "distribution_notice",
        "title": (payload.get("title") or "Investor Distribution Notice").strip(),
        "amount": amount,
        "currency": "USD",
        "status": "noticed",
        "noticed_at": int(time.time()),
        "processed_at": None,
        "notes": (payload.get("notes") or "").strip(),
    }
    data.setdefault("entries", []).insert(0, entry)
    data["entries"] = data["entries"][:500]
    _save(email, data)
    return {"status": "noticed", "entry": entry}

@router.post("/api/cash-ledger/process")
def cash_distribution_process(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    entry_id = (payload.get("entry_id") or "").strip()
    data = _load(email)
    entry = next((e for e in data.get("entries", []) if e.get("entry_id") == entry_id), None)
    if not entry:
        raise HTTPException(status_code=404, detail="entry not found")
    entry["status"] = "processed"
    entry["processed_at"] = int(time.time())
    if payload.get("notes"):
        entry["notes"] = str(payload.get("notes"))
    _save(email, data)

    mu = _mu()
    ledger = mu._load_ledger(email)
    amt = round(float(entry.get("amount") or 0.0), 2)
    ledger["balance"] = float(ledger.get("balance", 0.0)) + amt
    ledger["available"] = float(ledger.get("available", 0.0)) + amt
    ledger.setdefault("history", []).insert(0, {
        "type": "distribution_processed",
        "amount": amt,
        "timestamp": int(time.time()),
        "source": "cash_ledger_distribution"
    })
    saved = mu._save_ledger(email, ledger)
    perf, series = mu._perf_snapshot(email, saved)
    return {"status": "processed", "entry": entry, "capital": saved, "performance": perf, "series_points": len(series)}

@router.get("/api/cash-ledger/summary")
def cash_ledger_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    entries = data.get("entries", [])
    noticed = sum(1 for e in entries if e.get("status") == "noticed")
    processed = sum(1 for e in entries if e.get("status") == "processed")
    total_amount = round(sum(float(e.get("amount") or 0.0) for e in entries), 2)
    processed_amount = round(sum(float(e.get("amount") or 0.0) for e in entries if e.get("status") == "processed"), 2)
    return {
        "email": email,
        "entry_count": len(entries),
        "noticed_count": noticed,
        "processed_count": processed,
        "total_amount": total_amount,
        "processed_amount": processed_amount,
        "entries": entries[:200],
    }
