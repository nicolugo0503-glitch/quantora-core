from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["equalization-series-accounting"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
EQ_DIR = ARTIFACTS_DIR / "investor_equalization_series"

def _main():
    from backend.app import main as app_main
    return app_main

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _nav():
    from backend.app import qnt30582_nav_registry_router as nav
    return nav

def _cash():
    from backend.app import qnt30591_cash_ledger_router as cash
    return cash

def _safe(value: str) -> str:
    return hashlib.sha256((value or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _path(email: str) -> Path:
    EQ_DIR.mkdir(parents=True, exist_ok=True)
    return EQ_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _require_admin():
    return _main().require_admin()

def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {
            "email": email,
            "series": [],
            "history": [],
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

def _total_nav(email: str) -> float:
    nav_data = _nav()._load(email)
    return round(sum(float(x.get("nav", 0.0)) for x in nav_data.get("allocations", [])), 2)

def _cash_processed(email: str) -> float:
    cash_data = _cash()._load(email)
    return round(sum(float(e.get("amount", 0.0)) for e in cash_data.get("entries", []) if e.get("status") == "processed"), 2)

def _find_series(data: dict, series_id: str):
    return next((s for s in data.get("series", []) if s.get("series_id") == series_id), None)

def _recompute_series(data: dict, email: str) -> dict:
    total_nav = _total_nav(email)
    processed_cash = _cash_processed(email)
    base_capital = round(total_nav + processed_cash, 2)
    total_units = round(sum(float(s.get("units", 0.0)) for s in data.get("series", [])), 6)
    nav_per_unit = round(base_capital / total_units, 6) if total_units > 0 else 0.0
    for s in data.get("series", []):
        units = round(float(s.get("units", 0.0)), 6)
        capital = round(units * nav_per_unit, 2) if nav_per_unit > 0 else round(float(s.get("subscription_capital", 0.0)), 2)
        s["series_nav"] = capital
        s["nav_per_unit"] = nav_per_unit
        s["equalization_credit"] = round(capital - float(s.get("subscription_capital", 0.0)), 2)
    return data

@router.get("/api/equalization-series")
def equalization_series():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    data = _recompute_series(data, email)
    _save(email, data)
    return data

@router.post("/api/equalization-series/create")
def equalization_series_create(payload: dict = Body(...)):
    _require_admin()
    email = (payload.get("email") or "").strip().lower()
    series_name = (payload.get("series_name") or "").strip()
    subscription_capital = round(float(payload.get("subscription_capital") or 0.0), 2)
    units = round(float(payload.get("units") or 0.0), 6)
    if not email or not series_name or subscription_capital <= 0 or units <= 0:
        raise HTTPException(status_code=400, detail="email, series_name, positive subscription_capital and units required")
    data = _load(email)
    item = {
        "series_id": f"series_{int(time.time())}",
        "series_name": series_name,
        "subscription_capital": subscription_capital,
        "units": units,
        "series_nav": subscription_capital,
        "nav_per_unit": round(subscription_capital / units, 6),
        "equalization_credit": 0.0,
        "status": "active",
        "created_at": int(time.time()),
        "closed_at": None,
        "notes": (payload.get("notes") or "").strip(),
    }
    data.setdefault("series", []).insert(0, item)
    data.setdefault("history", []).insert(0, {
        "type": "series_created",
        "series_id": item["series_id"],
        "series_name": item["series_name"],
        "timestamp": int(time.time()),
    })
    data["history"] = data["history"][:500]
    data = _recompute_series(data, email)
    _save(email, data)
    return {"status": "created", "series": item}

@router.post("/api/equalization-series/close")
def equalization_series_close(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    series_id = (payload.get("series_id") or "").strip()
    data = _load(email)
    item = _find_series(data, series_id)
    if not item:
        raise HTTPException(status_code=404, detail="series not found")
    item["status"] = "closed"
    item["closed_at"] = int(time.time())
    if payload.get("notes"):
        item["notes"] = str(payload.get("notes"))
    data.setdefault("history", []).insert(0, {
        "type": "series_closed",
        "series_id": series_id,
        "timestamp": int(time.time()),
    })
    data["history"] = data["history"][:500]
    _save(email, data)
    return {"status": "closed", "series": item}

@router.get("/api/equalization-series/summary")
def equalization_series_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    data = _recompute_series(data, email)
    _save(email, data)
    active = sum(1 for s in data.get("series", []) if s.get("status") == "active")
    closed = sum(1 for s in data.get("series", []) if s.get("status") == "closed")
    total_capital = round(sum(float(s.get("subscription_capital", 0.0)) for s in data.get("series", [])), 2)
    total_nav = round(sum(float(s.get("series_nav", 0.0)) for s in data.get("series", [])), 2)
    total_credit = round(sum(float(s.get("equalization_credit", 0.0)) for s in data.get("series", [])), 2)
    nav_per_unit = round(float(data.get("series", [])[0].get("nav_per_unit", 0.0)), 6) if data.get("series") else 0.0
    return {
        "email": email,
        "series_count": len(data.get("series", [])),
        "active_series": active,
        "closed_series": closed,
        "total_subscription_capital": total_capital,
        "total_series_nav": total_nav,
        "total_equalization_credit": total_credit,
        "nav_per_unit": nav_per_unit,
        "series": data.get("series", [])[:200],
        "history": data.get("history", [])[:100],
    }
