from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["investor-ops"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
OPS_DIR = ARTIFACTS_DIR / "investor_ops_console"
REVIEW_DIR = ARTIFACTS_DIR / "investor_admin_reviews"

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _fund():
    from backend.app import qnt30565_funding_router as fr
    return fr

def _rep():
    from backend.app import qnt30564_reporting_router as rr
    return rr

def _recon():
    from backend.app import qnt30563_reconciliation_router as rc
    return rc

def _safe_email(email: str) -> str:
    return hashlib.sha256((email or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _ops_path(email: str) -> Path:
    OPS_DIR.mkdir(parents=True, exist_ok=True)
    return OPS_DIR / f"{_safe_email(email)}.json"

def _review_path(email: str) -> Path:
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    return REVIEW_DIR / f"{_safe_email(email)}.json"

def _require_user():
    return _mu()._require_session()

def _load(path: Path, default: dict) -> dict:
    if not path.exists():
        path.write_text(json.dumps(default, indent=2), encoding="utf-8")
        return default
    return json.loads(path.read_text(encoding="utf-8"))

def _save(path: Path, data: dict) -> dict:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data

def _ops_summary(email: str) -> dict:
    mu = _mu()
    fund = _fund()
    rep = _rep()
    recon = _recon()
    ledger = mu._load_ledger(email)
    perf, series = mu._perf_snapshot(email, ledger)
    funding = fund._load_profile(email)
    intents = fund._load_intents(email)
    statement_store = rep._load_statement_store(email)
    reconciliation = recon._build_reconciliation(email)
    return {
        "email": email,
        "capital": {
            "balance": round(float(ledger.get("balance", 0.0)), 2),
            "available": round(float(ledger.get("available", 0.0)), 2),
            "allocated": round(float(ledger.get("allocated", 0.0)), 2),
            "history_count": len(ledger.get("history", [])),
        },
        "performance": perf,
        "series_points": len(series),
        "funding": {
            "status": funding.get("funding_status"),
            "kyc_status": funding.get("kyc_status"),
            "payment_methods": len(funding.get("payment_methods", [])),
            "intent_count": len(intents.get("payment_intents", [])),
        },
        "reporting": {
            "statements": len(statement_store.get("statements", [])),
        },
        "reconciliation": {
            "status": reconciliation.get("status"),
            "warnings": reconciliation.get("warnings", []),
            "blockers": reconciliation.get("blockers", []),
        },
    }

@router.get("/api/investor-ops/summary")
def investor_ops_summary():
    session = _require_user()
    email = session.get("email")
    payload = _ops_summary(email)
    store = _load(_ops_path(email), {"email": email, "snapshots": []})
    store.setdefault("snapshots", []).insert(0, {"captured_at": int(time.time()), "summary": payload})
    store["snapshots"] = store["snapshots"][:50]
    _save(_ops_path(email), store)
    return payload

@router.get("/api/investor-ops/history")
def investor_ops_history():
    session = _require_user()
    email = session.get("email")
    return _load(_ops_path(email), {"email": email, "snapshots": []})

@router.get("/api/investor-admin/reviews")
def investor_admin_reviews():
    session = _require_user()
    email = session.get("email")
    return _load(_review_path(email), {"email": email, "reviews": []})

@router.post("/api/investor-admin/review-request")
def investor_admin_review_request(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    data = _load(_review_path(email), {"email": email, "reviews": []})
    review = {
        "review_id": f"rev_{int(time.time())}",
        "type": (payload.get("type") or "general").strip().lower(),
        "status": "pending",
        "title": (payload.get("title") or "Investor review request").strip(),
        "notes": (payload.get("notes") or "").strip(),
        "requested_at": int(time.time()),
    }
    data.setdefault("reviews", []).insert(0, review)
    data["reviews"] = data["reviews"][:100]
    _save(_review_path(email), data)
    return {"status": "requested", "review": review, "total_reviews": len(data["reviews"])}

@router.post("/api/investor-admin/review-decision")
def investor_admin_review_decision(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    data = _load(_review_path(email), {"email": email, "reviews": []})
    review_id = payload.get("review_id")
    decision = (payload.get("decision") or "").strip().lower()
    review = next((r for r in data.get("reviews", []) if r.get("review_id") == review_id), None)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    if decision not in {"approved", "rejected", "needs_info"}:
        raise HTTPException(status_code=400, detail="Invalid decision")
    review["status"] = decision
    review["reviewed_at"] = int(time.time())
    review["review_notes"] = (payload.get("review_notes") or "").strip()
    _save(_review_path(email), data)
    return {"status": decision, "review": review}
