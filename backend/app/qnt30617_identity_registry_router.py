from fastapi import APIRouter, Body
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["investor-identity-registry"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
REG_DIR = ARTIFACTS_DIR / "investor_identity_registry"

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _safe(v):
    return hashlib.sha256((v or "").strip().lower().encode()).hexdigest()[:24]

def _path(email):
    REG_DIR.mkdir(parents=True, exist_ok=True)
    return REG_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _load(email):
    p = _path(email)
    if not p.exists():
        d = {
            "email": email,
            "investors": [],
            "profiles": [],
            "created_at": int(time.time()),
            "updated_at": int(time.time())
        }
        p.write_text(json.dumps(d, indent=2), encoding="utf-8")
        return d
    return json.loads(p.read_text(encoding="utf-8"))

def _save(email, d):
    d["updated_at"] = int(time.time())
    _path(email).write_text(json.dumps(d, indent=2), encoding="utf-8")
    return d

def _find_profile(data, profile_id):
    return next((p for p in data.get("profiles", []) if p.get("profile_id") == profile_id), None)

@router.get("/api/identity-registry")
def identity_registry():
    session = _require_user()
    return _load(session.get("email"))

@router.post("/api/identity-registry/investor")
def add_investor(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    item = {
        "investor_id": f"inv_{int(time.time())}",
        "legal_name": str(payload.get("legal_name") or "Unnamed Investor"),
        "primary_email": str(payload.get("primary_email") or ""),
        "entity_type": str(payload.get("entity_type") or "individual"),
        "jurisdiction": str(payload.get("jurisdiction") or ""),
        "status": "active",
        "created_at": int(time.time())
    }
    data.setdefault("investors", []).insert(0, item)
    data["investors"] = data["investors"][:500]
    _save(email, data)
    return {"status": "created", "investor": item}

@router.post("/api/identity-registry/profile")
def add_delivery_profile(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    recipients = payload.get("recipients") or []
    item = {
        "profile_id": f"profile_{int(time.time())}",
        "profile_name": str(payload.get("profile_name") or "Default Delivery Profile"),
        "investor_id": str(payload.get("investor_id") or ""),
        "recipients": [
            {
                "name": str(r.get("name") or ""),
                "email": str(r.get("email") or ""),
                "role": str(r.get("role") or "recipient"),
                "active": bool(r.get("active", True))
            }
            for r in recipients
        ],
        "delivery_channels": payload.get("delivery_channels") or ["portal"],
        "status": "active",
        "created_at": int(time.time())
    }
    data.setdefault("profiles", []).insert(0, item)
    data["profiles"] = data["profiles"][:500]
    _save(email, data)
    return {"status": "created", "profile": item}

@router.post("/api/identity-registry/profile/disable")
def disable_profile(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    profile_id = str(payload.get("profile_id") or "")
    data = _load(email)
    profile = _find_profile(data, profile_id)
    if not profile:
        return {"status": "not_found"}
    profile["status"] = "disabled"
    profile["disabled_at"] = int(time.time())
    _save(email, data)
    return {"status": "disabled", "profile": profile}

@router.get("/api/identity-registry/summary")
def identity_registry_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    investors = data.get("investors", [])
    profiles = data.get("profiles", [])
    active_profiles = sum(1 for p in profiles if p.get("status") == "active")
    recipient_count = sum(len(p.get("recipients", [])) for p in profiles)
    latest_profile = profiles[0] if profiles else None
    return {
        "email": email,
        "investor_count": len(investors),
        "profile_count": len(profiles),
        "active_profile_count": active_profiles,
        "recipient_count": recipient_count,
        "latest_profile": latest_profile,
        "investors": investors[:100],
        "profiles": profiles[:100]
    }
