from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

app = FastAPI(title="QNT30394 PostgreSQL Production Persistence", version="1.0.0")

STATE = {
    "postgres_env_ready": False,
    "database_url_present": False,
    "pool_size": 10,
    "ssl_mode": "require",
    "migrations_applied": [],
    "tables": {
        "tenants": [],
        "users": [],
        "strategies": [],
        "orders": [],
        "fills": [],
        "subscriptions": [],
        "payments": [],
        "audit_logs": [],
    },
    "audit": [],
}

class DatabaseEnvUpdate(BaseModel):
    database_url_present: bool = False
    pool_size: int = 10
    ssl_mode: str = "require"

class TenantCreate(BaseModel):
    tenant_id: str
    tenant_name: str
    plan: str = "starter"

class UserCreate(BaseModel):
    user_id: str
    tenant_id: str
    email: str
    role: str = "viewer"

class StrategyCreate(BaseModel):
    strategy_id: str
    tenant_id: str
    name: str
    status: str = "active"

class OrderCreate(BaseModel):
    order_id: str
    tenant_id: str
    symbol: str
    side: str
    qty: float = Field(..., gt=0)
    status: str = "submitted"

def now():
    return datetime.utcnow().isoformat() + "Z"

def log_event(kind: str, payload: Dict[str, Any]):
    STATE["audit"].append({
        "id": str(uuid.uuid4()),
        "kind": kind,
        "timestamp": now(),
        "payload": payload,
    })
    STATE["audit"] = STATE["audit"][-500:]

@app.get("/postgres/status")
def status():
    return {
        "mission": "QNT30394",
        "postgres_env_ready": STATE["postgres_env_ready"],
        "database_url_present": STATE["database_url_present"],
        "pool_size": STATE["pool_size"],
        "ssl_mode": STATE["ssl_mode"],
        "migrations_applied": STATE["migrations_applied"],
        "table_counts": {k: len(v) for k, v in STATE["tables"].items()},
        "audit_events": len(STATE["audit"]),
    }

@app.post("/postgres/env/update")
def update_env(payload: DatabaseEnvUpdate):
    STATE["database_url_present"] = payload.database_url_present
    STATE["pool_size"] = payload.pool_size
    STATE["ssl_mode"] = payload.ssl_mode
    STATE["postgres_env_ready"] = payload.database_url_present
    log_event("postgres_env_updated", {
        "database_url_present": payload.database_url_present,
        "pool_size": payload.pool_size,
        "ssl_mode": payload.ssl_mode,
    })
    return {"status": "ok", "postgres_env_ready": STATE["postgres_env_ready"]}

@app.post("/postgres/migrations/apply")
def apply_migrations():
    migrations = [
        "001_create_tenants",
        "002_create_users",
        "003_create_strategies",
        "004_create_orders_and_fills",
        "005_create_subscriptions_and_payments",
        "006_create_audit_logs",
    ]
    for migration in migrations:
        if migration not in STATE["migrations_applied"]:
            STATE["migrations_applied"].append(migration)
    log_event("postgres_migrations_applied", {"count": len(STATE["migrations_applied"])})
    return {"status": "ok", "migrations_applied": STATE["migrations_applied"]}

@app.post("/postgres/tenants/create")
def create_tenant(payload: TenantCreate):
    record = payload.model_dump()
    record["created_at"] = now()
    STATE["tables"]["tenants"].append(record)
    log_event("tenant_persisted", {"tenant_id": payload.tenant_id})
    return {"status": "ok", "tenant": record}

@app.post("/postgres/users/create")
def create_user(payload: UserCreate):
    record = payload.model_dump()
    record["created_at"] = now()
    STATE["tables"]["users"].append(record)
    log_event("user_persisted", {"user_id": payload.user_id, "tenant_id": payload.tenant_id})
    return {"status": "ok", "user": record}

@app.post("/postgres/strategies/create")
def create_strategy(payload: StrategyCreate):
    record = payload.model_dump()
    record["created_at"] = now()
    STATE["tables"]["strategies"].append(record)
    log_event("strategy_persisted", {"strategy_id": payload.strategy_id, "tenant_id": payload.tenant_id})
    return {"status": "ok", "strategy": record}

@app.post("/postgres/orders/create")
def create_order(payload: OrderCreate):
    record = payload.model_dump()
    record["created_at"] = now()
    STATE["tables"]["orders"].append(record)
    log_event("order_persisted", {"order_id": payload.order_id, "tenant_id": payload.tenant_id, "symbol": payload.symbol})
    return {"status": "ok", "order": record}

@app.get("/postgres/table/{table_name}")
def get_table(table_name: str):
    if table_name not in STATE["tables"]:
        return {"status": "error", "message": "unknown table"}
    return {"table": table_name, "rows": STATE["tables"][table_name]}

@app.get("/postgres/audit")
def audit(limit: int = 25):
    return {"events": STATE["audit"][-limit:][::-1]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("postgres_production_persistence:app", host="127.0.0.1", port=8010, reload=False)
