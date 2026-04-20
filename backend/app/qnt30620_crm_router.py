from fastapi import APIRouter, Body
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["investor-lifecycle-crm"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
CRM_DIR = ARTIFACTS_DIR / "investor_lifecycle_crm"

DEFAULT_STAGES = [
    "prospect",
    "qualified",
    "onboarding",
    "active",
    "at_risk",
    "inactive",
]

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _identity():
    from backend.app import qnt30617_identity_registry_router as identity
    return identity

def _safe(v):
    return hashlib.sha256((v or "").strip().lower().encode()).hexdigest()[:24]

def _path(email):
    CRM_DIR.mkdir(parents=True, exist_ok=True)
    return CRM_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _load(email):
    p = _path(email)
    if not p.exists():
        d = {
            "email": email,
            "relationships": [],
            "activities": [],
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

def _find_relationship(data, relationship_id):
    return next((r for r in data.get("relationships", []) if r.get("relationship_id") == relationship_id), None)

def _find_by_investor(data, investor_id):
    return next((r for r in data.get("relationships", []) if r.get("investor_id") == investor_id), None)

@router.get("/api/crm")
def crm():
    session = _require_user()
    return _load(session.get("email"))

@router.post("/api/crm/relationship")
def create_relationship(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    data = _load(email)

    investor_id = str(payload.get("investor_id") or "")
    if not investor_id:
        return {"status": "investor_id_required"}

    existing = _find_by_investor(data, investor_id)
    if existing:
        return {"status": "already_exists", "relationship": existing}

    item = {
        "relationship_id": f"rel_{int(time.time())}",
        "investor_id": investor_id,
        "owner": str(payload.get("owner") or "Unassigned"),
        "stage": str(payload.get("stage") or "prospect"),
        "health": str(payload.get("health") or "neutral"),
        "aum_band": str(payload.get("aum_band") or ""),
        "region": str(payload.get("region") or ""),
        "last_contact_at": None,
        "next_action": str(payload.get("next_action") or ""),
        "notes": str(payload.get("notes") or ""),
        "created_at": int(time.time()),
        "updated_at": int(time.time())
    }
    data.setdefault("relationships", []).insert(0, item)
    data["relationships"] = data.get("relationships", [])[:500]
    _save(email, data)
    return {"status": "created", "relationship": item}

@router.post("/api/crm/stage")
def update_stage(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    relationship_id = str(payload.get("relationship_id") or "")
    stage = str(payload.get("stage") or "")
    data = _load(email)
    rel = _find_relationship(data, relationship_id)
    if not rel:
        return {"status": "not_found"}
    rel["stage"] = stage or rel.get("stage")
    rel["health"] = str(payload.get("health") or rel.get("health"))
    rel["next_action"] = str(payload.get("next_action") or rel.get("next_action"))
    rel["updated_at"] = int(time.time())
    _save(email, data)
    return {"status": "updated", "relationship": rel}

@router.post("/api/crm/activity")
def log_activity(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    data = _load(email)

    relationship_id = str(payload.get("relationship_id") or "")
    rel = _find_relationship(data, relationship_id)
    if not rel:
        return {"status": "relationship_not_found"}

    activity = {
        "activity_id": f"act_{int(time.time())}",
        "relationship_id": relationship_id,
        "investor_id": rel.get("investor_id"),
        "activity_type": str(payload.get("activity_type") or "note"),
        "subject": str(payload.get("subject") or "Relationship Activity"),
        "detail": str(payload.get("detail") or ""),
        "direction": str(payload.get("direction") or "internal"),
        "actor": str(payload.get("actor") or "Operator"),
        "created_at": int(time.time())
    }
    data.setdefault("activities", []).insert(0, activity)
    data["activities"] = data.get("activities", [])[:2000]
    rel["last_contact_at"] = activity["created_at"]
    if payload.get("next_action") is not None:
        rel["next_action"] = str(payload.get("next_action") or "")
    rel["updated_at"] = int(time.time())
    _save(email, data)
    return {"status": "logged", "activity": activity, "relationship": rel}

@router.get("/api/crm/summary")
def crm_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    relationships = data.get("relationships", [])
    activities = data.get("activities", [])

    by_stage = {}
    for stage in DEFAULT_STAGES:
        by_stage[stage] = 0
    for r in relationships:
        st = r.get("stage") or "unknown"
        by_stage[st] = by_stage.get(st, 0) + 1

    by_health = {"strong": 0, "neutral": 0, "watch": 0, "at_risk": 0}
    for r in relationships:
        h = r.get("health") or "neutral"
        by_health[h] = by_health.get(h, 0) + 1

    latest_relationship = relationships[0] if relationships else None
    latest_activity = activities[0] if activities else None

    return {
        "email": email,
        "relationship_count": len(relationships),
        "activity_count": len(activities),
        "stage_counts": by_stage,
        "health_counts": by_health,
        "latest_relationship": latest_relationship,
        "latest_activity": latest_activity,
        "relationships": relationships[:100],
        "activities": activities[:100]
    }
