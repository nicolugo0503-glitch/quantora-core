from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["trade-attribution"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ATTR_DIR = ARTIFACTS_DIR / "trade_attribution_by_sleeve"

def _main():
    from backend.app import main as app_main
    return app_main

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _sleeves():
    from backend.app import qnt30584_strategy_sleeve_execution_router as sleeves
    return sleeves

def _safe(value: str) -> str:
    return hashlib.sha256((value or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _path(email: str) -> Path:
    ATTR_DIR.mkdir(parents=True, exist_ok=True)
    return ATTR_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _require_admin():
    return _main().require_admin()

def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {"email": email, "trades": [], "created_at": int(time.time()), "updated_at": int(time.time())}
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))

def _save(email: str, data: dict) -> dict:
    data["updated_at"] = int(time.time())
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data

@router.get("/api/trade-attribution")
def trade_attribution():
    session = _require_user()
    return _load(session.get("email"))

@router.post("/api/trade-attribution/trade")
def trade_attribution_add(payload: dict = Body(...)):
    _require_admin()
    email = (payload.get("email") or "").strip().lower()
    sleeve_id = (payload.get("sleeve_id") or "").strip()
    symbol = (payload.get("symbol") or "").strip().upper()
    side = (payload.get("side") or "").strip().lower()
    qty = round(float(payload.get("qty") or 0.0), 6)
    price = round(float(payload.get("price") or 0.0), 6)
    pnl = round(float(payload.get("pnl") or 0.0), 2)
    if not email or not sleeve_id or not symbol or side not in {"buy","sell"} or qty <= 0 or price <= 0:
        raise HTTPException(status_code=400, detail="email, sleeve_id, symbol, side, qty, price required")
    data = _load(email)
    sleeve_data = _sleeves()._load(email)
    sleeve = next((s for s in sleeve_data.get("sleeves", []) if s.get("sleeve_id") == sleeve_id), None)
    if not sleeve:
        raise HTTPException(status_code=404, detail="sleeve not found")
    trade = {
        "trade_id": f"trd_{int(time.time())}",
        "sleeve_id": sleeve_id,
        "strategy_name": sleeve.get("strategy_name"),
        "symbol": symbol,
        "side": side,
        "qty": qty,
        "price": price,
        "notional": round(qty * price, 2),
        "pnl": pnl,
        "timestamp": int(time.time()),
    }
    data.setdefault("trades", []).insert(0, trade)
    data["trades"] = data["trades"][:1000]
    _save(email, data)
    return {"status": "recorded", "trade": trade}

@router.get("/api/trade-attribution/summary")
def trade_attribution_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    trades = data.get("trades", [])
    total_notional = round(sum(float(t.get("notional", 0.0)) for t in trades), 2)
    total_pnl = round(sum(float(t.get("pnl", 0.0)) for t in trades), 2)
    sleeve_rollup = {}
    for t in trades:
        sid = t.get("sleeve_id")
        item = sleeve_rollup.setdefault(sid, {
            "sleeve_id": sid,
            "strategy_name": t.get("strategy_name"),
            "trade_count": 0,
            "notional": 0.0,
            "pnl": 0.0,
        })
        item["trade_count"] += 1
        item["notional"] = round(item["notional"] + float(t.get("notional", 0.0)), 2)
        item["pnl"] = round(item["pnl"] + float(t.get("pnl", 0.0)), 2)
    return {
        "email": email,
        "trade_count": len(trades),
        "total_notional": total_notional,
        "total_pnl": total_pnl,
        "sleeves": list(sleeve_rollup.values()),
        "trades": trades[:200],
    }
