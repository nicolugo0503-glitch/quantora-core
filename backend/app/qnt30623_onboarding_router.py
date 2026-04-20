from fastapi import APIRouter, Body
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["investor-onboarding-subscription"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ONB_DIR = ARTIFACTS_DIR / "investor_onboarding"

DEFAULT_CHECKLIST = [
    "nda_signed",
    "subscription_agreement",
    "kyc_completed",
    "accreditation_verified",
    "capital_commitment",
]

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _safe(v):
    return hashlib.sha256((v or "").strip().lower().encode()).hexdigest()[:24]

def _path(email):
    ONB_DIR.mkdir(parents=True, exist_ok=True)
    return ONB_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _load(email):
    p = _path(email)
    if not p.exists():
        d = {"email": email, "investors": [], "created_at": int(time.time()), "updated_at": int(time.time())}
        p.write_text(json.dumps(d, indent=2), encoding="utf-8")
        return d
    return json.loads(p.read_text(encoding="utf-8"))

def _save(email, d):
    d["updated_at"] = int(time.time())
    _path(email).write_text(json.dumps(d, indent=2), encoding="utf-8")
    return d

def _find(data, investor_id):
    return next((i for i in data.get("investors", []) if i.get("investor_id") == investor_id), None)

@router.get("/api/onboarding")
def onboarding():
    session = _require_user()
    return _load(session.get("email"))

@router.post("/api/onboarding/investor")
def create_investor(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    investor_id = str(payload.get("investor_id") or f"inv_{int(time.time())}")
    item = {
        "investor_id": investor_id,
        "name": str(payload.get("name") or "Investor"),
        "status": "onboarding",
        "commitment": float(payload.get("commitment") or 0.0),
        "checklist": {k: False for k in DEFAULT_CHECKLIST},
        "documents": [],
        "created_at": int(time.time())
    }
    data.setdefault("investors", []).insert(0, item)
    _save(email, data)
    return {"status": "created", "investor": item}

@router.post("/api/onboarding/checklist")
def update_checklist(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    inv = _find(data, str(payload.get("investor_id")))
    if not inv:
        return {"status": "not_found"}
    key = str(payload.get("item"))
    value = bool(payload.get("value"))
    if key in inv["checklist"]:
        inv["checklist"][key] = value
    inv["status"] = "active" if all(inv["checklist"].values()) else "onboarding"
    _save(email, data)
    return {"status": "updated", "investor": inv}

@router.post("/api/onboarding/document")
def add_document(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    inv = _find(data, str(payload.get("investor_id")))
    if not inv:
        return {"status": "not_found"}
    doc = {
        "doc_id": f"doc_{int(time.time())}",
        "type": str(payload.get("type") or "subscription"),
        "name": str(payload.get("name") or "Document"),
        "status": "uploaded",
        "created_at": int(time.time())
    }
    inv.setdefault("documents", []).insert(0, doc)
    _save(email, data)
    return {"status": "added", "document": doc}

@router.get("/api/onboarding/summary")
def summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    invs = data.get("investors", [])
    active = sum(1 for i in invs if i.get("status") == "active")
    onboarding = sum(1 for i in invs if i.get("status") == "onboarding")
    total_commitment = sum(float(i.get("commitment") or 0.0) for i in invs)
    return {
        "email": email,
        "investor_count": len(invs),
        "active_count": active,
        "onboarding_count": onboarding,
        "total_commitment": round(total_commitment,2),
        "investors": invs[:100]
    }
