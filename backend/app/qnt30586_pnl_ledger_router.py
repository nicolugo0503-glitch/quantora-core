from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["pnl-ledger"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
PNL_DIR = ARTIFACTS_DIR / "investor_pnl_ledger"

def _main():
    from backend.app import main as app_main
    return app_main

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _attrib():
    from backend.app import qnt30585_trade_attribution_router as attrib
    return attrib

def _safe(value: str) -> str:
    return hashlib.sha256((value or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _path(email: str) -> Path:
    PNL_DIR.mkdir(parents=True, exist_ok=True)
    return PNL_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _require_admin():
    return _main().require_admin()

def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {
            "email": email,
            "positions": [],
            "ledger": [],
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

def _find_position(data: dict, sleeve_id: str, symbol: str):
    return next((p for p in data.get("positions", []) if p.get("sleeve_id") == sleeve_id and p.get("symbol") == symbol), None)

@router.get("/api/pnl-ledger")
def pnl_ledger():
    session = _require_user()
    return _load(session.get("email"))

@router.post("/api/pnl-ledger/mark")
def pnl_mark(payload: dict = Body(...)):
    _require_admin()
    email = (payload.get("email") or "").strip().lower()
    sleeve_id = (payload.get("sleeve_id") or "").strip()
    symbol = (payload.get("symbol") or "").strip().upper()
    mark_price = round(float(payload.get("mark_price") or 0.0), 6)
    qty = round(float(payload.get("qty") or 0.0), 6)
    avg_price = round(float(payload.get("avg_price") or 0.0), 6)
    if not email or not sleeve_id or not symbol or mark_price <= 0 or qty < 0 or avg_price <= 0:
        raise HTTPException(status_code=400, detail="email, sleeve_id, symbol, qty, avg_price, mark_price required")
    data = _load(email)
    pos = _find_position(data, sleeve_id, symbol)
    unrealized = round((mark_price - avg_price) * qty, 2)
    if not pos:
        pos = {
            "position_id": f"pos_{int(time.time())}",
            "sleeve_id": sleeve_id,
            "symbol": symbol,
            "qty": qty,
            "avg_price": avg_price,
            "mark_price": mark_price,
            "realized_pnl": 0.0,
            "unrealized_pnl": unrealized,
            "updated_at": int(time.time()),
        }
        data.setdefault("positions", []).append(pos)
    else:
        pos["qty"] = qty
        pos["avg_price"] = avg_price
        pos["mark_price"] = mark_price
        pos["unrealized_pnl"] = unrealized
        pos["updated_at"] = int(time.time())
    data.setdefault("ledger", []).insert(0, {
        "entry_id": f"pnl_{int(time.time())}",
        "type": "mark_update",
        "sleeve_id": sleeve_id,
        "symbol": symbol,
        "qty": qty,
        "avg_price": avg_price,
        "mark_price": mark_price,
        "realized_pnl": round(float(pos.get("realized_pnl", 0.0)), 2),
        "unrealized_pnl": unrealized,
        "timestamp": int(time.time()),
    })
    data["ledger"] = data["ledger"][:1000]
    _save(email, data)
    return {"status": "marked", "position": pos}

@router.post("/api/pnl-ledger/realize")
def pnl_realize(payload: dict = Body(...)):
    _require_admin()
    email = (payload.get("email") or "").strip().lower()
    sleeve_id = (payload.get("sleeve_id") or "").strip()
    symbol = (payload.get("symbol") or "").strip().upper()
    realized_pnl = round(float(payload.get("realized_pnl") or 0.0), 2)
    if not email or not sleeve_id or not symbol:
        raise HTTPException(status_code=400, detail="email, sleeve_id, symbol required")
    data = _load(email)
    pos = _find_position(data, sleeve_id, symbol)
    if not pos:
        raise HTTPException(status_code=404, detail="position not found")
    pos["realized_pnl"] = round(float(pos.get("realized_pnl", 0.0)) + realized_pnl, 2)
    pos["updated_at"] = int(time.time())
    data.setdefault("ledger", []).insert(0, {
        "entry_id": f"pnl_{int(time.time())}",
        "type": "realized_update",
        "sleeve_id": sleeve_id,
        "symbol": symbol,
        "realized_pnl": realized_pnl,
        "cumulative_realized_pnl": pos["realized_pnl"],
        "timestamp": int(time.time()),
    })
    data["ledger"] = data["ledger"][:1000]
    _save(email, data)
    return {"status": "realized", "position": pos}

@router.get("/api/pnl-ledger/summary")
def pnl_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    positions = data.get("positions", [])
    total_realized = round(sum(float(p.get("realized_pnl", 0.0)) for p in positions), 2)
    total_unrealized = round(sum(float(p.get("unrealized_pnl", 0.0)) for p in positions), 2)
    sleeve_rollup = {}
    for p in positions:
        sid = p.get("sleeve_id")
        item = sleeve_rollup.setdefault(sid, {
            "sleeve_id": sid,
            "positions": 0,
            "realized_pnl": 0.0,
            "unrealized_pnl": 0.0,
        })
        item["positions"] += 1
        item["realized_pnl"] = round(item["realized_pnl"] + float(p.get("realized_pnl", 0.0)), 2)
        item["unrealized_pnl"] = round(item["unrealized_pnl"] + float(p.get("unrealized_pnl", 0.0)), 2)
    return {
        "email": email,
        "position_count": len(positions),
        "total_realized_pnl": total_realized,
        "total_unrealized_pnl": total_unrealized,
        "sleeves": list(sleeve_rollup.values()),
        "positions": positions,
        "ledger": data.get("ledger", [])[:200],
    }
