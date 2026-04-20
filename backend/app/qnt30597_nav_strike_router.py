from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["nav-strike-valuation-registry"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
NAV_DIR = ARTIFACTS_DIR / "investor_nav_strike_registry"

def _main():
    from backend.app import main as app_main
    return app_main

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _rollforward():
    from backend.app import qnt30594_rollforward_router as rf
    return rf

def _dealing():
    from backend.app import qnt30596_dealing_day_router as dd
    return dd

def _safe(value: str) -> str:
    return hashlib.sha256((value or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _path(email: str) -> Path:
    NAV_DIR.mkdir(parents=True, exist_ok=True)
    return NAV_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _require_admin():
    return _main().require_admin()

def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {"email": email, "valuations": [], "created_at": int(time.time()), "updated_at": int(time.time())}
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))

def _save(email: str, data: dict) -> dict:
    data["updated_at"] = int(time.time())
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data

def _build_valuation(email: str, valuation_date: str):
    rf_data = _rollforward()._load(email)
    if not rf_data.get("periods"):
        period = _rollforward()._build_period(email, "Current Period Rollforward")
        rf_data.setdefault("periods", []).insert(0, period)
        _rollforward()._save(email, rf_data)
    latest_period = rf_data["periods"][0]

    dd_data = _dealing()._load(email)
    latest_day = (dd_data.get("dealing_days") or [None])[0]

    official_nav = round(float(latest_period.get("ending_nav", 0.0)), 2)
    return {
        "valuation_id": f"val_{int(time.time())}",
        "valuation_date": valuation_date,
        "official_nav": official_nav,
        "opening_capital": round(float(latest_period.get("opening_capital", 0.0)), 2),
        "rollforward_change": round(float(latest_period.get("net_rollforward_change", 0.0)), 2),
        "equalization_total": round(float(latest_period.get("equalization_total", 0.0)), 2),
        "dealing_day_id": latest_day.get("day_id") if latest_day else None,
        "cutoff_status": latest_day.get("cutoff_status") if latest_day else None,
        "status": "draft",
        "struck_at": int(time.time()),
        "finalized_at": None,
        "notes": "",
    }

@router.get("/api/nav-strike")
def nav_strike():
    session = _require_user()
    return _load(session.get("email"))

@router.post("/api/nav-strike/strike")
def nav_strike_create(payload: dict = Body(None)):
    session = _require_user()
    email = session.get("email")
    valuation_date = ((payload or {}).get("valuation_date") or "current").strip()
    data = _load(email)
    item = _build_valuation(email, valuation_date)
    data.setdefault("valuations", []).insert(0, item)
    data["valuations"] = data["valuations"][:120]
    _save(email, data)
    return {"status": "struck", "valuation": item}

@router.post("/api/nav-strike/finalize")
def nav_strike_finalize(payload: dict = Body(...)):
    _require_admin()
    email = (payload.get("email") or "").strip().lower()
    valuation_id = (payload.get("valuation_id") or "").strip()
    if not email or not valuation_id:
        raise HTTPException(status_code=400, detail="email and valuation_id required")
    data = _load(email)
    item = next((v for v in data.get("valuations", []) if v.get("valuation_id") == valuation_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="valuation not found")
    item["status"] = "official"
    item["finalized_at"] = int(time.time())
    if payload.get("notes"):
        item["notes"] = str(payload.get("notes"))
    _save(email, data)
    return {"status": "official", "valuation": item}

@router.get("/api/nav-strike/summary")
def nav_strike_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    if not data.get("valuations"):
        item = _build_valuation(email, "current")
        data.setdefault("valuations", []).insert(0, item)
        _save(email, data)
    latest = data["valuations"][0]
    official = sum(1 for v in data.get("valuations", []) if v.get("status") == "official")
    draft = sum(1 for v in data.get("valuations", []) if v.get("status") == "draft")
    return {
        "email": email,
        "valuation_count": len(data.get("valuations", [])),
        "official_count": official,
        "draft_count": draft,
        "latest_valuation": latest,
        "valuations": data.get("valuations", [])[:50],
    }
