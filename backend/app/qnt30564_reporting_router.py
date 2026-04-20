from fastapi import APIRouter
from pathlib import Path
import json, time, hashlib, datetime

router = APIRouter(tags=["reporting"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
STATEMENTS_DIR = ARTIFACTS_DIR / "user_statements"

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _recon():
    from backend.app import qnt30563_reconciliation_router as recon
    return recon

def _safe_email(email: str) -> str:
    return hashlib.sha256((email or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _statement_path(email: str) -> Path:
    STATEMENTS_DIR.mkdir(parents=True, exist_ok=True)
    return STATEMENTS_DIR / f"{_safe_email(email)}.json"

def _require_user():
    mu = _mu()
    return mu._require_session()

def _load_statement_store(email: str) -> dict:
    path = _statement_path(email)
    if not path.exists():
        data = {"email": email, "statements": []}
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))

def _save_statement_store(email: str, data: dict) -> dict:
    _statement_path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data

def _period_label(ts: int) -> str:
    dt = datetime.datetime.utcfromtimestamp(int(ts))
    return dt.strftime("%Y-%m")

def _build_statement(email: str) -> dict:
    mu = _mu()
    recon = _recon()
    ledger = mu._load_ledger(email)
    current, series = mu._perf_snapshot(email, ledger)
    rec = recon._build_reconciliation(email)

    history = ledger.get("history", [])
    deposits = round(sum(float(x.get("amount") or 0.0) for x in history if (x.get("type") or "").lower() == "deposit"), 2)
    withdrawals = round(sum(float(x.get("amount") or 0.0) for x in history if (x.get("type") or "").lower() == "withdraw"), 2)
    broker_syncs = round(sum(float(x.get("amount") or 0.0) for x in history if (x.get("type") or "").lower() == "broker_sync"), 2)

    statement = {
        "statement_id": f"stmt_{int(time.time())}",
        "generated_at": int(time.time()),
        "period": _period_label(int(time.time())),
        "investor_email": email,
        "summary": {
            "balance": round(float(ledger.get("balance", 0.0)), 2),
            "available": round(float(ledger.get("available", 0.0)), 2),
            "allocated": round(float(ledger.get("allocated", 0.0)), 2),
            "net_invested_capital": round(float((current or {}).get("net_invested_capital", 0.0)), 2),
            "pnl_value": round(float((current or {}).get("pnl_value", 0.0)), 2),
            "return_pct": round(float((current or {}).get("return_pct", 0.0)), 2),
        },
        "flows": {
            "deposits": deposits,
            "withdrawals": withdrawals,
            "broker_syncs": broker_syncs,
            "net_flow": round(deposits - withdrawals, 2),
        },
        "reconciliation": {
            "status": rec.get("status"),
            "blockers": rec.get("blockers", []),
            "warnings": rec.get("warnings", []),
            "drift": rec.get("drift", {}),
        },
        "series_points": len(series),
        "recent_activity": history[:20],
    }
    return statement

@router.get("/api/user-statements")
def user_statements():
    session = _require_user()
    email = session.get("email")
    data = _load_statement_store(email)
    return data

@router.post("/api/user-statements/generate")
def user_statements_generate():
    session = _require_user()
    email = session.get("email")
    store = _load_statement_store(email)
    statement = _build_statement(email)
    store.setdefault("statements", []).insert(0, statement)
    store["statements"] = store["statements"][:50]
    _save_statement_store(email, store)
    return {"status": "generated", "statement": statement, "total_statements": len(store["statements"])}

@router.get("/api/user-statements/latest")
def user_statements_latest():
    session = _require_user()
    email = session.get("email")
    store = _load_statement_store(email)
    if not store.get("statements"):
        statement = _build_statement(email)
        store.setdefault("statements", []).insert(0, statement)
        _save_statement_store(email, store)
    return {"statement": store["statements"][0], "total_statements": len(store["statements"])}

@router.get("/api/user-reports/summary")
def user_reports_summary():
    session = _require_user()
    email = session.get("email")
    store = _load_statement_store(email)
    latest = store["statements"][0] if store.get("statements") else _build_statement(email)
    if not store.get("statements"):
        store.setdefault("statements", []).insert(0, latest)
        _save_statement_store(email, store)
    return {
        "investor_email": email,
        "latest_statement": latest,
        "reporting_status": "ready",
        "statement_count": len(store.get("statements", [])),
    }
