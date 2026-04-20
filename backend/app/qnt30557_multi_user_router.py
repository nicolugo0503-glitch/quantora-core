from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
import json, time, hashlib, hmac

router = APIRouter(tags=["multi-user"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
USER_LEDGER_DIR = ARTIFACTS_DIR / "user_ledgers"
USER_PERF_DIR = ARTIFACTS_DIR / "user_performance"

def _main():
    from backend.app import main as app_main
    return app_main

def _safe_email(email: str) -> str:
    return hashlib.sha256((email or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _ledger_path(email: str) -> Path:
    USER_LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    return USER_LEDGER_DIR / f"{_safe_email(email)}.json"

def _perf_path(email: str) -> Path:
    USER_PERF_DIR.mkdir(parents=True, exist_ok=True)
    return USER_PERF_DIR / f"{_safe_email(email)}.json"

def _default_ledger(email: str):
    return {
        "email": (email or "").strip().lower(),
        "balance": 0.0,
        "available": 0.0,
        "allocated": 0.0,
        "history": [],
        "created_at": int(time.time()),
    }

def _load_ledger(email: str):
    path = _ledger_path(email)
    if not path.exists():
        data = _default_ledger(email)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))

def _save_ledger(email: str, data: dict):
    data["balance"] = round(float(data.get("balance", 0.0)), 2)
    data["available"] = round(float(data.get("available", 0.0)), 2)
    data["allocated"] = round(float(data.get("allocated", 0.0)), 2)
    _ledger_path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data

def _append(data: dict, typ: str, amount: float):
    data.setdefault("history", []).insert(0, {
        "type": typ,
        "amount": round(float(amount), 2),
        "timestamp": int(time.time())
    })
    data["history"] = data["history"][:200]

def _perf_snapshot(email: str, ledger: dict):
    path = _perf_path(email)
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        payload = {"series": []}
    deposits = 0.0
    withdrawals = 0.0
    for row in ledger.get("history", []):
        typ = (row.get("type") or "").lower()
        amt = float(row.get("amount") or 0.0)
        if typ == "deposit":
            deposits += amt
        elif typ == "withdraw":
            withdrawals += amt
    net_flow = deposits - withdrawals
    snap = {
        "timestamp": int(time.time()),
        "balance": round(float(ledger.get("balance", 0.0)), 2),
        "available": round(float(ledger.get("available", 0.0)), 2),
        "allocated": round(float(ledger.get("allocated", 0.0)), 2),
        "net_invested_capital": round(net_flow, 2),
        "pnl_value": round(float(ledger.get("balance", 0.0)) - net_flow, 2),
    }
    snap["return_pct"] = 0.0 if abs(net_flow) < 1e-9 else round((snap["pnl_value"] / net_flow) * 100.0, 2)
    series = payload.get("series", [])
    if not series or any(round(float(series[-1].get(k, 0.0)), 2) != round(float(snap.get(k, 0.0)), 2) for k in ["balance", "available", "allocated", "net_invested_capital", "pnl_value"]):
        series.append(snap)
    else:
        series[-1] = snap
    payload["series"] = series[-300:]
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return snap, payload["series"]

def _require_session():
    app_main = _main()
    session = app_main.get_session()
    if not session.get("logged_in") or not session.get("email"):
        raise HTTPException(status_code=401, detail="Authentication required")
    return app_main.session_view(session)

@router.post("/api/user/register")
def user_register(payload: dict = Body(...)):
    app_main = _main()
    model = app_main.RegisterRequest(**payload)
    result = app_main.auth_register(model)
    email = (payload.get("email") or "").strip().lower()
    _save_ledger(email, _default_ledger(email))
    _perf_snapshot(email, _load_ledger(email))
    return {"status": "registered", "user": {"email": email, "display_name": payload.get("display_name") or "Operator"}, "auth": result}

@router.post("/api/user/login")
def user_login(payload: dict = Body(...)):
    app_main = _main()
    model = app_main.LoginRequest(**payload)
    result = app_main.auth_login(model)
    email = (payload.get("email") or "").strip().lower()
    _load_ledger(email)
    _perf_snapshot(email, _load_ledger(email))
    return {"status": "logged_in", "user": {"email": email}, "auth": result}

@router.post("/api/user/logout")
def user_logout():
    app_main = _main()
    return app_main.auth_logout()

@router.get("/api/user/me")
def user_me():
    session = _require_session()
    ledger = _load_ledger(session.get("email"))
    current, _series = _perf_snapshot(session.get("email"), ledger)
    return {"user": {"email": session.get("email"), "display_name": session.get("display_name")}, "capital": ledger, "performance": current}

@router.get("/api/user-capital")
def user_capital():
    session = _require_session()
    return _load_ledger(session.get("email"))

@router.post("/api/user-capital/deposit")
def user_capital_deposit(payload: dict = Body(...)):
    session = _require_session()
    amount = round(float(payload.get("amount") or 0.0), 2)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")
    data = _load_ledger(session.get("email"))
    data["balance"] = float(data.get("balance", 0.0)) + amount
    data["available"] = float(data.get("available", 0.0)) + amount
    _append(data, "deposit", amount)
    saved = _save_ledger(session.get("email"), data)
    current, series = _perf_snapshot(session.get("email"), saved)
    return {"capital": saved, "performance": current, "series_points": len(series)}

@router.post("/api/user-capital/withdraw")
def user_capital_withdraw(payload: dict = Body(...)):
    session = _require_session()
    amount = round(float(payload.get("amount") or 0.0), 2)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")
    data = _load_ledger(session.get("email"))
    if amount > float(data.get("available", 0.0)):
        raise HTTPException(status_code=400, detail="Insufficient available balance")
    data["balance"] = float(data.get("balance", 0.0)) - amount
    data["available"] = float(data.get("available", 0.0)) - amount
    _append(data, "withdraw", amount)
    saved = _save_ledger(session.get("email"), data)
    current, series = _perf_snapshot(session.get("email"), saved)
    return {"capital": saved, "performance": current, "series_points": len(series)}

@router.get("/api/user-performance")
def user_performance():
    session = _require_session()
    ledger = _load_ledger(session.get("email"))
    current, series = _perf_snapshot(session.get("email"), ledger)
    return {"current": current, "series": series}
