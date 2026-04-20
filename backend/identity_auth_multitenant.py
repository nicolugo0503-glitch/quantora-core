from fastapi import FastAPI
from pydantic import BaseModel, Field, EmailStr
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid
import hashlib
import secrets

app = FastAPI(title="QNT30388 Identity, Auth, and Multi-Tenant Access Control", version="1.0.0")

STATE = {
    "tenants": {},
    "users": {},
    "roles": {
        "owner": ["tenant.read", "tenant.write", "users.manage", "billing.read", "billing.write", "trading.read", "trading.write", "ops.read"],
        "admin": ["tenant.read", "users.manage", "billing.read", "trading.read", "trading.write", "ops.read"],
        "analyst": ["tenant.read", "trading.read", "ops.read"],
        "viewer": ["tenant.read", "trading.read"],
    },
    "sessions": {},
    "api_keys": {},
    "audit": [],
}

class TenantCreate(BaseModel):
    tenant_id: str
    tenant_name: str
    plan: str = "starter"
    status: str = "active"
    metadata: Optional[Dict[str, Any]] = None

class UserCreate(BaseModel):
    user_id: str
    tenant_id: str
    full_name: str
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: str = "viewer"
    status: str = "active"
    metadata: Optional[Dict[str, Any]] = None

class LoginRequest(BaseModel):
    tenant_id: str
    email: EmailStr
    password: str

class InviteRequest(BaseModel):
    tenant_id: str
    email: EmailStr
    role: str = "viewer"

class AccessCheckRequest(BaseModel):
    session_token: str
    permission: str

class ApiKeyRequest(BaseModel):
    user_id: str
    tenant_id: str
    label: str = "default"
    scopes: List[str] = []

class RoleUpdateRequest(BaseModel):
    user_id: str
    role: str

def now():
    return datetime.utcnow().isoformat() + "Z"

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def mk_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"

def log_event(kind: str, payload: Dict[str, Any]):
    STATE["audit"].append({
        "id": str(uuid.uuid4()),
        "kind": kind,
        "timestamp": now(),
        "payload": payload,
    })
    STATE["audit"] = STATE["audit"][-500:]

def effective_permissions(role: str) -> List[str]:
    return STATE["roles"].get(role, [])

@app.get("/identity/status")
def status():
    return {
        "mission": "QNT30388",
        "tenant_count": len(STATE["tenants"]),
        "user_count": len(STATE["users"]),
        "session_count": len(STATE["sessions"]),
        "api_key_count": len(STATE["api_keys"]),
        "roles": list(STATE["roles"].keys()),
        "audit_events": len(STATE["audit"]),
    }

@app.post("/identity/tenant/create")
def create_tenant(payload: TenantCreate):
    record = payload.model_dump()
    record["created_at"] = now()
    STATE["tenants"][payload.tenant_id] = record
    log_event("tenant_created", {"tenant_id": payload.tenant_id, "tenant_name": payload.tenant_name})
    return {"status": "ok", "tenant": record}

@app.get("/identity/tenants")
def list_tenants():
    return {"tenants": list(STATE["tenants"].values())}

@app.post("/identity/user/create")
def create_user(payload: UserCreate):
    if payload.tenant_id not in STATE["tenants"]:
        return {"status": "error", "message": "tenant not found"}
    if payload.role not in STATE["roles"]:
        return {"status": "error", "message": "unknown role"}
    record = payload.model_dump()
    record["password_hash"] = hash_password(payload.password)
    record.pop("password", None)
    record["permissions"] = effective_permissions(payload.role)
    record["created_at"] = now()
    STATE["users"][payload.user_id] = record
    log_event("user_created", {"user_id": payload.user_id, "tenant_id": payload.tenant_id, "role": payload.role})
    return {"status": "ok", "user": record}

@app.get("/identity/users")
def list_users():
    return {"users": list(STATE["users"].values())}

@app.post("/identity/login")
def login(payload: LoginRequest):
    match = None
    for user in STATE["users"].values():
        if user["tenant_id"] == payload.tenant_id and user["email"].lower() == payload.email.lower():
            match = user
            break
    if not match:
        return {"status": "error", "message": "user not found"}
    if match["password_hash"] != hash_password(payload.password):
        return {"status": "error", "message": "invalid credentials"}
    token = secrets.token_hex(16)
    session = {
        "session_token": token,
        "user_id": match["user_id"],
        "tenant_id": match["tenant_id"],
        "role": match["role"],
        "permissions": match["permissions"],
        "issued_at": now(),
        "expires_at": (datetime.utcnow() + timedelta(hours=12)).isoformat() + "Z",
        "status": "active",
    }
    STATE["sessions"][token] = session
    log_event("login_success", {"user_id": match["user_id"], "tenant_id": match["tenant_id"]})
    return {"status": "ok", "session": session}

@app.post("/identity/access/check")
def access_check(payload: AccessCheckRequest):
    session = STATE["sessions"].get(payload.session_token)
    if not session or session["status"] != "active":
        return {"status": "denied", "reason": "invalid_session"}
    allowed = payload.permission in session["permissions"]
    return {
        "status": "allowed" if allowed else "denied",
        "tenant_id": session["tenant_id"],
        "user_id": session["user_id"],
        "role": session["role"],
        "permission": payload.permission,
    }

@app.post("/identity/invite")
def invite_user(payload: InviteRequest):
    if payload.tenant_id not in STATE["tenants"]:
        return {"status": "error", "message": "tenant not found"}
    if payload.role not in STATE["roles"]:
        return {"status": "error", "message": "unknown role"}
    invite = {
        "invite_id": mk_id("INV"),
        "tenant_id": payload.tenant_id,
        "email": payload.email,
        "role": payload.role,
        "invite_token": secrets.token_hex(12),
        "status": "issued",
        "issued_at": now(),
    }
    log_event("invite_issued", invite)
    return {"status": "ok", "invite": invite}

@app.post("/identity/role/update")
def update_role(payload: RoleUpdateRequest):
    user = STATE["users"].get(payload.user_id)
    if not user:
        return {"status": "error", "message": "user not found"}
    if payload.role not in STATE["roles"]:
        return {"status": "error", "message": "unknown role"}
    user["role"] = payload.role
    user["permissions"] = effective_permissions(payload.role)
    log_event("role_updated", {"user_id": payload.user_id, "role": payload.role})
    return {"status": "ok", "user": user}

@app.post("/identity/api-key/create")
def create_api_key(payload: ApiKeyRequest):
    user = STATE["users"].get(payload.user_id)
    if not user:
        return {"status": "error", "message": "user not found"}
    if user["tenant_id"] != payload.tenant_id:
        return {"status": "error", "message": "tenant mismatch"}
    key_id = mk_id("API")
    key_value = f"qnt_{secrets.token_hex(18)}"
    record = {
        "key_id": key_id,
        "tenant_id": payload.tenant_id,
        "user_id": payload.user_id,
        "label": payload.label,
        "scopes": payload.scopes or user["permissions"],
        "masked_key": key_value[:8] + "..." + key_value[-4:],
        "created_at": now(),
        "status": "active",
    }
    STATE["api_keys"][key_id] = record
    log_event("api_key_created", {"key_id": key_id, "tenant_id": payload.tenant_id, "user_id": payload.user_id})
    return {"status": "ok", "api_key": record, "secret_once": key_value}

@app.get("/identity/tenant/{tenant_id}/dashboard")
def tenant_dashboard(tenant_id: str):
    tenant = STATE["tenants"].get(tenant_id)
    if not tenant:
        return {"status": "not_found"}
    users = [u for u in STATE["users"].values() if u["tenant_id"] == tenant_id]
    api_keys = [k for k in STATE["api_keys"].values() if k["tenant_id"] == tenant_id]
    return {
        "tenant": tenant,
        "users": users,
        "api_keys": api_keys,
        "summary": {
            "user_count": len(users),
            "api_key_count": len(api_keys),
            "roles_present": sorted(list(set(u["role"] for u in users))),
        }
    }

@app.get("/identity/audit")
def audit(limit: int = 25):
    return {"events": STATE["audit"][-limit:][::-1]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("identity_auth_multitenant:app", host="127.0.0.1", port=8010, reload=False)
