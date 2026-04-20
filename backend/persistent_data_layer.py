from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import os
import threading
import uuid

app = FastAPI(title="QNT30389 Persistent Data Layer and State Durability", version="1.0.0")

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_FILE = os.path.join(DATA_DIR, "quantora_state.json")
lock = threading.Lock()

DEFAULT_DB = {
    "meta": {
        "schema_version": "1.0.0",
        "created_at": None,
        "updated_at": None,
        "last_backup_at": None,
    },
    "tenants": {},
    "users": {},
    "strategies": {},
    "trades": {},
    "allocations": {},
    "subscriptions": {},
    "invoices": {},
    "audit": [],
}

def now():
    return datetime.utcnow().isoformat() + "Z"

def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)

def init_db():
    ensure_data_dir()
    if not os.path.exists(DB_FILE):
        db = DEFAULT_DB.copy()
        db["meta"] = dict(DEFAULT_DB["meta"])
        db["meta"]["created_at"] = now()
        db["meta"]["updated_at"] = now()
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=2)
    return load_db()

def load_db():
    ensure_data_dir()
    if not os.path.exists(DB_FILE):
        return init_db()
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(db):
    db["meta"]["updated_at"] = now()
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2)

def audit(db, kind: str, payload: Dict[str, Any]):
    db["audit"].append({
        "id": str(uuid.uuid4()),
        "kind": kind,
        "timestamp": now(),
        "payload": payload,
    })
    db["audit"] = db["audit"][-1000:]

class TenantRecord(BaseModel):
    tenant_id: str
    tenant_name: str
    plan: str = "starter"
    status: str = "active"
    metadata: Optional[Dict[str, Any]] = None

class UserRecord(BaseModel):
    user_id: str
    tenant_id: str
    full_name: str
    email: str
    role: str = "viewer"
    status: str = "active"
    metadata: Optional[Dict[str, Any]] = None

class StrategyRecord(BaseModel):
    strategy_id: str
    tenant_id: str
    realized_pnl: float = 0.0
    sharpe: float = 0.0
    drawdown: float = 0.0
    win_rate: float = Field(0.0, ge=0.0, le=1.0)
    active: bool = True
    metadata: Optional[Dict[str, Any]] = None

class TradeRecord(BaseModel):
    trade_id: str
    tenant_id: str
    strategy_id: str
    symbol: str
    side: str
    qty: float = Field(..., gt=0)
    entry_price: float = Field(..., gt=0)
    exit_price: float = Field(..., gt=0)
    fees: float = 0.0
    metadata: Optional[Dict[str, Any]] = None

class AllocationRecord(BaseModel):
    allocation_id: str
    tenant_id: str
    strategy_id: str
    capital: float = Field(..., ge=0.0)
    weight: float = Field(..., ge=0.0)
    status: str = "active"

class SubscriptionRecord(BaseModel):
    subscription_id: str
    tenant_id: str
    customer_name: str
    plan: str
    monthly_price: float = Field(..., ge=0.0)
    status: str = "active"

class InvoiceRecord(BaseModel):
    invoice_id: str
    tenant_id: str
    amount: float = Field(..., ge=0.0)
    currency: str = "USD"
    status: str = "issued"

@app.on_event("startup")
def startup_event():
    init_db()

@app.get("/data-layer/status")
def status():
    with lock:
        db = load_db()
        return {
            "mission": "QNT30389",
            "db_file": DB_FILE,
            "schema_version": db["meta"]["schema_version"],
            "updated_at": db["meta"]["updated_at"],
            "counts": {
                "tenants": len(db["tenants"]),
                "users": len(db["users"]),
                "strategies": len(db["strategies"]),
                "trades": len(db["trades"]),
                "allocations": len(db["allocations"]),
                "subscriptions": len(db["subscriptions"]),
                "invoices": len(db["invoices"]),
                "audit": len(db["audit"]),
            }
        }

@app.post("/data-layer/tenant/upsert")
def upsert_tenant(payload: TenantRecord):
    with lock:
        db = load_db()
        record = payload.model_dump()
        record["updated_at"] = now()
        db["tenants"][payload.tenant_id] = record
        audit(db, "tenant_upserted", {"tenant_id": payload.tenant_id})
        save_db(db)
        return {"status": "ok", "tenant": record}

@app.post("/data-layer/user/upsert")
def upsert_user(payload: UserRecord):
    with lock:
        db = load_db()
        if payload.tenant_id not in db["tenants"]:
            return {"status": "error", "message": "tenant not found"}
        record = payload.model_dump()
        record["updated_at"] = now()
        db["users"][payload.user_id] = record
        audit(db, "user_upserted", {"user_id": payload.user_id, "tenant_id": payload.tenant_id})
        save_db(db)
        return {"status": "ok", "user": record}

@app.post("/data-layer/strategy/upsert")
def upsert_strategy(payload: StrategyRecord):
    with lock:
        db = load_db()
        if payload.tenant_id not in db["tenants"]:
            return {"status": "error", "message": "tenant not found"}
        record = payload.model_dump()
        record["updated_at"] = now()
        db["strategies"][payload.strategy_id] = record
        audit(db, "strategy_upserted", {"strategy_id": payload.strategy_id, "tenant_id": payload.tenant_id})
        save_db(db)
        return {"status": "ok", "strategy": record}

@app.post("/data-layer/trade/upsert")
def upsert_trade(payload: TradeRecord):
    with lock:
        db = load_db()
        if payload.tenant_id not in db["tenants"]:
            return {"status": "error", "message": "tenant not found"}
        if payload.strategy_id not in db["strategies"]:
            return {"status": "error", "message": "strategy not found"}
        record = payload.model_dump()
        record["updated_at"] = now()
        db["trades"][payload.trade_id] = record
        audit(db, "trade_upserted", {"trade_id": payload.trade_id, "strategy_id": payload.strategy_id})
        save_db(db)
        return {"status": "ok", "trade": record}

@app.post("/data-layer/allocation/upsert")
def upsert_allocation(payload: AllocationRecord):
    with lock:
        db = load_db()
        if payload.tenant_id not in db["tenants"]:
            return {"status": "error", "message": "tenant not found"}
        if payload.strategy_id not in db["strategies"]:
            return {"status": "error", "message": "strategy not found"}
        record = payload.model_dump()
        record["updated_at"] = now()
        db["allocations"][payload.allocation_id] = record
        audit(db, "allocation_upserted", {"allocation_id": payload.allocation_id, "strategy_id": payload.strategy_id})
        save_db(db)
        return {"status": "ok", "allocation": record}

@app.post("/data-layer/subscription/upsert")
def upsert_subscription(payload: SubscriptionRecord):
    with lock:
        db = load_db()
        if payload.tenant_id not in db["tenants"]:
            return {"status": "error", "message": "tenant not found"}
        record = payload.model_dump()
        record["updated_at"] = now()
        db["subscriptions"][payload.subscription_id] = record
        audit(db, "subscription_upserted", {"subscription_id": payload.subscription_id, "tenant_id": payload.tenant_id})
        save_db(db)
        return {"status": "ok", "subscription": record}

@app.post("/data-layer/invoice/upsert")
def upsert_invoice(payload: InvoiceRecord):
    with lock:
        db = load_db()
        if payload.tenant_id not in db["tenants"]:
            return {"status": "error", "message": "tenant not found"}
        record = payload.model_dump()
        record["updated_at"] = now()
        db["invoices"][payload.invoice_id] = record
        audit(db, "invoice_upserted", {"invoice_id": payload.invoice_id, "tenant_id": payload.tenant_id})
        save_db(db)
        return {"status": "ok", "invoice": record}

@app.get("/data-layer/export")
def export_state():
    with lock:
        db = load_db()
        audit(db, "state_exported", {"counts": {k: len(v) if isinstance(v, dict) else len(v) for k, v in db.items() if k != "meta"}})
        save_db(db)
        return db

@app.post("/data-layer/import")
def import_state(payload: Dict[str, Any]):
    with lock:
        current = load_db()
        incoming = DEFAULT_DB.copy()
        incoming["meta"] = dict(DEFAULT_DB["meta"])
        for key in DEFAULT_DB.keys():
            if key in payload:
                incoming[key] = payload[key]
        incoming["meta"]["created_at"] = current["meta"].get("created_at") or now()
        incoming["meta"]["updated_at"] = now()
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(incoming, f, indent=2)
        db = load_db()
        audit(db, "state_imported", {"schema_version": db["meta"]["schema_version"]})
        save_db(db)
        return {"status": "ok", "meta": db["meta"]}

@app.post("/data-layer/backup/create")
def create_backup():
    with lock:
        db = load_db()
        backup_name = f"quantora_backup_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.json"
        backup_path = os.path.join(DATA_DIR, backup_name)
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=2)
        db["meta"]["last_backup_at"] = now()
        audit(db, "backup_created", {"backup_file": backup_name})
        save_db(db)
        return {"status": "ok", "backup_file": backup_name, "backup_path": backup_path}

@app.get("/data-layer/records/{collection}")
def list_records(collection: str):
    with lock:
        db = load_db()
        if collection not in ["tenants", "users", "strategies", "trades", "allocations", "subscriptions", "invoices"]:
            return {"status": "error", "message": "unknown collection"}
        return {"collection": collection, "records": list(db[collection].values())}

@app.get("/data-layer/audit")
def get_audit(limit: int = 25):
    with lock:
        db = load_db()
        return {"events": db["audit"][-limit:][::-1]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("persistent_data_layer:app", host="127.0.0.1", port=8010, reload=False)
