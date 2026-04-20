from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["statement-pack"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
PACK_DIR = ARTIFACTS_DIR / "investor_statement_packs"

def _main():
    from backend.app import main as app_main
    return app_main

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _reporting():
    from backend.app import qnt30564_reporting_router as reporting
    return reporting

def _waterfall():
    from backend.app import qnt30587_waterfall_router as waterfall
    return waterfall

def _pnl():
    from backend.app import qnt30586_pnl_ledger_router as pnl
    return pnl

def _safe(value: str) -> str:
    return hashlib.sha256((value or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _path(email: str) -> Path:
    PACK_DIR.mkdir(parents=True, exist_ok=True)
    return PACK_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _require_admin():
    return _main().require_admin()

def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {
            "email": email,
            "packs": [],
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

def _latest_statement(email: str):
    store = _reporting()._load_statement_store(email)
    return (store.get("statements") or [None])[0]

def _latest_waterfall(email: str):
    wf = _waterfall()._load(email)
    snaps = wf.get("snapshots") or []
    if snaps:
        return snaps[0]
    snap = _waterfall()._build_snapshot(email, wf.get("fee_config", {}))
    wf.setdefault("snapshots", []).insert(0, snap)
    _waterfall()._save(email, wf)
    return snap

def _pnl_summary(email: str):
    pnl = _pnl()._load(email)
    positions = pnl.get("positions", [])
    return {
        "position_count": len(positions),
        "total_realized_pnl": round(sum(float(p.get("realized_pnl", 0.0)) for p in positions), 2),
        "total_unrealized_pnl": round(sum(float(p.get("unrealized_pnl", 0.0)) for p in positions), 2),
    }

def _build_pack(email: str) -> dict:
    statement = _latest_statement(email)
    waterfall = _latest_waterfall(email)
    pnl = _pnl_summary(email)
    return {
        "pack_id": f"pack_{int(time.time())}",
        "generated_at": int(time.time()),
        "email": email,
        "title": "Investor Statement Pack",
        "statement": statement,
        "waterfall": waterfall,
        "pnl_summary": pnl,
        "sections": [
            {"name": "Investor Statement", "status": "included"},
            {"name": "Performance Waterfall", "status": "included"},
            {"name": "PnL Summary", "status": "included"},
        ],
        "delivery_status": "generated",
    }

@router.get("/api/statement-packs")
def statement_packs():
    session = _require_user()
    return _load(session.get("email"))

@router.post("/api/statement-packs/generate")
def statement_packs_generate(payload: dict = Body(None)):
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    pack = _build_pack(email)
    if payload and payload.get("title"):
        pack["title"] = str(payload.get("title"))
    data.setdefault("packs", []).insert(0, pack)
    data["packs"] = data["packs"][:100]
    _save(email, data)
    return {"status": "generated", "pack": pack, "total_packs": len(data["packs"])}

@router.post("/api/statement-packs/deliver")
def statement_packs_deliver(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    pack_id = payload.get("pack_id")
    channel = (payload.get("channel") or "portal_simulated").strip().lower()
    data = _load(email)
    pack = next((p for p in data.get("packs", []) if p.get("pack_id") == pack_id), None)
    if not pack:
        raise HTTPException(status_code=404, detail="pack not found")
    pack["delivery_status"] = "delivered_simulated"
    pack["delivery_channel"] = channel
    pack["delivered_at"] = int(time.time())
    _save(email, data)
    return {"status": "delivered", "pack": pack}

@router.get("/api/statement-packs/summary")
def statement_packs_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    if not data.get("packs"):
        pack = _build_pack(email)
        data.setdefault("packs", []).insert(0, pack)
        _save(email, data)
    latest = data["packs"][0]
    delivered = sum(1 for p in data.get("packs", []) if str(p.get("delivery_status")) == "delivered_simulated")
    return {
        "email": email,
        "pack_count": len(data.get("packs", [])),
        "delivered_count": delivered,
        "latest_pack": latest,
        "packs": data.get("packs", [])[:50],
    }
