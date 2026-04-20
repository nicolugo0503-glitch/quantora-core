from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["portfolio-allocation"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ALLOC_DIR = ARTIFACTS_DIR / "portfolio_allocation_engine"

DEFAULT_STRATEGIES = [
    {"strategy_id": "strat_trend", "name": "Trend Engine", "status": "active"},
    {"strategy_id": "strat_meanrev", "name": "Mean Reversion", "status": "active"},
    {"strategy_id": "strat_macro", "name": "Macro Overlay", "status": "active"},
    {"strategy_id": "strat_cash", "name": "Cash Reserve", "status": "active"},
]

def _main():
    from backend.app import main as app_main
    return app_main

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _nav():
    from backend.app import qnt30582_nav_registry_router as nav
    return nav

def _safe(value: str) -> str:
    return hashlib.sha256((value or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _path(email: str) -> Path:
    ALLOC_DIR.mkdir(parents=True, exist_ok=True)
    return ALLOC_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _require_admin():
    return _main().require_admin()

def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {
            "email": email,
            "strategies": [{**s, "target_pct": 0.0, "allocated_amount": 0.0} for s in DEFAULT_STRATEGIES],
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

def _find_strategy(data: dict, strategy_id: str):
    return next((s for s in data.get("strategies", []) if s.get("strategy_id") == strategy_id), None)

def _total_nav(email: str) -> float:
    nav_data = _nav()._load(email)
    return round(sum(float(x.get("nav", 0.0)) for x in nav_data.get("allocations", [])), 2)

def _recompute_amounts(data: dict, total_nav: float):
    for s in data.get("strategies", []):
        target_pct = float(s.get("target_pct", 0.0))
        s["allocated_amount"] = round(total_nav * (target_pct / 100.0), 2)
    return data

@router.get("/api/portfolio-allocation")
def portfolio_allocation():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    nav = _total_nav(email)
    data = _recompute_amounts(data, nav)
    _save(email, data)
    return data

@router.post("/api/portfolio-allocation/weights")
def portfolio_allocation_weights(payload: dict = Body(...)):
    _require_admin()
    email = (payload.get("email") or "").strip().lower()
    weights = payload.get("weights") or []
    if not email or not isinstance(weights, list) or not weights:
        raise HTTPException(status_code=400, detail="email and weights required")
    data = _load(email)
    total = round(sum(float(x.get("target_pct") or 0.0) for x in weights), 4)
    if total > 100.0001:
        raise HTTPException(status_code=400, detail="Total target_pct cannot exceed 100")
    for w in weights:
        strategy_id = (w.get("strategy_id") or "").strip()
        strat = _find_strategy(data, strategy_id)
        if not strat:
            continue
        strat["target_pct"] = round(float(w.get("target_pct") or 0.0), 4)
    nav = _total_nav(email)
    data = _recompute_amounts(data, nav)
    data.setdefault("history", []).insert(0, {
        "type": "weights_updated",
        "timestamp": int(time.time()),
        "total_nav": nav,
        "weights": [{"strategy_id": s["strategy_id"], "target_pct": s["target_pct"]} for s in data.get("strategies", [])],
    })
    data["history"] = data["history"][:200]
    _save(email, data)
    return {"status": "updated", "total_nav": nav, "strategies": data.get("strategies", [])}

@router.post("/api/portfolio-allocation/rebalance")
def portfolio_allocation_rebalance(payload: dict = Body(None)):
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    nav = _total_nav(email)
    data = _recompute_amounts(data, nav)
    data.setdefault("history", []).insert(0, {
        "type": "rebalance",
        "timestamp": int(time.time()),
        "total_nav": nav,
        "note": (payload or {}).get("note", ""),
    })
    data["history"] = data["history"][:200]
    _save(email, data)
    return {"status": "rebalanced", "total_nav": nav, "strategies": data.get("strategies", [])}

@router.get("/api/portfolio-allocation/summary")
def portfolio_allocation_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    nav = _total_nav(email)
    data = _recompute_amounts(data, nav)
    _save(email, data)
    allocated = round(sum(float(s.get("allocated_amount", 0.0)) for s in data.get("strategies", [])), 2)
    free_nav = round(nav - allocated, 2)
    return {
        "email": email,
        "total_nav": nav,
        "allocated_nav": allocated,
        "unallocated_nav": free_nav,
        "strategy_count": len(data.get("strategies", [])),
        "strategies": data.get("strategies", []),
        "history": data.get("history", [])[:50],
    }
