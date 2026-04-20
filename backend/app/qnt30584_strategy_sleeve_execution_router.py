from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["strategy-sleeve-execution"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
SLEEVE_DIR = ARTIFACTS_DIR / "strategy_sleeve_execution_registry"

def _main():
    from backend.app import main as app_main
    return app_main

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _alloc():
    from backend.app import qnt30583_portfolio_allocation_router as alloc
    return alloc

def _safe(value: str) -> str:
    return hashlib.sha256((value or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _path(email: str) -> Path:
    SLEEVE_DIR.mkdir(parents=True, exist_ok=True)
    return SLEEVE_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _require_admin():
    return _main().require_admin()

def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {
            "email": email,
            "sleeves": [],
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

def _find_sleeve(data: dict, sleeve_id: str):
    return next((s for s in data.get("sleeves", []) if s.get("sleeve_id") == sleeve_id), None)

def _bootstrap_from_allocations(email: str, data: dict) -> dict:
    if data.get("sleeves"):
        return data
    alloc_summary = _alloc().portfolio_allocation_summary.__wrapped__ if hasattr(_alloc().portfolio_allocation_summary, "__wrapped__") else None
    alloc_data = _alloc()._load(email)
    nav = _alloc()._total_nav(email)
    alloc_data = _alloc()._recompute_amounts(alloc_data, nav)
    for strat in alloc_data.get("strategies", []):
        data.setdefault("sleeves", []).append({
            "sleeve_id": f"sleeve_{strat.get('strategy_id')}",
            "strategy_id": strat.get("strategy_id"),
            "strategy_name": strat.get("name"),
            "target_pct": round(float(strat.get("target_pct", 0.0)), 4),
            "allocated_amount": round(float(strat.get("allocated_amount", 0.0)), 2),
            "execution_status": "not_deployed",
            "deployed_amount": 0.0,
            "last_execution_at": None,
        })
    return data

@router.get("/api/strategy-sleeves")
def strategy_sleeves():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    data = _bootstrap_from_allocations(email, data)
    _save(email, data)
    return data

@router.post("/api/strategy-sleeves/deploy")
def strategy_sleeves_deploy(payload: dict = Body(...)):
    _require_admin()
    email = (payload.get("email") or "").strip().lower()
    sleeve_id = (payload.get("sleeve_id") or "").strip()
    deployed_amount = round(float(payload.get("deployed_amount") or 0.0), 2)
    if not email or not sleeve_id or deployed_amount < 0:
        raise HTTPException(status_code=400, detail="email, sleeve_id, deployed_amount required")
    data = _load(email)
    data = _bootstrap_from_allocations(email, data)
    sleeve = _find_sleeve(data, sleeve_id)
    if not sleeve:
        raise HTTPException(status_code=404, detail="sleeve not found")
    sleeve["deployed_amount"] = deployed_amount
    sleeve["execution_status"] = "deployed" if deployed_amount > 0 else "not_deployed"
    sleeve["last_execution_at"] = int(time.time())
    data.setdefault("history", []).insert(0, {
        "type": "deploy",
        "sleeve_id": sleeve_id,
        "deployed_amount": deployed_amount,
        "timestamp": int(time.time()),
    })
    data["history"] = data["history"][:200]
    _save(email, data)
    return {"status": sleeve["execution_status"], "sleeve": sleeve}

@router.post("/api/strategy-sleeves/sync")
def strategy_sleeves_sync(payload: dict = Body(None)):
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    alloc_data = _alloc()._load(email)
    nav = _alloc()._total_nav(email)
    alloc_data = _alloc()._recompute_amounts(alloc_data, nav)
    existing = {s.get("strategy_id"): s for s in data.get("sleeves", [])}
    new_sleeves = []
    for strat in alloc_data.get("strategies", []):
        s = existing.get(strat.get("strategy_id"), {
            "sleeve_id": f"sleeve_{strat.get('strategy_id')}",
            "strategy_id": strat.get("strategy_id"),
            "strategy_name": strat.get("name"),
            "execution_status": "not_deployed",
            "deployed_amount": 0.0,
            "last_execution_at": None,
        })
        s["target_pct"] = round(float(strat.get("target_pct", 0.0)), 4)
        s["allocated_amount"] = round(float(strat.get("allocated_amount", 0.0)), 2)
        new_sleeves.append(s)
    data["sleeves"] = new_sleeves
    data.setdefault("history", []).insert(0, {
        "type": "sync",
        "timestamp": int(time.time()),
        "note": (payload or {}).get("note", "synced from allocation engine"),
    })
    data["history"] = data["history"][:200]
    _save(email, data)
    return {"status": "synced", "sleeves": data.get("sleeves", [])}

@router.get("/api/strategy-sleeves/summary")
def strategy_sleeves_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    data = _bootstrap_from_allocations(email, data)
    _save(email, data)
    target_alloc = round(sum(float(s.get("allocated_amount", 0.0)) for s in data.get("sleeves", [])), 2)
    deployed = round(sum(float(s.get("deployed_amount", 0.0)) for s in data.get("sleeves", [])), 2)
    undeployed = round(target_alloc - deployed, 2)
    return {
        "email": email,
        "sleeve_count": len(data.get("sleeves", [])),
        "target_allocated_amount": target_alloc,
        "deployed_amount": deployed,
        "undeployed_amount": undeployed,
        "sleeves": data.get("sleeves", []),
        "history": data.get("history", [])[:50],
    }
