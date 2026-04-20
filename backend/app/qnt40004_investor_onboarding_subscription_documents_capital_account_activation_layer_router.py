from fastapi import APIRouter, Body, Depends, HTTPException
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(
    prefix="/api/investor-onboarding-subscription-documents-capital-account-activation-layer",
    tags=["investor-onboarding-subscription-documents-capital-account-activation-layer"],
)

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "investor_onboarding_subscription_documents_capital_account_activation_layer"
DEFAULT_POLICY = {
    "retain_cycles": 365,
    "minimum_score": 95.0,
    "minimum_onboarding_completion": 0.95,
    "minimum_subscription_completion": 0.95,
    "minimum_identity_completion": 0.95,
    "minimum_funding_readiness": 0.95,
    "minimum_capital_activation_readiness": 0.95,
    "maximum_open_exceptions": 0,
    "maximum_pending_documents": 1,
    "require_onboarding_ready": True,
    "require_subscription_ready": True,
    "require_identity_ready": True,
    "require_funding_ready": True,
    "require_capital_account_ready": True,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


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


def _capital():
    from backend.app import qnt30624_capital_ledger_router as module
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
            "onboarding_events": [],
            "subscription_events": [],
            "identity_events": [],
            "funding_events": [],
            "capital_activation_events": [],
            "latest_run": None,
            "last_context": {},
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))


def _save(email: str, data: dict):
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")


def _onboarding_context(email: str) -> dict:
    onboarding = _onboarding().summary()
    subscription = _subscription().subscription_summary()
    identity = _identity().identity_vault_summary()
    funding = _funding().user_funding_summary()
    capital = _capital().capital_ledger_summary()
    investors = onboarding.get("investors") or []
    active_investors = [i for i in investors if i.get("status") == "active"]
    docs = subscription.get("documents") or []
    signed_docs = [d for d in docs if str(d.get("status")) == "signed"]
    identity_docs = identity.get("documents") or []
    approved_identity = [d for d in identity_docs if str(d.get("review_status")) == "approved"]
    recent_intents = funding.get("recent_intents") or []
    completed_intents = [x for x in recent_intents if str(x.get("status")) == "completed"]
    return {
        "captured_at": _now_iso(),
        "onboarding_summary": {
            "investor_count": onboarding.get("investor_count", 0),
            "active_count": onboarding.get("active_count", 0),
            "onboarding_count": onboarding.get("onboarding_count", 0),
            "total_commitment": onboarding.get("total_commitment", 0.0),
            "latest_investor_id": (investors[0] if investors else {}).get("investor_id"),
        },
        "subscription_summary": {
            "total_documents": subscription.get("total_documents", 0),
            "sent_documents": subscription.get("sent_documents", 0),
            "signed_documents": subscription.get("signed_documents", 0),
            "awaiting_signature_documents": subscription.get("awaiting_signature_documents", 0),
            "signed_ratio": round((len(signed_docs) / max(len(docs), 1)), 4),
        },
        "identity_summary": {
            "total_documents": identity.get("total_documents", 0),
            "uploaded_documents": identity.get("uploaded_documents", 0),
            "approved_documents": identity.get("approved_documents", 0),
            "pending_review_documents": identity.get("pending_review_documents", 0),
            "approved_ratio": round((len(approved_identity) / max(len(identity_docs), 1)), 4),
        },
        "funding_summary": {
            "payment_methods": (funding.get("summary") or {}).get("payment_methods", 0),
            "completed_deposits": (funding.get("summary") or {}).get("completed_deposits", 0),
            "pending_intents": (funding.get("summary") or {}).get("pending_intents", 0),
            "total_completed_amount": (funding.get("summary") or {}).get("total_completed_amount", 0.0),
            "kyc_status": (funding.get("profile") or {}).get("kyc_status"),
            "funding_status": (funding.get("profile") or {}).get("funding_status"),
            "completed_intent_count": len(completed_intents),
        },
        "capital_summary": {
            "account_count": capital.get("account_count", 0),
            "entry_count": capital.get("entry_count", 0),
            "allocation_count": capital.get("allocation_count", 0),
            "total_committed_capital": capital.get("total_committed_capital", 0.0),
            "total_funded_capital": capital.get("total_funded_capital", 0.0),
            "total_nav": capital.get("total_nav", 0.0),
            "latest_investor_id": (capital.get("accounts") or [{}])[0].get("investor_id") if capital.get("accounts") else None,
        },
    }


def _summary_for_email(email: str) -> dict:
    s = _load(email)
    latest = s.get("latest_run") or {}
    return {
        "investor_onboarding_subscription_documents_capital_account_activation_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "onboarding_event_count": len(s.get("onboarding_events") or []),
            "subscription_event_count": len(s.get("subscription_events") or []),
            "identity_event_count": len(s.get("identity_events") or []),
            "funding_event_count": len(s.get("funding_events") or []),
            "capital_activation_event_count": len(s.get("capital_activation_events") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "onboarding_events": s.get("onboarding_events") or [],
        "subscription_events": s.get("subscription_events") or [],
        "identity_events": s.get("identity_events") or [],
        "funding_events": s.get("funding_events") or [],
        "capital_activation_events": s.get("capital_activation_events") or [],
    }


def _band(score: float) -> str:
    if score >= 98.0:
        return "INSTITUTIONAL_ACTIVATION_READY"
    if score >= 95.0:
        return "CAPITAL_ACCOUNT_ACTIVATION_CLEAR"
    if score >= 91.0:
        return "ACTIVATION_WATCH"
    return "ACTIVATION_REMEDIATION_REQUIRED"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _onboarding_context(email)

    onboarding_completion = float(payload.get("onboarding_completion", 0.0) or 0.0)
    subscription_completion = float(payload.get("subscription_completion", 0.0) or 0.0)
    identity_completion = float(payload.get("identity_completion", 0.0) or 0.0)
    funding_readiness = float(payload.get("funding_readiness", 0.0) or 0.0)
    capital_activation_readiness = float(payload.get("capital_activation_readiness", 0.0) or 0.0)
    open_exceptions = int(payload.get("open_exceptions", 0) or 0)
    pending_documents = int(payload.get("pending_documents", 0) or 0)

    score = 100.0
    reasons = []
    alerts = []

    def penalize(metric: float, minimum: float, weight: float, reason: str, code: str):
        nonlocal score
        if metric < minimum:
            score -= round((minimum - metric) * weight, 2)
            reasons.append(reason)
            alerts.append(code)

    penalize(onboarding_completion, float(policy.get("minimum_onboarding_completion", 0.95)), 120.0, "onboarding completion is below policy", "ONBOARDING_COMPLETION_WEAK")
    penalize(subscription_completion, float(policy.get("minimum_subscription_completion", 0.95)), 115.0, "subscription document completion is below policy", "SUBSCRIPTION_COMPLETION_WEAK")
    penalize(identity_completion, float(policy.get("minimum_identity_completion", 0.95)), 110.0, "identity completion is below policy", "IDENTITY_COMPLETION_WEAK")
    penalize(funding_readiness, float(policy.get("minimum_funding_readiness", 0.95)), 100.0, "funding readiness is below policy", "FUNDING_READINESS_WEAK")
    penalize(capital_activation_readiness, float(policy.get("minimum_capital_activation_readiness", 0.95)), 125.0, "capital activation readiness is below policy", "CAPITAL_ACTIVATION_WEAK")

    if open_exceptions > int(policy.get("maximum_open_exceptions", 0)):
        score -= min(open_exceptions * 8.0, 24.0)
        reasons.append("open onboarding or compliance exceptions remain unresolved")
        alerts.append("OPEN_EXCEPTIONS")
    if pending_documents > int(policy.get("maximum_pending_documents", 1)):
        score -= min((pending_documents - int(policy.get("maximum_pending_documents", 1))) * 6.0, 18.0)
        reasons.append("pending documents exceed policy")
        alerts.append("PENDING_DOCUMENTS_EXCEED_POLICY")

    onboarding_ready = (ctx.get("onboarding_summary") or {}).get("active_count", 0) > 0
    subscription_ready = (ctx.get("subscription_summary") or {}).get("signed_documents", 0) >= 4
    identity_ready = (ctx.get("identity_summary") or {}).get("approved_documents", 0) >= 4
    funding_ready = (ctx.get("funding_summary") or {}).get("payment_methods", 0) > 0 and str((ctx.get("funding_summary") or {}).get("kyc_status") or "").startswith("approved")
    capital_ready = (ctx.get("capital_summary") or {}).get("account_count", 0) > 0 and (ctx.get("capital_summary") or {}).get("entry_count", 0) > 0

    if policy.get("require_onboarding_ready", True) and not onboarding_ready:
        score -= 8.0
        reasons.append("investor onboarding is not sufficiently initialized")
        alerts.append("ONBOARDING_NOT_READY")
    if policy.get("require_subscription_ready", True) and not subscription_ready:
        score -= 8.0
        reasons.append("subscription document execution is not sufficiently initialized")
        alerts.append("SUBSCRIPTION_NOT_READY")
    if policy.get("require_identity_ready", True) and not identity_ready:
        score -= 8.0
        reasons.append("identity review is not sufficiently initialized")
        alerts.append("IDENTITY_NOT_READY")
    if policy.get("require_funding_ready", True) and not funding_ready:
        score -= 8.0
        reasons.append("funding rails are not sufficiently initialized")
        alerts.append("FUNDING_NOT_READY")
    if policy.get("require_capital_account_ready", True) and not capital_ready:
        score -= 8.0
        reasons.append("capital account activation is not sufficiently initialized")
        alerts.append("CAPITAL_ACCOUNT_NOT_READY")

    score = max(round(score, 2), 0.0)
    band = _band(score)
    posture = "CAPITAL_ACCOUNT_ACTIVATION_CLEAR" if score >= float(policy.get("minimum_score", 95.0)) else ("ACTIVATION_WATCH" if score >= 91.0 else "ACTIVATION_REMEDIATION_REQUIRED")
    operator_review_required = posture != "CAPITAL_ACCOUNT_ACTIVATION_CLEAR" or open_exceptions > 0 or pending_documents > int(policy.get("maximum_pending_documents", 1))

    row = {
        "mission": "QNT40004",
        "evaluated_at": _now_iso(),
        "score": score,
        "band": band,
        "posture": posture,
        "operator_review_required": operator_review_required,
        "onboarding_completion": onboarding_completion,
        "subscription_completion": subscription_completion,
        "identity_completion": identity_completion,
        "funding_readiness": funding_readiness,
        "capital_activation_readiness": capital_activation_readiness,
        "open_exceptions": open_exceptions,
        "pending_documents": pending_documents,
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
        "capital_ledger": _capital().capital_ledger_summary(),
    }


@router.post("/evaluate")
def evaluate(payload: dict = Body(...), user=Depends(_require_user)):
    email = (user or {}).get("email")
    if not email:
        raise HTTPException(status_code=401, detail="session required")
    return {"ok": True, "run": _evaluate(email, payload), **_summary_for_email(email)}


@router.post("/create-onboarding-case")
def create_onboarding_case(payload: dict = Body(None), user=Depends(_require_user)):
    email = (user or {}).get("email")
    if not email:
        raise HTTPException(status_code=401, detail="session required")
    investor_id = str((payload or {}).get("investor_id") or "lp_activation_001")
    result = _onboarding().create_investor({
        "investor_id": investor_id,
        "name": str((payload or {}).get("name") or "Institutional LP One"),
        "commitment": float((payload or {}).get("commitment") or 500000.0),
    })
    inv = result.get("investor") or {}
    row = {
        "captured_at": _now_iso(),
        "investor_id": inv.get("investor_id"),
        "status": inv.get("status"),
        "commitment": inv.get("commitment", 0.0),
    }
    store = _load(email)
    _append(store, "onboarding_events", row, (store.get("policy") or {}).get("retain_cycles", 365))
    _save(email, store)
    return {"ok": True, "onboarding_event": row, "investor": inv}


@router.post("/send-subscription-documents")
def send_subscription_documents(payload: dict = Body(None), user=Depends(_require_user)):
    email = (user or {}).get("email")
    if not email:
        raise HTTPException(status_code=401, detail="session required")
    sent = []
    signed = []
    for doc_type in ["subscription_agreement", "investor_questionnaire", "risk_acknowledgement", "signature_packet"]:
        sent.append(_subscription().subscription_send({"doc_type": doc_type, "notes": "activation packet dispatched"}).get("document") or {})
        signed.append(_subscription().subscription_sign({"doc_type": doc_type, "notes": "simulated lp signature"}).get("document") or {})
    row = {
        "captured_at": _now_iso(),
        "sent_documents": len([d for d in sent if d]),
        "signed_documents": len([d for d in signed if d]),
    }
    store = _load(email)
    _append(store, "subscription_events", row, (store.get("policy") or {}).get("retain_cycles", 365))
    _save(email, store)
    return {"ok": True, "subscription_event": row, "documents": signed}


@router.post("/activate-capital-account")
def activate_capital_account(payload: dict = Body(None), user=Depends(_require_user)):
    email = (user or {}).get("email")
    if not email:
        raise HTTPException(status_code=401, detail="session required")
    investor_id = str((payload or {}).get("investor_id") or "lp_activation_001")
    account = _capital().create_account({
        "investor_id": investor_id,
        "committed_capital": float((payload or {}).get("committed_capital") or 500000.0),
    })
    entry = _capital().add_entry({
        "investor_id": investor_id,
        "amount": float((payload or {}).get("funded_capital") or 250000.0),
        "entry_type": "funding",
        "description": str((payload or {}).get("description") or "initial capital activation"),
    })
    recalc = _capital().recalculate()
    row = {
        "captured_at": _now_iso(),
        "investor_id": investor_id,
        "committed_capital": (account.get("account") or {}).get("committed_capital", 0.0),
        "funded_amount": (entry.get("entry") or {}).get("amount", 0.0),
        "total_nav": recalc.get("summary", {}).get("total_nav", 0.0),
    }
    store = _load(email)
    _append(store, "capital_activation_events", row, (store.get("policy") or {}).get("retain_cycles", 365))
    _save(email, store)
    return {"ok": True, "capital_activation_event": row, "account": account, "entry": entry, "recalculation": recalc}


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

    investor_id = "lp_activation_001"
    create_onboarding_case({"investor_id": investor_id, "name": "Institutional LP One", "commitment": 500000.0}, user)

    for item in ["nda_signed", "subscription_agreement", "kyc_completed", "accreditation_verified", "capital_commitment"]:
        _onboarding().update_checklist({"investor_id": investor_id, "item": item, "value": True})

    for doc_type in ["government_id", "proof_of_address", "accreditation", "tax_form"]:
        _identity().identity_vault_upload({"doc_type": doc_type, "notes": "bootstrap upload"})
        _identity().identity_vault_review({"doc_type": doc_type, "decision": "approved", "notes": "bootstrap approval"})
    store = _load(email)
    _append(store, "identity_events", {
        "captured_at": _now_iso(),
        "approved_documents": 4,
        "status": "identity_complete",
    }, (store.get("policy") or {}).get("retain_cycles", 365))
    _save(email, store)

    _funding().user_funding_add_method({"method_type": "wire", "nickname": "LP Operating Wire"})
    _funding().user_funding_kyc_start()
    _funding().user_funding_kyc_approve()
    intent = _funding().user_funding_deposit_intent({"amount": 250000.0})
    _funding().user_funding_deposit_confirm({"intent_id": (intent.get("intent") or {}).get("intent_id")})
    store = _load(email)
    _append(store, "funding_events", {
        "captured_at": _now_iso(),
        "funding_status": "capital_received",
        "completed_amount": 250000.0,
    }, (store.get("policy") or {}).get("retain_cycles", 365))
    _save(email, store)

    subscription_result = send_subscription_documents({}, user)
    capital_result = activate_capital_account({"investor_id": investor_id, "committed_capital": 500000.0, "funded_capital": 250000.0}, user)

    run = _evaluate(email, {
        "onboarding_completion": 0.99,
        "subscription_completion": 0.99,
        "identity_completion": 0.99,
        "funding_readiness": 0.98,
        "capital_activation_readiness": 0.98,
        "open_exceptions": 0,
        "pending_documents": 0,
    })
    return {
        "ok": True,
        "run": run,
        "subscription_event": subscription_result.get("subscription_event"),
        "capital_activation_event": capital_result.get("capital_activation_event"),
        **_summary_for_email(email),
    }
