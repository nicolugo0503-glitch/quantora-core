from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["multi-series-nav-rollforward"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
RF_DIR = ARTIFACTS_DIR / "investor_multi_series_rollforward"

def _main():
    from backend.app import main as app_main
    return app_main

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _eq():
    from backend.app import qnt30593_equalization_router as eq
    return eq

def _safe(value: str) -> str:
    return hashlib.sha256((value or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _path(email: str) -> Path:
    RF_DIR.mkdir(parents=True, exist_ok=True)
    return RF_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _require_admin():
    return _main().require_admin()

def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {"email": email, "periods": [], "created_at": int(time.time()), "updated_at": int(time.time())}
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))

def _save(email: str, data: dict) -> dict:
    data["updated_at"] = int(time.time())
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data

def _build_period(email: str, period_name: str) -> dict:
    eq_data = _eq()._load(email)
    eq_data = _eq()._recompute_series(eq_data, email)
    series = eq_data.get("series", [])
    opening_capital = round(sum(float(s.get("subscription_capital", 0.0)) for s in series), 2)
    ending_nav = round(sum(float(s.get("series_nav", 0.0)) for s in series), 2)
    equalization = round(sum(float(s.get("equalization_credit", 0.0)) for s in series), 2)
    roll = []
    for s in series:
        roll.append({
            "series_id": s.get("series_id"),
            "series_name": s.get("series_name"),
            "opening_capital": round(float(s.get("subscription_capital", 0.0)), 2),
            "ending_nav": round(float(s.get("series_nav", 0.0)), 2),
            "equalization_credit": round(float(s.get("equalization_credit", 0.0)), 2),
            "units": round(float(s.get("units", 0.0)), 6),
            "nav_per_unit": round(float(s.get("nav_per_unit", 0.0)), 6),
            "status": s.get("status"),
        })
    return {
        "period_id": f"rf_{int(time.time())}",
        "period_name": period_name,
        "generated_at": int(time.time()),
        "opening_capital": opening_capital,
        "ending_nav": ending_nav,
        "equalization_total": equalization,
        "net_rollforward_change": round(ending_nav - opening_capital, 2),
        "series_count": len(roll),
        "series": roll,
    }

@router.get("/api/rollforward")
def rollforward():
    session = _require_user()
    return _load(session.get("email"))

@router.post("/api/rollforward/generate")
def rollforward_generate(payload: dict = Body(None)):
    session = _require_user()
    email = session.get("email")
    period_name = ((payload or {}).get("period_name") or "Current Period Rollforward").strip()
    data = _load(email)
    period = _build_period(email, period_name)
    data.setdefault("periods", []).insert(0, period)
    data["periods"] = data["periods"][:120]
    _save(email, data)
    return {"status": "generated", "period": period, "total_periods": len(data["periods"])}

@router.post("/api/rollforward/lock")
def rollforward_lock(payload: dict = Body(...)):
    _require_admin()
    email = (payload.get("email") or "").strip().lower()
    period_id = (payload.get("period_id") or "").strip()
    if not email or not period_id:
        raise HTTPException(status_code=400, detail="email and period_id required")
    data = _load(email)
    period = next((p for p in data.get("periods", []) if p.get("period_id") == period_id), None)
    if not period:
        raise HTTPException(status_code=404, detail="period not found")
    period["status"] = "locked"
    period["locked_at"] = int(time.time())
    _save(email, data)
    return {"status": "locked", "period": period}

@router.get("/api/rollforward/summary")
def rollforward_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    if not data.get("periods"):
        period = _build_period(email, "Current Period Rollforward")
        data.setdefault("periods", []).insert(0, period)
        _save(email, data)
    latest = data["periods"][0]
    locked = sum(1 for p in data.get("periods", []) if p.get("status") == "locked")
    return {
        "email": email,
        "period_count": len(data.get("periods", [])),
        "locked_count": locked,
        "latest_period": latest,
        "periods": data.get("periods", [])[:50],
    }
