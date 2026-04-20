from fastapi import APIRouter, Body
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["broker-reconciliation-bridge"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
BROKER_DIR = ARTIFACTS_DIR / "broker_reconciliation_bridge"

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _attrib():
    from backend.app import qnt30585_trade_attribution_router as attrib
    return attrib

def _audit():
    from backend.app import qnt30602_audit_trail_router as audit
    return audit

def _safe(value: str) -> str:
    return hashlib.sha256((value or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _path(email: str) -> Path:
    BROKER_DIR.mkdir(parents=True, exist_ok=True)
    return BROKER_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {
            "email": email,
            "broker_trades": [],
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

def _internal_trades(email: str):
    data = _attrib()._load(email)
    return data.get("trades", [])

def _match_key(trade: dict):
    return (
        str(trade.get("symbol") or "").upper(),
        str(trade.get("side") or "").lower(),
        round(float(trade.get("qty") or 0.0), 6),
        round(float(trade.get("price") or 0.0), 6),
    )

def _run_match(email: str):
    data = _load(email)
    internal = _internal_trades(email)
    broker = data.get("broker_trades", [])

    internal_keys = [_match_key(t) for t in internal]
    broker_keys = [_match_key(t) for t in broker]

    matched = []
    missing_in_broker = []
    unexpected_broker = []

    used_broker_idx = set()

    for trade in internal:
        key = _match_key(trade)
        found_idx = None
        for idx, b in enumerate(broker):
            if idx in used_broker_idx:
                continue
            if _match_key(b) == key:
                found_idx = idx
                break
        if found_idx is not None:
            used_broker_idx.add(found_idx)
            matched.append({
                "internal_trade_id": trade.get("trade_id"),
                "broker_trade_id": broker[found_idx].get("broker_trade_id"),
                "symbol": trade.get("symbol"),
                "side": trade.get("side"),
                "qty": trade.get("qty"),
                "price": trade.get("price"),
            })
        else:
            missing_in_broker.append({
                "internal_trade_id": trade.get("trade_id"),
                "symbol": trade.get("symbol"),
                "side": trade.get("side"),
                "qty": trade.get("qty"),
                "price": trade.get("price"),
            })

    for idx, b in enumerate(broker):
        if idx not in used_broker_idx:
            unexpected_broker.append({
                "broker_trade_id": b.get("broker_trade_id"),
                "symbol": b.get("symbol"),
                "side": b.get("side"),
                "qty": b.get("qty"),
                "price": b.get("price"),
            })

    status = "matched" if not missing_in_broker and not unexpected_broker else "breaks_detected"

    run = {
        "run_id": f"brokerrec_{int(time.time())}",
        "timestamp": int(time.time()),
        "status": status,
        "internal_trade_count": len(internal),
        "broker_trade_count": len(broker),
        "matched_count": len(matched),
        "missing_in_broker_count": len(missing_in_broker),
        "unexpected_broker_count": len(unexpected_broker),
        "matched": matched[:200],
        "missing_in_broker": missing_in_broker[:200],
        "unexpected_broker": unexpected_broker[:200],
    }
    return run

@router.get("/api/broker-reconciliation")
def broker_reconciliation():
    session = _require_user()
    return _load(session.get("email"))

@router.post("/api/broker-reconciliation/add-broker-trade")
def add_broker_trade(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    trade = {
        "broker_trade_id": str(payload.get("broker_trade_id") or f"alpaca_{int(time.time())}"),
        "symbol": str(payload.get("symbol") or "").upper(),
        "side": str(payload.get("side") or "").lower(),
        "qty": round(float(payload.get("qty") or 0.0), 6),
        "price": round(float(payload.get("price") or 0.0), 6),
        "broker": str(payload.get("broker") or "alpaca").lower(),
        "timestamp": int(time.time()),
        "notes": str(payload.get("notes") or ""),
    }
    data.setdefault("broker_trades", []).insert(0, trade)
    data["broker_trades"] = data["broker_trades"][:1000]
    _save(email, data)
    return {"status": "added", "broker_trade": trade}

@router.post("/api/broker-reconciliation/run")
def run_broker_reconciliation(payload: dict = Body(None)):
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    run = _run_match(email)
    if payload and payload.get("notes"):
        run["notes"] = str(payload.get("notes"))
    data.setdefault("runs", []).insert(0, run)
    data["runs"] = data["runs"][:200]
    _save(email, data)

    try:
        _audit()._append_record(email, "broker_reconciliation_run", {
            "run_id": run["run_id"],
            "status": run["status"],
            "matched_count": run["matched_count"],
            "missing_in_broker_count": run["missing_in_broker_count"],
            "unexpected_broker_count": run["unexpected_broker_count"],
        })
    except Exception:
        pass

    return {"status": run["status"], "run": run, "total_runs": len(data["runs"])}

@router.get("/api/broker-reconciliation/summary")
def broker_reconciliation_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    if not data.get("runs"):
        run = _run_match(email)
        data.setdefault("runs", []).insert(0, run)
        _save(email, data)
    latest = data["runs"][0]
    matched_runs = sum(1 for r in data.get("runs", []) if r.get("status") == "matched")
    break_runs = sum(1 for r in data.get("runs", []) if r.get("status") == "breaks_detected")
    return {
        "email": email,
        "run_count": len(data.get("runs", [])),
        "matched_run_count": matched_runs,
        "break_run_count": break_runs,
        "broker_trade_count": len(data.get("broker_trades", [])),
        "latest_run": latest,
        "runs": data.get("runs", [])[:50],
    }
