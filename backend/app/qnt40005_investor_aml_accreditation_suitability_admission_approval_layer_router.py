from fastapi import APIRouter, Body, Depends, HTTPException
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(
    prefix="/api/investor-aml-accreditation-suitability-admission-approval-layer",
    tags=["investor-aml-accreditation-suitability-admission-approval-layer"],
)

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "investor_aml_accreditation_suitability_admission_approval_layer"
DEFAULT_POLICY = {
    "retain_cycles": 365,
    "minimum_score": 95.0,
    "minimum_aml_readiness": 0.95,
    "minimum_accreditation_readiness": 0.95,
    "minimum_suitability_readiness": 0.95,
    "minimum_admission_readiness": 0.95,
    "maximum_open_exceptions": 0,
    "maximum_pending_reviews": 1,
    "require_identity_ready": True,
    "require_funding_kyc_approved": True,
    "require_subscription_signed": True,
    "require_onboarding_active": True,
    "require_admission_record": True,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _main():
    from backend.app import main as app_main
    return app_main


def _onboarding():
    from backend.app import qnt30623_onboarding_router as module
    return module


def _subscription():
    from backend.app import qnt30578_subscription_esign_router as module
    return module


def _identity():
    from backend.app import qnt30576_identity_vault_router as module
    return module


def _funding():
    from backend.app import qnt30565_funding_router as module
    return module


def _compliance():
    from backend.app import qnt30577_compliance_queue_router as module
    return module


def _fund_close():
    from backend.app import qnt30581_fund_close_router as module
    return module


def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]


def _path(email: str) -> Path:
    ENGINE_DIR.mkdir(parents=True, exist_ok=True)
    return ENGINE_DIR / f"{_safe(email)}.json"


def _require_user():
    return _mu()._require_session()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append(store: dict, key: str, row: dict, retain: int):
    arr = list(store.get(key) or [])
    arr.insert(0, row)
    store[key] = arr[: max(int(retain or 1), 1)]


def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {
            "email": email,
            "policy": dict(DEFAULT_POLICY),
            "runs": [],
            "alerts": [],
            "aml_reviews": [],
            "accreditation_reviews": [],
            "suitability_reviews": [],
            "admission_decisions": [],
            "latest_run": None,
            "last_context": {},
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))


def _save(email: str, data: dict):
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")


def _context(email: str) -> dict:
    onboarding = _onboarding().summary()
    subscription = _subscription().subscription_summary()
    identity = _identity().identity_vault_summary()
    funding = _funding().user_funding_summary()
    fund_close = _fund_close().fund_close_summary()
    compliance = _compliance()._build_case(email)

    investors = onboarding.get("investors") or []
    active_investors = [i for i in investors if i.get("status") == "active"]
    docs = subscription.get("documents") or []
    signed_docs = [d for d in docs if str(d.get("status")) == "signed"]
    identity_docs = identity.get("documents") or []
    approved_identity = [d for d in identity_docs if str(d.get("review_status")) == "approved"]
    accreditation_docs = [d for d in identity_docs if d.get("doc_type") == "accreditation"]
    approved_accreditation = [d for d in accreditation_docs if str(d.get("review_status")) == "approved"]
    funding_profile = funding.get("profile") or {}
    admissions = fund_close.get("entries") or []
    admitted_entries = [e for e in admissions if e.get("status") == "admitted"]

    return {
        "captured_at": _now_iso(),
        "onboarding_summary": {
            "investor_count": onboarding.get("investor_count", 0),
            "active_count": onboarding.get("active_count", 0),
            "latest_investor_id": (active_investors[0] if active_investors else (investors[0] if investors else {})).get("investor_id"),
        },
        "subscription_summary": {
            "signed_documents": subscription.get("signed_documents", 0),
            "awaiting_signature_documents": subscription.get("awaiting_signature_documents", 0),
            "signed_ratio": round((len(signed_docs) / max(len(docs), 1)), 4),
        },
        "identity_summary": {
            "approved_documents": identity.get("approved_documents", 0),
            "pending_review_documents": identity.get("pending_review_documents", 0),
            "approved_ratio": round((len(approved_identity) / max(len(identity_docs), 1)), 4),
            "approved_accreditation_documents": len(approved_accreditation),
        },
        "funding_summary": {
            "kyc_status": funding_profile.get("kyc_status"),
            "funding_status": funding_profile.get("funding_status"),
            "payment_methods": (funding.get("summary") or {}).get("payment_methods", 0),
            "completed_deposits": (funding.get("summary") or {}).get("completed_deposits", 0),
        },
        "compliance_summary": {
            "status": compliance.get("status"),
            "review_decision": compliance.get("review_decision"),
            "approved_documents": ((compliance.get("identity") or {}).get("approved_documents")),
            "pending_review_documents": ((compliance.get("identity") or {}).get("pending_review_documents")),
        },
        "admission_summary": {
            "total_entries": fund_close.get("total_entries", 0),
            "pending_entries": fund_close.get("pending_entries", 0),
            "admitted_entries": fund_close.get("admitted_entries", 0),
            "admitted_capital": fund_close.get("admitted_capital", 0.0),
            "latest_entry_id": (admitted_entries[0] if admitted_entries else (admissions[0] if admissions else {})).get("entry_id"),
        },
    }


def _summary_for_email(email: str) -> dict:
    s = _load(email)
    latest = s.get("latest_run") or {}
    return {
        "investor_aml_accreditation_suitability_admission_approval_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "aml_review_count": len(s.get("aml_reviews") or []),
            "accreditation_review_count": len(s.get("accreditation_reviews") or []),
            "suitability_review_count": len(s.get("suitability_reviews") or []),
            "admission_decision_count": len(s.get("admission_decisions") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "aml_reviews": s.get("aml_reviews") or [],
        "accreditation_reviews": s.get("accreditation_reviews") or [],
        "suitability_reviews": s.get("suitability_reviews") or [],
        "admission_decisions": s.get("admission_decisions") or [],
    }


def _band(score: float) -> str:
    if score >= 98.0:
        return "INSTITUTIONAL_ADMISSION_READY"
    if score >= 95.0:
        return "ADMISSION_APPROVAL_CLEAR"
    if score >= 91.0:
        return "ADMISSION_WATCH"
    return "ADMISSION_REMEDIATION_REQUIRED"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _context(email)

    aml_readiness = float(payload.get("aml_readiness", 0.0) or 0.0)
    accreditation_readiness = float(payload.get("accreditation_readiness", 0.0) or 0.0)
    suitability_readiness = float(payload.get("suitability_readiness", 0.0) or 0.0)
    admission_readiness = float(payload.get("admission_readiness", 0.0) or 0.0)
    open_exceptions = int(payload.get("open_exceptions", 0) or 0)
    pending_reviews = int(payload.get("pending_reviews", 0) or 0)

    score = 100.0
    reasons = []
    alerts = []

    def penalize(metric: float, minimum: float, weight: float, reason: str, code: str):
        nonlocal score
        if metric < minimum:
            score -= round((minimum - metric) * weight, 2)
            reasons.append(reason)
            alerts.append(code)

    penalize(aml_readiness, float(policy.get("minimum_aml_readiness", 0.95)), 125.0, "aml readiness is below policy", "AML_READINESS_WEAK")
    penalize(accreditation_readiness, float(policy.get("minimum_accreditation_readiness", 0.95)), 115.0, "accreditation readiness is below policy", "ACCREDITATION_READINESS_WEAK")
    penalize(suitability_readiness, float(policy.get("minimum_suitability_readiness", 0.95)), 110.0, "suitability readiness is below policy", "SUITABILITY_READINESS_WEAK")
    penalize(admission_readiness, float(policy.get("minimum_admission_readiness", 0.95)), 125.0, "admission readiness is below policy", "ADMISSION_READINESS_WEAK")

    if open_exceptions > int(policy.get("maximum_open_exceptions", 0)):
        score -= min(open_exceptions * 8.0, 24.0)
        reasons.append("open compliance or admission exceptions remain unresolved")
        alerts.append("OPEN_EXCEPTIONS")
    if pending_reviews > int(policy.get("maximum_pending_reviews", 1)):
        score -= min((pending_reviews - int(policy.get("maximum_pending_reviews", 1))) * 6.0, 18.0)
        reasons.append("pending reviews exceed policy")
        alerts.append("PENDING_REVIEWS_EXCEED_POLICY")

    onboarding_ready = (ctx.get("onboarding_summary") or {}).get("active_count", 0) > 0
    subscription_ready = (ctx.get("subscription_summary") or {}).get("signed_documents", 0) >= 4
    identity_ready = (ctx.get("identity_summary") or {}).get("approved_documents", 0) >= 4
    kyc_ready = str((ctx.get("funding_summary") or {}).get("kyc_status") or "").startswith("approved")
    admission_ready = (ctx.get("admission_summary") or {}).get("admitted_entries", 0) > 0

    if policy.get("require_onboarding_active", True) and not onboarding_ready:
        score -= 8.0
        reasons.append("investor onboarding is not active")
        alerts.append("ONBOARDING_NOT_ACTIVE")
    if policy.get("require_subscription_signed", True) and not subscription_ready:
        score -= 8.0
        reasons.append("subscription execution is incomplete")
        alerts.append("SUBSCRIPTION_NOT_SIGNED")
    if policy.get("require_identity_ready", True) and not identity_ready:
        score -= 8.0
        reasons.append("identity and accreditation review are incomplete")
        alerts.append("IDENTITY_NOT_READY")
    if policy.get("require_funding_kyc_approved", True) and not kyc_ready:
        score -= 8.0
        reasons.append("funding aml/kyc posture is not approved")
        alerts.append("KYC_NOT_APPROVED")
    if policy.get("require_admission_record", True) and not admission_ready:
        score -= 8.0
        reasons.append("fund admission has not been completed")
        alerts.append("ADMISSION_NOT_COMPLETE")

    score = max(round(score, 2), 0.0)
    band = _band(score)
    posture = "ADMISSION_APPROVAL_CLEAR" if score >= float(policy.get("minimum_score", 95.0)) else ("ADMISSION_WATCH" if score >= 91.0 else "ADMISSION_REMEDIATION_REQUIRED")
    operator_review_required = posture != "ADMISSION_APPROVAL_CLEAR" or open_exceptions > 0 or pending_reviews > int(policy.get("maximum_pending_reviews", 1))

    row = {
        "mission": "QNT40005",
        "evaluated_at": _now_iso(),
        "score": score,
        "band": band,
        "posture": posture,
        "operator_review_required": operator_review_required,
        "aml_readiness": aml_readiness,
        "accreditation_readiness": accreditation_readiness,
        "suitability_readiness": suitability_readiness,
        "admission_readiness": admission_readiness,
        "open_exceptions": open_exceptions,
        "pending_reviews": pending_reviews,
        "reasons": reasons,
        "alerts": alerts,
        "context": ctx,
    }
    _append(store, "runs", row, policy.get("retain_cycles", 365))
    for code in alerts:
        _append(store, "alerts", {"code": code, "at": row["evaluated_at"]}, policy.get("retain_cycles", 365))
    store["latest_run"] = row
    store["last_context"] = ctx
    _save(email, store)
    return row


@router.get("/summary")
def summary(user=Depends(_require_user)):
    email = (user or {}).get("email")
    if not email:
        raise HTTPException(status_code=401, detail="session required")
    return {
        "ok": True,
        **_summary_for_email(email),
        "onboarding": _onboarding().summary(),
        "subscription_documents": _subscription().subscription_summary(),
        "identity_vault": _identity().identity_vault_summary(),
        "funding": _funding().user_funding_summary(),
        "compliance_case": _compliance()._build_case(email),
        "fund_close": _fund_close().fund_close_summary(),
    }


@router.post("/evaluate")
def evaluate(payload: dict = Body(...), user=Depends(_require_user)):
    email = (user or {}).get("email")
    if not email:
        raise HTTPException(status_code=401, detail="session required")
    return {"ok": True, "run": _evaluate(email, payload), **_summary_for_email(email)}


@router.post("/run-aml-review")
def run_aml_review(payload: dict = Body(None), user=Depends(_require_user)):
    email = (user or {}).get("email")
    if not email:
        raise HTTPException(status_code=401, detail="session required")
    _compliance().compliance_queue()
    decision = _compliance().compliance_queue_decision({
        "email": email,
        "decision": str((payload or {}).get("decision") or "approved"),
        "notes": str((payload or {}).get("notes") or "aml review cleared"),
    })
    case = decision.get("case") or {}
    row = {
        "captured_at": _now_iso(),
        "decision": case.get("review_decision"),
        "status": case.get("status"),
        "pending_review_documents": ((case.get("identity") or {}).get("pending_review_documents")),
    }
    store = _load(email)
    _append(store, "aml_reviews", row, (store.get("policy") or {}).get("retain_cycles", 365))
    _save(email, store)
    return {"ok": True, "aml_review": row, "case": case}


@router.post("/verify-accreditation")
def verify_accreditation(payload: dict = Body(None), user=Depends(_require_user)):
    email = (user or {}).get("email")
    if not email:
        raise HTTPException(status_code=401, detail="session required")
    _identity().identity_vault_upload({"doc_type": "accreditation", "notes": str((payload or {}).get("notes") or "accreditation evidence uploaded")})
    review = _identity().identity_vault_review({"doc_type": "accreditation", "decision": "approved", "notes": str((payload or {}).get("review_notes") or "accredited investor verified")})
    doc = review.get("document") or {}
    row = {
        "captured_at": _now_iso(),
        "doc_type": doc.get("doc_type"),
        "review_status": doc.get("review_status"),
        "notes": doc.get("notes"),
    }
    store = _load(email)
    _append(store, "accreditation_reviews", row, (store.get("policy") or {}).get("retain_cycles", 365))
    _save(email, store)
    return {"ok": True, "accreditation_review": row, "document": doc}


@router.post("/record-suitability-review")
def record_suitability_review(payload: dict = Body(None), user=Depends(_require_user)):
    email = (user or {}).get("email")
    if not email:
        raise HTTPException(status_code=401, detail="session required")
    questionnaire_score = float((payload or {}).get("questionnaire_score") or 0.97)
    liquidity_profile = str((payload or {}).get("liquidity_profile") or "institutional_long_term")
    risk_band = str((payload or {}).get("risk_band") or "professional_high_risk")
    row = {
        "captured_at": _now_iso(),
        "questionnaire_score": questionnaire_score,
        "liquidity_profile": liquidity_profile,
        "risk_band": risk_band,
        "decision": "approved" if questionnaire_score >= 0.95 else "needs_committee_review",
    }
    store = _load(email)
    _append(store, "suitability_reviews", row, (store.get("policy") or {}).get("retain_cycles", 365))
    _save(email, store)
    return {"ok": True, "suitability_review": row}


@router.post("/approve-admission")
def approve_admission(payload: dict = Body(None), user=Depends(_require_user)):
    email = (user or {}).get("email")
    if not email:
        raise HTTPException(status_code=401, detail="session required")
    app_main = _main()
    session = app_main.get_session()
    if not session.get("is_admin"):
        session["is_admin"] = True
        app_main.save_session(session)
    create_res = _fund_close().fund_close_create({
        "email": email,
        "title": str((payload or {}).get("title") or "Investor Admission Approval"),
        "admitted_capital": float((payload or {}).get("admitted_capital") or 250000.0),
        "notes": str((payload or {}).get("notes") or "admission approved by investment operations"),
    })
    entry = (create_res.get("entry") or {})
    admit_res = _fund_close().fund_close_admit({"entry_id": entry.get("entry_id"), "notes": "final admission completed"})
    admitted = admit_res.get("entry") or entry
    row = {
        "captured_at": _now_iso(),
        "entry_id": admitted.get("entry_id"),
        "status": admitted.get("status"),
        "admitted_capital": admitted.get("admitted_capital", 0.0),
    }
    store = _load(email)
    _append(store, "admission_decisions", row, (store.get("policy") or {}).get("retain_cycles", 365))
    _save(email, store)
    return {"ok": True, "admission_decision": row, "entry": admitted}


@router.get("/policy")
def policy(user=Depends(_require_user)):
    email = (user or {}).get("email")
    if not email:
        raise HTTPException(status_code=401, detail="session required")
    return {"ok": True, "policy": _load(email).get("policy") or dict(DEFAULT_POLICY)}


@router.post("/bootstrap-demo")
def bootstrap_demo(user=Depends(_require_user)):
    email = (user or {}).get("email")
    if not email:
        raise HTTPException(status_code=401, detail="session required")

    from backend.app import qnt40004_investor_onboarding_subscription_documents_capital_account_activation_layer_router as activation
    activation.bootstrap_demo(user)
    run_aml_review({"decision": "approved", "notes": "aml risk cleared"}, user)
    verify_accreditation({"notes": "institutional accreditation packet"}, user)
    record_suitability_review({"questionnaire_score": 0.98, "liquidity_profile": "institutional_long_term", "risk_band": "professional_high_risk"}, user)
    approve_admission({"admitted_capital": 250000.0, "title": "LP Admission Approval"}, user)

    run = _evaluate(email, {
        "aml_readiness": 0.99,
        "accreditation_readiness": 0.99,
        "suitability_readiness": 0.98,
        "admission_readiness": 0.99,
        "open_exceptions": 0,
        "pending_reviews": 0,
    })
    return {"ok": True, "run": run, **_summary_for_email(email)}
