from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["identity-vault"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
VAULT_DIR = ARTIFACTS_DIR / "investor_identity_vault"

DEFAULT_DOCS = [
    {"doc_type": "government_id", "title": "Government ID"},
    {"doc_type": "proof_of_address", "title": "Proof of Address"},
    {"doc_type": "accreditation", "title": "Accreditation Document"},
    {"doc_type": "tax_form", "title": "Tax Form"},
]

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _safe(value: str) -> str:
    return hashlib.sha256((value or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _path(email: str) -> Path:
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    return VAULT_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {
            "email": email,
            "documents": [
                {
                    **d,
                    "status": "missing",
                    "uploaded_at": None,
                    "review_status": "not_submitted",
                    "notes": ""
                } for d in DEFAULT_DOCS
            ],
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

def _find_doc(data: dict, doc_type: str):
    return next((d for d in data.get("documents", []) if d.get("doc_type") == doc_type), None)

@router.get("/api/identity-vault")
def identity_vault():
    session = _require_user()
    email = session.get("email")
    return _load(email)

@router.post("/api/identity-vault/document")
def identity_vault_upload(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    doc_type = (payload.get("doc_type") or "").strip()
    if not doc_type:
        raise HTTPException(status_code=400, detail="doc_type required")
    data = _load(email)
    doc = _find_doc(data, doc_type)
    if not doc:
        doc = {
            "doc_type": doc_type,
            "title": payload.get("title") or doc_type.replace("_", " ").title(),
            "status": "missing",
            "uploaded_at": None,
            "review_status": "not_submitted",
            "notes": "",
        }
        data.setdefault("documents", []).append(doc)
    doc["status"] = "uploaded_simulated"
    doc["uploaded_at"] = int(time.time())
    doc["review_status"] = "pending_review"
    if payload.get("notes"):
        doc["notes"] = str(payload.get("notes"))
    _save(email, data)
    return {"status": "uploaded", "document": doc}

@router.post("/api/identity-vault/review")
def identity_vault_review(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    doc_type = (payload.get("doc_type") or "").strip()
    decision = (payload.get("decision") or "").strip().lower()
    if decision not in {"approved", "rejected", "needs_info"}:
        raise HTTPException(status_code=400, detail="invalid decision")
    data = _load(email)
    doc = _find_doc(data, doc_type)
    if not doc:
        raise HTTPException(status_code=404, detail="document not found")
    doc["review_status"] = decision
    if payload.get("notes"):
        doc["notes"] = str(payload.get("notes"))
    _save(email, data)
    return {"status": decision, "document": doc}

@router.get("/api/identity-vault/summary")
def identity_vault_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    docs = data.get("documents", [])
    uploaded = sum(1 for d in docs if str(d.get("status")) != "missing")
    approved = sum(1 for d in docs if str(d.get("review_status")) == "approved")
    pending = sum(1 for d in docs if str(d.get("review_status")) == "pending_review")
    return {
        "email": email,
        "total_documents": len(docs),
        "uploaded_documents": uploaded,
        "approved_documents": approved,
        "pending_review_documents": pending,
        "documents": docs,
    }
