from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["subscription-esign"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
SUB_DIR = ARTIFACTS_DIR / "subscription_documents_esign"

DEFAULT_DOCS = [
    {"doc_type": "subscription_agreement", "title": "Subscription Agreement"},
    {"doc_type": "investor_questionnaire", "title": "Investor Questionnaire"},
    {"doc_type": "risk_acknowledgement", "title": "Risk Acknowledgement"},
    {"doc_type": "signature_packet", "title": "Signature Packet"},
]

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _safe(value: str) -> str:
    return hashlib.sha256((value or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _path(email: str) -> Path:
    SUB_DIR.mkdir(parents=True, exist_ok=True)
    return SUB_DIR / f"{_safe(email)}.json"

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
                    "status": "draft",
                    "sent_at": None,
                    "signed_at": None,
                    "signature_status": "not_sent",
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

@router.get("/api/subscription-docs")
def subscription_docs():
    session = _require_user()
    return _load(session.get("email"))

@router.post("/api/subscription-docs/send")
def subscription_send(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    doc_type = (payload.get("doc_type") or "").strip()
    if not doc_type:
        raise HTTPException(status_code=400, detail="doc_type required")
    data = _load(email)
    doc = _find_doc(data, doc_type)
    if not doc:
        raise HTTPException(status_code=404, detail="document not found")
    doc["status"] = "sent"
    doc["sent_at"] = int(time.time())
    doc["signature_status"] = "awaiting_signature"
    if payload.get("notes"):
        doc["notes"] = str(payload.get("notes"))
    _save(email, data)
    return {"status": "sent", "document": doc}

@router.post("/api/subscription-docs/sign")
def subscription_sign(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    doc_type = (payload.get("doc_type") or "").strip()
    if not doc_type:
        raise HTTPException(status_code=400, detail="doc_type required")
    data = _load(email)
    doc = _find_doc(data, doc_type)
    if not doc:
        raise HTTPException(status_code=404, detail="document not found")
    doc["status"] = "signed"
    doc["signed_at"] = int(time.time())
    doc["signature_status"] = "completed_simulated"
    if payload.get("notes"):
        doc["notes"] = str(payload.get("notes"))
    _save(email, data)
    return {"status": "signed", "document": doc}

@router.post("/api/subscription-docs/review")
def subscription_review(payload: dict = Body(...)):
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

@router.get("/api/subscription-docs/summary")
def subscription_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    docs = data.get("documents", [])
    sent = sum(1 for d in docs if str(d.get("status")) in {"sent", "signed"})
    signed = sum(1 for d in docs if str(d.get("status")) == "signed")
    awaiting = sum(1 for d in docs if str(d.get("signature_status")) == "awaiting_signature")
    return {
        "email": email,
        "total_documents": len(docs),
        "sent_documents": sent,
        "signed_documents": signed,
        "awaiting_signature_documents": awaiting,
        "documents": docs,
    }
