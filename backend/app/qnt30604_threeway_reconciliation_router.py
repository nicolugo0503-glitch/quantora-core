from fastapi import APIRouter, Body
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["three-way-reconciliation"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
THREEWAY_DIR = ARTIFACTS_DIR / "threeway_reconciliation"

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _broker():
    from backend.app import qnt30603_broker_reconciliation_router as broker
    return broker

def _attrib():
    from backend.app import qnt30585_trade_attribution_router as attrib
    return attrib

def _nav():
    from backend.app import qnt30597_nav_strike_router as nav
    return nav

def _safe(value: str) -> str:
    return hashlib.sha256((value or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _path(email: str) -> Path:
    THREEWAY_DIR.mkdir(parents=True, exist_ok=True)
    return THREEWAY_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {
            "email": email,
            "broker_state": {"cash": 0.0, "positions": [], "updated_at": None},
            "runs": [],
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

def _internal_positions_from_trades(email: str):
    trade_data = _attrib()._load(email)
    trades = trade_data.get("trades", [])
    pos = {}
    cash_effect = 0.0
    for t in trades:
        symbol = str(t.get("symbol") or "").upper()
        side = str(t.get("side") or "").lower()
        qty = float(t.get("qty") or 0.0)
        price = float(t.get("price") or 0.0)
        notional = round(qty * price, 2)
        current = pos.setdefault(symbol, {"symbol": symbol, "qty": 0.0, "last_price": price})
        if side == "buy":
            current["qty"] += qty
            cash_effect -= notional
        elif side == "sell":
            current["qty"] -= qty
            cash_effect += notional
        current["last_price"] = price
    positions = []
    for symbol, p in pos.items():
        qty = round(float(p["qty"]), 6)
        if abs(qty) < 1e-9:
            continue
        last_price = round(float(p["last_price"]), 6)
        market_value = round(qty * last_price, 2)
        positions.append({
            "symbol": symbol,
            "qty": qty,
            "price": last_price,
            "market_value": market_value,
        })
    positions.sort(key=lambda x: x["symbol"])
    return positions, round(cash_effect, 2)

def _official_nav(email: str) -> float:
    nav_data = _nav()._load(email)
    vals = nav_data.get("valuations") or []
    return round(float(vals[0].get("official_nav", 0.0)), 2) if vals else 0.0

def _positions_to_map(positions):
    out = {}
    for p in positions:
        out[str(p.get("symbol") or "").upper()] = {
            "qty": round(float(p.get("qty") or 0.0), 6),
            "price": round(float(p.get("price") or 0.0), 6),
            "market_value": round(float(p.get("market_value") or (float(p.get("qty") or 0.0) * float(p.get("price") or 0.0))), 2),
        }
    return out

def _run_reconciliation(email: str):
    data = _load(email)
    broker_state = data.get("broker_state", {})
    broker_cash = round(float(broker_state.get("cash") or 0.0), 2)
    broker_positions = broker_state.get("positions", []) or []

    internal_positions, internal_cash_effect = _internal_positions_from_trades(email)
    official_nav = _official_nav(email)

    internal_pos_map = _positions_to_map(internal_positions)
    broker_pos_map = _positions_to_map(broker_positions)

    breaks = []

    expected_cash = round(official_nav - sum(p["market_value"] for p in internal_positions), 2) if official_nav else round(internal_cash_effect, 2)
    cash_diff = round(expected_cash - broker_cash, 2)
    cash_ok = abs(cash_diff) < 0.01
    if not cash_ok:
        breaks.append({
            "code": "cash_mismatch",
            "severity": "high",
            "message": f"Expected cash {expected_cash} does not match broker cash {broker_cash}.",
            "difference": cash_diff,
        })

    position_breaks = []
    all_symbols = sorted(set(internal_pos_map.keys()) | set(broker_pos_map.keys()))
    for sym in all_symbols:
        ip = internal_pos_map.get(sym, {"qty": 0.0, "price": 0.0, "market_value": 0.0})
        bp = broker_pos_map.get(sym, {"qty": 0.0, "price": 0.0, "market_value": 0.0})
        qty_diff = round(ip["qty"] - bp["qty"], 6)
        mv_diff = round(ip["market_value"] - bp["market_value"], 2)
        if abs(qty_diff) >= 1e-6 or abs(mv_diff) >= 0.01:
            item = {
                "symbol": sym,
                "internal_qty": ip["qty"],
                "broker_qty": bp["qty"],
                "qty_difference": qty_diff,
                "internal_market_value": ip["market_value"],
                "broker_market_value": bp["market_value"],
                "market_value_difference": mv_diff,
            }
            position_breaks.append(item)
            breaks.append({
                "code": "position_mismatch",
                "severity": "high",
                "message": f"Position mismatch on {sym}.",
                "difference": mv_diff,
                "symbol": sym,
            })
    positions_ok = len(position_breaks) == 0

    internal_portfolio_value = round(sum(p["market_value"] for p in internal_positions) + expected_cash, 2)
    broker_portfolio_value = round(sum(float(p.get("market_value") or (float(p.get("qty") or 0.0) * float(p.get("price") or 0.0))) for p in broker_positions) + broker_cash, 2)
    nav_diff = round(official_nav - broker_portfolio_value, 2)
    nav_ok = abs(nav_diff) < 0.01 if official_nav else False
    if not nav_ok:
        breaks.append({
            "code": "nav_consistency_break",
            "severity": "high",
            "message": f"Official NAV {official_nav} does not match broker portfolio value {broker_portfolio_value}.",
            "difference": nav_diff,
        })

    run = {
        "run_id": f"threeway_{int(time.time())}",
        "timestamp": int(time.time()),
        "status": "clean" if len(breaks) == 0 else "breaks_detected",
        "break_count": len(breaks),
        "checks": {
            "cash": {
                "ok": cash_ok,
                "expected_cash": expected_cash,
                "broker_cash": broker_cash,
                "difference": cash_diff,
            },
            "positions": {
                "ok": positions_ok,
                "internal_position_count": len(internal_positions),
                "broker_position_count": len(broker_positions),
                "break_count": len(position_breaks),
                "breaks": position_breaks[:100],
            },
            "nav_consistency": {
                "ok": nav_ok,
                "official_nav": official_nav,
                "internal_portfolio_value": internal_portfolio_value,
                "broker_portfolio_value": broker_portfolio_value,
                "difference": nav_diff,
            },
        },
        "breaks": breaks[:200],
    }
    return run

@router.get("/api/threeway")
def threeway():
    session = _require_user()
    return _load(session.get("email"))

@router.post("/api/threeway/import-broker-state")
def import_broker_state(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    cash = round(float(payload.get("cash") or 0.0), 2)
    positions = []
    for p in payload.get("positions", []) or []:
        qty = round(float(p.get("qty") or 0.0), 6)
        price = round(float(p.get("price") or 0.0), 6)
        positions.append({
            "symbol": str(p.get("symbol") or "").upper(),
            "qty": qty,
            "price": price,
            "market_value": round(qty * price, 2),
        })
    data["broker_state"] = {
        "cash": cash,
        "positions": positions,
        "updated_at": int(time.time()),
    }
    _save(email, data)
    return {"status": "imported", "broker_state": data["broker_state"]}

@router.post("/api/threeway/run")
def run_threeway(payload: dict = Body(None)):
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    run = _run_reconciliation(email)
    if payload and payload.get("notes"):
        run["notes"] = str(payload.get("notes"))
    data.setdefault("runs", []).insert(0, run)
    data["runs"] = data["runs"][:200]
    _save(email, data)
    return {"status": run["status"], "run": run, "total_runs": len(data["runs"])}

@router.get("/api/threeway/summary")
def threeway_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    if not data.get("runs"):
        run = _run_reconciliation(email)
        data.setdefault("runs", []).insert(0, run)
        _save(email, data)
    latest = data["runs"][0]
    clean_runs = sum(1 for r in data.get("runs", []) if r.get("status") == "clean")
    break_runs = sum(1 for r in data.get("runs", []) if r.get("status") == "breaks_detected")
    return {
        "email": email,
        "run_count": len(data.get("runs", [])),
        "clean_run_count": clean_runs,
        "break_run_count": break_runs,
        "broker_state": data.get("broker_state", {}),
        "latest_run": latest,
        "runs": data.get("runs", [])[:50],
    }
