from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["performance-waterfall"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
WF_DIR = ARTIFACTS_DIR / "investor_performance_waterfall"

DEFAULT_FEE_CONFIG = {
    "management_fee_pct": 2.0,
    "performance_fee_pct": 20.0,
    "hurdle_rate_pct": 0.0,
}

def _main():
    from backend.app import main as app_main
    return app_main

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _pnl():
    from backend.app import qnt30586_pnl_ledger_router as pnl
    return pnl

def _safe(value: str) -> str:
    return hashlib.sha256((value or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _path(email: str) -> Path:
    WF_DIR.mkdir(parents=True, exist_ok=True)
    return WF_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _require_admin():
    return _main().require_admin()

def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {
            "email": email,
            "fee_config": DEFAULT_FEE_CONFIG.copy(),
            "snapshots": [],
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

def _build_snapshot(email: str, fee_config: dict) -> dict:
    pnl_summary = _pnl().pnl_summary.__wrapped__ if hasattr(_pnl().pnl_summary, "__wrapped__") else None
    pnl_data = _pnl()._load(email)
    positions = pnl_data.get("positions", [])
    gross_realized = round(sum(float(p.get("realized_pnl", 0.0)) for p in positions), 2)
    gross_unrealized = round(sum(float(p.get("unrealized_pnl", 0.0)) for p in positions), 2)
    gross_total = round(gross_realized + gross_unrealized, 2)

    mgmt_fee = round(gross_total * (float(fee_config.get("management_fee_pct", 0.0)) / 100.0), 2) if gross_total > 0 else 0.0
    hurdle_rate_pct = float(fee_config.get("hurdle_rate_pct", 0.0))
    hurdle_value = round(gross_total * (hurdle_rate_pct / 100.0), 2) if gross_total > 0 else 0.0
    eligible_perf_base = max(0.0, gross_total - hurdle_value)
    perf_fee = round(eligible_perf_base * (float(fee_config.get("performance_fee_pct", 0.0)) / 100.0), 2) if eligible_perf_base > 0 else 0.0
    net_after_fees = round(gross_total - mgmt_fee - perf_fee, 2)

    return {
        "snapshot_id": f"wf_{int(time.time())}",
        "timestamp": int(time.time()),
        "gross_realized_pnl": gross_realized,
        "gross_unrealized_pnl": gross_unrealized,
        "gross_total_pnl": gross_total,
        "management_fee_pct": round(float(fee_config.get("management_fee_pct", 0.0)), 4),
        "performance_fee_pct": round(float(fee_config.get("performance_fee_pct", 0.0)), 4),
        "hurdle_rate_pct": round(hurdle_rate_pct, 4),
        "management_fee_value": mgmt_fee,
        "performance_fee_value": perf_fee,
        "net_pnl_after_fees": net_after_fees,
    }

@router.get("/api/performance-waterfall")
def performance_waterfall():
    session = _require_user()
    return _load(session.get("email"))

@router.post("/api/performance-waterfall/fees")
def performance_waterfall_fees(payload: dict = Body(...)):
    _require_admin()
    email = (payload.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="email required")
    data = _load(email)
    cfg = data.get("fee_config", DEFAULT_FEE_CONFIG.copy())
    for key in ["management_fee_pct", "performance_fee_pct", "hurdle_rate_pct"]:
        if key in payload:
            cfg[key] = round(float(payload.get(key) or 0.0), 4)
    data["fee_config"] = cfg
    _save(email, data)
    return {"status": "updated", "fee_config": cfg}

@router.post("/api/performance-waterfall/calculate")
def performance_waterfall_calculate(payload: dict = Body(None)):
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    snap = _build_snapshot(email, data.get("fee_config", DEFAULT_FEE_CONFIG.copy()))
    data.setdefault("snapshots", []).insert(0, snap)
    data["snapshots"] = data["snapshots"][:200]
    _save(email, data)
    return {"status": "calculated", "snapshot": snap}

@router.get("/api/performance-waterfall/summary")
def performance_waterfall_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    if not data.get("snapshots"):
        snap = _build_snapshot(email, data.get("fee_config", DEFAULT_FEE_CONFIG.copy()))
        data.setdefault("snapshots", []).insert(0, snap)
        _save(email, data)
    latest = data["snapshots"][0]
    return {
        "email": email,
        "fee_config": data.get("fee_config", DEFAULT_FEE_CONFIG.copy()),
        "latest_snapshot": latest,
        "snapshot_count": len(data.get("snapshots", [])),
        "snapshots": data.get("snapshots", [])[:50],
    }
