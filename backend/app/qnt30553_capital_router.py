import json
import time
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

try:
    from backend.app.qnt30555_performance_router import snapshot as performance_snapshot
except Exception:
    def performance_snapshot():
        return None

router = APIRouter(prefix="/api/capital", tags=["capital"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
LEDGER_FILE = ARTIFACTS_DIR / "capital_ledger.json"


class AmountRequest(BaseModel):
    amount: float = Field(gt=0)


def _default_ledger() -> Dict[str, Any]:
    return {
        "account_id": "master",
        "balance": 100000.0,
        "available": 100000.0,
        "allocated": 0.0,
        "currency": "USD",
        "history": [
            {
                "type": "seed",
                "amount": 100000.0,
                "timestamp": int(time.time()),
                "note": "initial system balance"
            }
        ]
    }


def _ensure():
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    if not LEDGER_FILE.exists():
        LEDGER_FILE.write_text(json.dumps(_default_ledger(), indent=2), encoding="utf-8")


def _load() -> Dict[str, Any]:
    _ensure()
    return json.loads(LEDGER_FILE.read_text(encoding="utf-8"))


def _save(data: Dict[str, Any]) -> Dict[str, Any]:
    data["balance"] = round(float(data.get("balance", 0.0)), 2)
    data["available"] = round(float(data.get("available", 0.0)), 2)
    data["allocated"] = round(float(data.get("allocated", 0.0)), 2)
    LEDGER_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def _append(data: Dict[str, Any], entry: Dict[str, Any]) -> None:
    history = data.setdefault("history", [])
    history.insert(0, entry)


@router.get("")
def get_capital():
    data = _load()
    return {
        "account_id": data.get("account_id", "master"),
        "balance": round(float(data.get("balance", 0.0)), 2),
        "available": round(float(data.get("available", 0.0)), 2),
        "allocated": round(float(data.get("allocated", 0.0)), 2),
        "currency": data.get("currency", "USD"),
        "history_count": len(data.get("history", [])),
    }


@router.get("/ledger")
def get_ledger():
    return _load()


@router.post("/deposit")
def deposit(payload: AmountRequest):
    data = _load()
    amount = round(float(payload.amount), 2)
    data["balance"] = float(data.get("balance", 0.0)) + amount
    data["available"] = float(data.get("available", 0.0)) + amount
    _append(data, {"type": "deposit", "amount": amount, "timestamp": int(time.time())})
    return _save(data)


@router.post("/withdraw")
def withdraw(payload: AmountRequest):
    data = _load()
    amount = round(float(payload.amount), 2)
    available = float(data.get("available", 0.0))
    if amount > available:
        raise HTTPException(status_code=400, detail="insufficient available balance")
    data["balance"] = float(data.get("balance", 0.0)) - amount
    data["available"] = available - amount
    _append(data, {"type": "withdraw", "amount": amount, "timestamp": int(time.time())})
    return _save(data)


@router.post("/allocate")
def allocate(payload: AmountRequest):
    data = _load()
    amount = round(float(payload.amount), 2)
    available = float(data.get("available", 0.0))
    if amount > available:
        raise HTTPException(status_code=400, detail="insufficient available balance")
    data["available"] = available - amount
    data["allocated"] = float(data.get("allocated", 0.0)) + amount
    _append(data, {"type": "allocate", "amount": amount, "timestamp": int(time.time())})
    return _save(data)


@router.post("/deallocate")
def deallocate(payload: AmountRequest):
    data = _load()
    amount = round(float(payload.amount), 2)
    allocated = float(data.get("allocated", 0.0))
    if amount > allocated:
        raise HTTPException(status_code=400, detail="insufficient allocated balance")
    data["allocated"] = allocated - amount
    data["available"] = float(data.get("available", 0.0)) + amount
    _append(data, {"type": "deallocate", "amount": amount, "timestamp": int(time.time())})
    return _save(data)
