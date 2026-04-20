from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
import json, time

router = APIRouter(tags=["compliance-queue"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
QUEUE_DIR = ARTIFACTS_DIR / "compliance_review_queue"

def _main():
    from backend.app import main as app_main
    return app_main

def _vault():
    from backend.app import qnt30576_identity_vault_router as vault
    return vault

def _fund():
    from backend.app import qnt30565_funding_router as fund
    return fund

def _path() -> Path:
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    return QUEUE_DIR / "review_queue.json"

def _load() -> dict:
    path = _path()
    if not path.exists():
        data = {"cases": [], "activity": []}
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))

def _save(data: dict) -> dict:
    _path().write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data

def _require_admin():
    return _main().require_admin()

def _all_emails():
    users = _main().users_db().get("users", [])
    emails = []
    for u in users:
        email = (u.get("email") or "").strip().lower()
        if email:
            emails.append(email)
    return emails

def _build_case(email: str) -> dict:
    vault = _vault()
    fund = _fund()
    docs = vault._load(email)
    documents = docs.get("documents", [])
    uploaded = sum(1 for d in documents if str(d.get("status")) != "missing")
    approved = sum(1 for d in documents if str(d.get("review_status")) == "approved")
    pending = sum(1 for d in documents if str(d.get("review_status")) == "pending_review")
    funding = fund._load_profile(email)
    status = "ready_for_review" if uploaded > 0 else "missing_documents"
    if pending > 0:
        status = "pending_document_review"
    if approved == len(documents) and len(documents) > 0:
        status = "verified"
    return {
        "case_id": f"case_{email.replace('@','_at_').replace('.','_')}",
        "email": email,
        "identity": {
            "total_documents": len(documents),
            "uploaded_documents": uploaded,
            "approved_documents": approved,
            "pending_review_documents": pending,
        },
        "funding": {
            "kyc_status": funding.get("kyc_status"),
            "payment_methods": len(funding.get("payment_methods", [])),
        },
        "status": status,
        "updated_at": int(time.time()),
    }

@router.get("/api/compliance-queue")
def compliance_queue():
    _require_admin()
    data = _load()
    emails = _all_emails()
    cases = [_build_case(email) for email in emails]
    data["cases"] = cases
    _save(data)
    return data

@router.get("/api/compliance-queue/summary")
def compliance_queue_summary():
    _require_admin()
    data = compliance_queue()
    cases = data.get("cases", [])
    statuses = {}
    for c in cases:
        s = c.get("status") or "unknown"
        statuses[s] = statuses.get(s, 0) + 1
    return {
        "case_count": len(cases),
        "status_counts": statuses,
        "cases": cases[:200],
    }

@router.post("/api/compliance-queue/decision")
def compliance_queue_decision(payload: dict = Body(...)):
    _require_admin()
    email = (payload.get("email") or "").strip().lower()
    decision = (payload.get("decision") or "").strip().lower()
    notes = (payload.get("notes") or "").strip()
    if not email or decision not in {"approved", "rejected", "needs_info"}:
        raise HTTPException(status_code=400, detail="email and valid decision required")
    data = _load()
    case = next((c for c in data.get("cases", []) if c.get("email") == email), None)
    if not case:
        case = _build_case(email)
        data.setdefault("cases", []).append(case)
    case["review_decision"] = decision
    case["review_notes"] = notes
    case["reviewed_at"] = int(time.time())
    case["status"] = "verified" if decision == "approved" else ("rejected" if decision == "rejected" else "needs_info")
    data.setdefault("activity", []).insert(0, {
        "email": email,
        "decision": decision,
        "notes": notes,
        "timestamp": int(time.time())
    })
    data["activity"] = data["activity"][:500]
    _save(data)
    return {"status": decision, "case": case}

@router.get("/api/compliance-queue/activity")
def compliance_queue_activity():
    _require_admin()
    return _load()
