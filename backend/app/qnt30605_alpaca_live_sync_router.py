from fastapi import APIRouter, Body
from pathlib import Path
import json, time, hashlib, os

router = APIRouter(tags=["alpaca-live-sync"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
SYNC_DIR = ARTIFACTS_DIR / "alpaca_live_state_sync"

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _threeway():
    from backend.app import qnt30604_threeway_reconciliation_router as threeway
    return threeway

def _broker():
    from backend.app import qnt30603_broker_reconciliation_router as broker
    return broker

def _safe(value: str) -> str:
    return hashlib.sha256((value or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _path(email: str) -> Path:
    SYNC_DIR.mkdir(parents=True, exist_ok=True)
    return SYNC_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {
            "email": email,
            "sync_runs": [],
            "latest_live_state": {
                "cash": 0.0,
                "positions": [],
                "source": "none",
                "updated_at": None,
                "is_live_connected": False,
            },
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

def _env_connected() -> bool:
    return bool(os.getenv("ALPACA_API_KEY") and os.getenv("ALPACA_SECRET_KEY"))

def _mock_live_state():
    return {
        "cash": 100000.00,
        "positions": [
            {"symbol": "AAPL", "qty": 10.0, "price": 185.25, "market_value": 1852.50},
            {"symbol": "TSLA", "qty": 5.0, "price": 240.10, "market_value": 1200.50},
        ],
        "source": "mock_live_sync",
        "updated_at": int(time.time()),
        "is_live_connected": False,
    }

def _normalize_live_state(payload: dict):
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
    return {
        "cash": cash,
        "positions": positions,
        "source": str(payload.get("source") or "manual_import"),
        "updated_at": int(time.time()),
        "is_live_connected": bool(payload.get("is_live_connected", False)),
    }

@router.get("/api/alpaca-sync")
def alpaca_sync():
    session = _require_user()
    return _load(session.get("email"))

@router.post("/api/alpaca-sync/import")
def alpaca_sync_import(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    live_state = _normalize_live_state(payload)
    data["latest_live_state"] = live_state
    _save(email, data)

    broker_data = _broker()._load(email)
    broker_state_trades = []
    for idx, p in enumerate(live_state.get("positions", []), start=1):
        broker_state_trades.append({
            "broker_trade_id": f"livepos_{int(time.time())}_{idx}",
            "symbol": p["symbol"],
            "side": "buy",
            "qty": p["qty"],
            "price": p["price"],
            "broker": "alpaca",
            "timestamp": int(time.time()),
            "notes": "generated from imported live state",
        })
    if broker_state_trades:
        broker_data["broker_trades"] = broker_state_trades + broker_data.get("broker_trades", [])
        broker_data["broker_trades"] = broker_data["broker_trades"][:1000]
        _broker()._save(email, broker_data)

    threeway = _threeway()._load(email)
    threeway["broker_state"] = {
        "cash": live_state["cash"],
        "positions": live_state["positions"],
        "updated_at": live_state["updated_at"],
    }
    _threeway()._save(email, threeway)

    return {"status": "imported", "live_state": live_state}

@router.post("/api/alpaca-sync/run")
def alpaca_sync_run(payload: dict = Body(None)):
    session = _require_user()
    email = session.get("email")
    data = _load(email)

    if payload and payload.get("cash") is not None:
        live_state = _normalize_live_state(payload)
        sync_source = "manual_payload"
    else:
        live_state = _mock_live_state()
        live_state["is_live_connected"] = _env_connected()
        live_state["source"] = "alpaca_live_env" if live_state["is_live_connected"] else "mock_live_sync"
        sync_source = live_state["source"]

    data["latest_live_state"] = live_state

    threeway = _threeway()._load(email)
    threeway["broker_state"] = {
        "cash": live_state["cash"],
        "positions": live_state["positions"],
        "updated_at": live_state["updated_at"],
    }
    _threeway()._save(email, threeway)

    run = {
        "sync_id": f"sync_{int(time.time())}",
        "timestamp": int(time.time()),
        "source": sync_source,
        "is_live_connected": live_state["is_live_connected"],
        "cash": live_state["cash"],
        "position_count": len(live_state["positions"]),
        "status": "synced",
    }
    data.setdefault("sync_runs", []).insert(0, run)
    data["sync_runs"] = data["sync_runs"][:200]
    _save(email, data)
    return {"status": "synced", "run": run, "live_state": live_state}

@router.get("/api/alpaca-sync/summary")
def alpaca_sync_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    latest = data.get("latest_live_state", {})
    runs = data.get("sync_runs", [])
    return {
        "email": email,
        "sync_run_count": len(runs),
        "latest_live_state": latest,
        "latest_run": runs[0] if runs else None,
        "is_live_connected": bool(latest.get("is_live_connected")),
        "position_count": len(latest.get("positions", [])),
        "runs": runs[:50],
    }
