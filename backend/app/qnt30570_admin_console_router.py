from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
import json, time, hashlib, os

router = APIRouter(tags=["institutional-admin"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
OVERSIGHT_DIR = ARTIFACTS_DIR / "institutional_admin_console"

def _main():
    from backend.app import main as app_main
    return app_main

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _ops():
    from backend.app import qnt30569_investor_ops_router as ops
    return ops

def _rep():
    from backend.app import qnt30564_reporting_router as rep
    return rep

def _fund():
    from backend.app import qnt30565_funding_router as fund
    return fund

def _recon():
    from backend.app import qnt30563_reconciliation_router as recon
    return recon

def _safe_email(email: str) -> str:
    return hashlib.sha256((email or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _path() -> Path:
    OVERSIGHT_DIR.mkdir(parents=True, exist_ok=True)
    return OVERSIGHT_DIR / "global_oversight.json"

def _load_store() -> dict:
    path = _path()
    if not path.exists():
        data = {"snapshots": [], "watchlist": [], "notes": []}
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))

def _save_store(data: dict) -> dict:
    _path().write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data

def _require_admin():
    app_main = _main()
    return app_main.require_admin()

def _all_user_emails():
    app_main = _main()
    users = app_main.users_db().get("users", [])
    emails = []
    for u in users:
        email = (u.get("email") or "").strip().lower()
        if email:
            emails.append(email)
    return emails

def _user_overview(email: str) -> dict:
    mu = _mu()
    rep = _rep()
    fund = _fund()
    recon = _recon()
    ledger = mu._load_ledger(email)
    perf, series = mu._perf_snapshot(email, ledger)
    statements = rep._load_statement_store(email)
    funding = fund._load_profile(email)
    intents = fund._load_intents(email)
    reconciliation = recon._build_reconciliation(email)
    return {
        "email": email,
        "balance": round(float(ledger.get("balance", 0.0)), 2),
        "available": round(float(ledger.get("available", 0.0)), 2),
        "allocated": round(float(ledger.get("allocated", 0.0)), 2),
        "return_pct": round(float((perf or {}).get("return_pct", 0.0)), 2),
        "pnl_value": round(float((perf or {}).get("pnl_value", 0.0)), 2),
        "statement_count": len(statements.get("statements", [])),
        "payment_methods": len(funding.get("payment_methods", [])),
        "intent_count": len(intents.get("payment_intents", [])),
        "kyc_status": funding.get("kyc_status"),
        "reconciliation_status": reconciliation.get("status"),
        "reconciliation_warnings": reconciliation.get("warnings", []),
        "series_points": len(series),
    }

@router.get("/api/admin-oversight/summary")
def admin_oversight_summary(admin=Body(None)):
    _require_admin()
    users = _all_user_emails()
    rows = [_user_overview(email) for email in users]
    total_balance = round(sum(float(r.get("balance", 0.0)) for r in rows), 2)
    total_allocated = round(sum(float(r.get("allocated", 0.0)) for r in rows), 2)
    total_available = round(sum(float(r.get("available", 0.0)) for r in rows), 2)
    investors_with_warnings = [r["email"] for r in rows if r.get("reconciliation_warnings")]
    investors_pending_kyc = [r["email"] for r in rows if str(r.get("kyc_status") or "").lower() != "approved_simulated"]
    payload = {
        "captured_at": int(time.time()),
        "investor_count": len(rows),
        "aggregate": {
            "total_balance": total_balance,
            "total_allocated": total_allocated,
            "total_available": total_available,
        },
        "alerts": {
            "reconciliation_warning_count": len(investors_with_warnings),
            "pending_kyc_count": len(investors_pending_kyc),
            "investors_with_warnings": investors_with_warnings[:20],
            "investors_pending_kyc": investors_pending_kyc[:20],
        },
        "investors": rows[:200],
    }
    store = _load_store()
    store.setdefault("snapshots", []).insert(0, payload)
    store["snapshots"] = store["snapshots"][:50]
    _save_store(store)
    return payload

@router.get("/api/admin-oversight/history")
def admin_oversight_history():
    _require_admin()
    return _load_store()

@router.post("/api/admin-oversight/watchlist")
def admin_oversight_watchlist(payload: dict = Body(...)):
    _require_admin()
    email = (payload.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email required")
    store = _load_store()
    watch = store.setdefault("watchlist", [])
    if email not in watch:
        watch.append(email)
    _save_store(store)
    return {"status": "added", "watchlist": watch}

@router.post("/api/admin-oversight/note")
def admin_oversight_note(payload: dict = Body(...)):
    _require_admin()
    email = (payload.get("email") or "").strip().lower()
    note = (payload.get("note") or "").strip()
    if not email or not note:
        raise HTTPException(status_code=400, detail="Email and note required")
    store = _load_store()
    entry = {"email": email, "note": note, "created_at": int(time.time())}
    store.setdefault("notes", []).insert(0, entry)
    store["notes"] = store["notes"][:200]
    _save_store(store)
    return {"status": "saved", "entry": entry}

@router.get("/api/admin-oversight/watchlist")
def admin_watchlist():
    _require_admin()
    store = _load_store()
    return {"watchlist": store.get("watchlist", []), "notes": store.get("notes", [])[:100]}
