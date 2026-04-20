import json
import time
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter

router = APIRouter(prefix="/api/performance-history", tags=["performance-history"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
LEDGER_FILE = ARTIFACTS_DIR / "capital_ledger.json"
HISTORY_FILE = ARTIFACTS_DIR / "performance_history.json"


def _default_ledger() -> Dict[str, Any]:
    now = int(time.time())
    return {
        "account_id": "master",
        "balance": 100000.0,
        "available": 100000.0,
        "allocated": 0.0,
        "currency": "USD",
        "history": [
            {"type": "seed", "amount": 100000.0, "timestamp": now, "note": "initial system balance"}
        ],
    }


def _default_history() -> Dict[str, Any]:
    now = int(time.time())
    return {
        "series": [
            {
                "timestamp": now,
                "balance": 100000.0,
                "available": 100000.0,
                "allocated": 0.0,
                "net_flow": 100000.0,
                "net_invested_capital": 100000.0,
                "pnl_value": 0.0,
                "return_pct": 0.0,
            }
        ]
    }


def _ensure() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    if not LEDGER_FILE.exists():
        LEDGER_FILE.write_text(json.dumps(_default_ledger(), indent=2), encoding="utf-8")
    if not HISTORY_FILE.exists():
        HISTORY_FILE.write_text(json.dumps(_default_history(), indent=2), encoding="utf-8")


def _read_json(path: Path, fallback: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def _load_ledger() -> Dict[str, Any]:
    _ensure()
    return _read_json(LEDGER_FILE, _default_ledger())


def _load_history() -> Dict[str, Any]:
    _ensure()
    return _read_json(HISTORY_FILE, _default_history())


def _save_history(data: Dict[str, Any]) -> Dict[str, Any]:
    HISTORY_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def _compute_net_flow(ledger: Dict[str, Any]) -> float:
    total = 0.0
    for entry in ledger.get("history", []):
        typ = (entry.get("type") or "").lower()
        amt = float(entry.get("amount") or 0.0)
        if typ in {"seed", "deposit"}:
            total += amt
        elif typ == "withdraw":
            total -= amt
    return round(total, 2)


def _round_snapshot(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    for key in ["balance", "available", "allocated", "net_flow", "net_invested_capital", "pnl_value", "return_pct"]:
        snapshot[key] = round(float(snapshot.get(key) or 0.0), 2)
    snapshot["timestamp"] = int(snapshot.get("timestamp") or time.time())
    return snapshot


def generate_snapshot() -> Dict[str, Any]:
    ledger = _load_ledger()
    net_flow = _compute_net_flow(ledger)
    balance = float(ledger.get("balance") or 0.0)
    available = float(ledger.get("available") or 0.0)
    allocated = float(ledger.get("allocated") or 0.0)
    pnl_value = balance - net_flow
    return_pct = 0.0 if abs(net_flow) < 1e-9 else (pnl_value / net_flow) * 100.0
    return _round_snapshot(
        {
            "timestamp": int(time.time()),
            "balance": balance,
            "available": available,
            "allocated": allocated,
            "net_flow": net_flow,
            "net_invested_capital": net_flow,
            "pnl_value": pnl_value,
            "return_pct": return_pct,
        }
    )


def _append_snapshot(series: List[Dict[str, Any]], snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
    if series:
        prev = series[-1]
        same_shape = (
            round(float(prev.get("balance") or 0.0), 2) == round(float(snapshot.get("balance") or 0.0), 2)
            and round(float(prev.get("available") or 0.0), 2) == round(float(snapshot.get("available") or 0.0), 2)
            and round(float(prev.get("allocated") or 0.0), 2) == round(float(snapshot.get("allocated") or 0.0), 2)
            and round(float(prev.get("net_flow") or 0.0), 2) == round(float(snapshot.get("net_flow") or 0.0), 2)
        )
        if same_shape:
            series[-1] = snapshot
            return series
    series.append(snapshot)
    return series[-500:]


@router.get("/summary")
def summary():
    snapshot = generate_snapshot()
    return {
        "status": "ok",
        "current": snapshot,
        "series_points": len(_load_history().get("series", [])),
    }


@router.get("/series")
def series():
    history = _load_history()
    current = generate_snapshot()
    rows = _append_snapshot(history.get("series", []), current)
    history["series"] = rows
    _save_history(history)
    return {
        "status": "ok",
        "series": rows,
        "current": current,
    }


@router.post("/snapshot")
def snapshot():
    history = _load_history()
    snap = generate_snapshot()
    rows = _append_snapshot(history.get("series", []), snap)
    history["series"] = rows
    _save_history(history)
    return {
        "status": "ok",
        "snapshot": snap,
        "series_points": len(rows),
    }


@router.get("/attribution")
def attribution():
    ledger = _load_ledger()
    history = _load_history().get("series", [])
    current = generate_snapshot()
    flows = {"deposits": 0.0, "withdrawals": 0.0, "allocations": 0.0, "deallocations": 0.0}
    counts = {"deposits": 0, "withdrawals": 0, "allocations": 0, "deallocations": 0}
    for entry in ledger.get("history", []):
        typ = (entry.get("type") or "").lower()
        amt = float(entry.get("amount") or 0.0)
        if typ == "deposit":
            flows["deposits"] += amt
            counts["deposits"] += 1
        elif typ == "withdraw":
            flows["withdrawals"] += amt
            counts["withdrawals"] += 1
        elif typ == "allocate":
            flows["allocations"] += amt
            counts["allocations"] += 1
        elif typ == "deallocate":
            flows["deallocations"] += amt
            counts["deallocations"] += 1
    return {
        "status": "ok",
        "current_balance": current["balance"],
        "net_invested_capital": current["net_invested_capital"],
        "pnl_value": current["pnl_value"],
        "return_pct": current["return_pct"],
        "series_points": len(history),
        "flow_breakdown": {k: round(v, 2) for k, v in flows.items()},
        "activity_counts": counts,
    }
