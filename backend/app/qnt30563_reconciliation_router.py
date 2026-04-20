from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["reconciliation"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
BROKER_PROFILE_DIR = ARTIFACTS_DIR / "user_broker_profiles"
RECON_DIR = ARTIFACTS_DIR / "user_reconciliation"

def _main():
    from backend.app import main as app_main
    return app_main

def _multi():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _safe_email(email: str) -> str:
    return hashlib.sha256((email or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _profile_path(email: str) -> Path:
    BROKER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    return BROKER_PROFILE_DIR / f"{_safe_email(email)}.json"

def _recon_path(email: str) -> Path:
    RECON_DIR.mkdir(parents=True, exist_ok=True)
    return RECON_DIR / f"{_safe_email(email)}.json"

def _default_profile(email: str) -> dict:
    return {
        "email": (email or "").strip().lower(),
        "broker": "alpaca",
        "linked": False,
        "account_id": None,
        "paper": True,
        "created_at": int(time.time()),
        "updated_at": int(time.time()),
    }

def _load_profile(email: str) -> dict:
    path = _profile_path(email)
    if not path.exists():
        data = _default_profile(email)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))

def _save_profile(email: str, data: dict) -> dict:
    data["updated_at"] = int(time.time())
    _profile_path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data

def _save_recon(email: str, data: dict) -> dict:
    _recon_path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data

def _load_recon(email: str) -> dict:
    path = _recon_path(email)
    if not path.exists():
        data = {"email": (email or "").strip().lower(), "checks": [], "last_run_at": None}
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))

def _require_user():
    mu = _multi()
    return mu._require_session()

def _to_float(v):
    try:
        return float(v)
    except Exception:
        return 0.0

def _alpaca_snapshot():
    app_main = _main()
    state = app_main.refresh_alpaca_state(soft=True)
    account = state.get("account") or {}
    positions = state.get("positions") or []
    orders = state.get("orders") or []
    exposure = 0.0
    unrealized = 0.0
    for p in positions:
        exposure += abs(_to_float(p.get("market_value") or p.get("current_market_value") or 0.0))
        unrealized += _to_float(p.get("unrealized_pl") or p.get("unrealized_pnl") or 0.0)
    return {
        "connected": bool(state.get("connected")),
        "paper": bool(state.get("paper", True)),
        "account_id": account.get("id") or account.get("account_id"),
        "portfolio_value": _to_float(account.get("portfolio_value") or account.get("equity") or 0.0),
        "cash": _to_float(account.get("cash") or account.get("buying_power") or 0.0),
        "positions": positions,
        "orders": orders[:50],
        "position_count": len(positions),
        "open_order_count": len(orders),
        "gross_exposure": round(exposure, 2),
        "unrealized_pnl": round(unrealized, 2),
    }

def _build_reconciliation(email: str) -> dict:
    mu = _multi()
    ledger = mu._load_ledger(email)
    current, series = mu._perf_snapshot(email, ledger)
    profile = _load_profile(email)
    broker = _alpaca_snapshot()

    system_balance = _to_float(ledger.get("balance"))
    system_available = _to_float(ledger.get("available"))
    system_allocated = _to_float(ledger.get("allocated"))
    broker_exposure = _to_float(broker.get("gross_exposure"))
    broker_portfolio = _to_float(broker.get("portfolio_value"))
    broker_cash = _to_float(broker.get("cash"))
    unrealized_pnl = _to_float(broker.get("unrealized_pnl"))

    exposure_drift = round(system_allocated - broker_exposure, 2)
    cash_drift = round(system_available - broker_cash, 2) if broker_cash else round(system_available, 2)
    equity_drift = round(system_balance - broker_portfolio, 2) if broker_portfolio else round(system_balance, 2)

    status = "aligned"
    blockers = []
    warnings = []

    if not profile.get("linked"):
        status = "unlinked"
        blockers.append("user_broker_profile_not_linked")
    if not broker.get("connected"):
        status = "broker_disconnected"
        blockers.append("broker_not_connected")
    if abs(exposure_drift) > 1.0:
        status = "drift"
        warnings.append("allocated_vs_broker_exposure_mismatch")
    if broker_portfolio and abs(equity_drift) > 1.0:
        status = "drift"
        warnings.append("ledger_vs_broker_equity_mismatch")

    payload = {
        "email": email,
        "status": status,
        "last_run_at": int(time.time()),
        "profile": profile,
        "system": {
            "balance": round(system_balance, 2),
            "available": round(system_available, 2),
            "allocated": round(system_allocated, 2),
            "performance": current,
            "series_points": len(series),
        },
        "broker": broker,
        "drift": {
            "allocated_vs_broker_exposure": exposure_drift,
            "available_vs_broker_cash": cash_drift,
            "balance_vs_broker_equity": equity_drift,
            "unrealized_pnl": round(unrealized_pnl, 2),
        },
        "blockers": blockers,
        "warnings": warnings,
    }
    _save_recon(email, payload)
    return payload

@router.post("/api/user-broker/link")
def user_broker_link(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    profile = _load_profile(email)
    profile["linked"] = True
    profile["broker"] = (payload.get("broker") or "alpaca").strip().lower()
    if payload.get("paper") is not None:
        profile["paper"] = bool(payload.get("paper"))
    broker = _alpaca_snapshot()
    profile["account_id"] = broker.get("account_id") or profile.get("account_id")
    _save_profile(email, profile)
    recon = _build_reconciliation(email)
    return {"status": "linked", "profile": profile, "reconciliation": recon}

@router.post("/api/user-broker/unlink")
def user_broker_unlink():
    session = _require_user()
    email = session.get("email")
    profile = _load_profile(email)
    profile["linked"] = False
    _save_profile(email, profile)
    recon = _build_reconciliation(email)
    return {"status": "unlinked", "profile": profile, "reconciliation": recon}

@router.get("/api/user-broker/status")
def user_broker_status():
    session = _require_user()
    email = session.get("email")
    profile = _load_profile(email)
    broker = _alpaca_snapshot()
    return {"profile": profile, "broker": broker}

@router.get("/api/user-reconciliation")
def user_reconciliation():
    session = _require_user()
    email = session.get("email")
    return _build_reconciliation(email)

@router.post("/api/user-reconciliation/run")
def user_reconciliation_run():
    session = _require_user()
    email = session.get("email")
    return _build_reconciliation(email)

@router.post("/api/user-reconciliation/sync-from-broker")
def user_reconciliation_sync_from_broker():
    session = _require_user()
    email = session.get("email")
    mu = _multi()
    ledger = mu._load_ledger(email)
    broker = _alpaca_snapshot()
    if not broker.get("connected"):
        raise HTTPException(status_code=400, detail="Broker not connected")
    gross_exposure = _to_float(broker.get("gross_exposure"))
    portfolio_value = _to_float(broker.get("portfolio_value"))
    cash = _to_float(broker.get("cash"))
    ledger["allocated"] = round(gross_exposure, 2)
    if portfolio_value > 0:
        ledger["balance"] = round(portfolio_value, 2)
    if cash > 0:
        ledger["available"] = round(cash, 2)
    ledger.setdefault("history", []).insert(0, {
        "type": "broker_sync",
        "amount": round(portfolio_value, 2),
        "timestamp": int(time.time())
    })
    saved = mu._save_ledger(email, ledger)
    current, series = mu._perf_snapshot(email, saved)
    recon = _build_reconciliation(email)
    return {"status": "synced", "capital": saved, "performance": current, "series_points": len(series), "reconciliation": recon}
