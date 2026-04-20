from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(
    prefix="/api/investor-commitments-subscription-acceptance-capital-call-scheduling-layer",
    tags=["investor-commitments-subscription-acceptance-capital-call-scheduling-layer"],
)

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "investor_commitments_subscription_acceptance_capital_call_scheduling_layer"
DEFAULT_POLICY = {
    "retain_cycles": 365,
    "minimum_score": 95.0,
    "minimum_commitment_coverage": 0.95,
    "minimum_subscription_acceptance_readiness": 0.95,
    "minimum_capital_call_schedule_readiness": 0.95,
    "maximum_open_exceptions": 0,
    "maximum_pending_notices": 1,
    "require_active_onboarding": True,
    "require_signed_subscription": True,
    "require_admission_record": True,
    "require_capital_call_notice": True,
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


def _capital_calls():
    from backend.app import qnt30579_capital_call_router as module
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
            "commitment_events": [],
            "subscription_acceptance_events": [],
            "capital_call_schedule_events": [],
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
    capital_calls = _capital_calls().capital_calls_summary()
    fund_close = _fund_close().fund_close_summary()

    investors = onboarding.get("investors") or []
    active_investors = [i for i in investors if i.get("status") == "active"]
    docs = subscription.get("documents") or []
    signed_docs = [d for d in docs if str(d.get("status")) == "signed"]
    calls = capital_calls.get("notices") or []
    issued_calls = [n for n in calls if str(n.get("status")) == "issued"]
    paid_calls = [n for n in calls if str(n.get("status")).startswith("paid")]
    entries = fund_close.get("entries") or []
    admitted_entries = [e for e in entries if e.get("status") == "admitted"]

    return {
        "captured_at": _now_iso(),
        "onboarding_summary": {
            "investor_count": onboarding.get("investor_count", 0),
            "active_count": onboarding.get("active_count", 0),
            "total_commitment": onboarding.get("total_commitment", 0.0),
            "latest_investor_id": (active_investors[0] if active_investors else (investors[0] if investors else {})).get("investor_id"),
        },
        "subscription_summary": {
            "signed_documents": subscription.get("signed_documents", 0),
            "awaiting_signature_documents": subscription.get("awaiting_signature_documents", 0),
            "signed_ratio": round((len(signed_docs) / max(len(docs), 1)), 4),
        },
        "capital_call_summary": {
            "total_notices": capital_calls.get("total_notices", 0),
            "issued_notices": capital_calls.get("issued_notices", 0),
            "paid_notices": capital_calls.get("paid_notices", 0),
            "total_amount": capital_calls.get("total_amount", 0.0),
            "paid_amount": capital_calls.get("paid_amount", 0.0),
            "outstanding_amount": round(float(capital_calls.get("total_amount", 0.0)) - float(capital_calls.get("paid_amount", 0.0)), 2),
            "issued_call_count": len(issued_calls),
            "paid_call_count": len(paid_calls),
        },
        "admission_summary": {
            "total_entries": fund_close.get("total_entries", 0),
            "pending_entries": fund_close.get("pending_entries", 0),
            "admitted_entries": fund_close.get("admitted_entries", 0),
            "admitted_capital": fund_close.get("admitted_capital", 0.0),
            "latest_entry_id": (admitted_entries[0] if admitted_entries else (entries[0] if entries else {})).get("entry_id"),
        },
    }


def _summary_for_email(email: str) -> dict:
    s = _load(email)
    latest = s.get("latest_run") or {}
    return {
        "investor_commitments_subscription_acceptance_capital_call_scheduling_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "commitment_event_count": len(s.get("commitment_events") or []),
            "subscription_acceptance_event_count": len(s.get("subscription_acceptance_events") or []),
            "capital_call_schedule_event_count": len(s.get("capital_call_schedule_events") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "commitment_events": s.get("commitment_events") or [],
        "subscription_acceptance_events": s.get("subscription_acceptance_events") or [],
        "capital_call_schedule_events": s.get("capital_call_schedule_events") or [],
    }


def _band(score: float) -> str:
    if score >= 98.0:
        return "INSTITUTIONAL_CAPITAL_CALL_READY"
    if score >= 95.0:
        return "CAPITAL_CALL_SCHEDULING_CLEAR"
    if score >= 91.0:
        return "SCHEDULING_WATCH"
    return "SCHEDULING_REMEDIATION_REQUIRED"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _context(email)

    commitment_coverage = float(payload.get("commitment_coverage", 0.0) or 0.0)
    subscription_acceptance_readiness = float(payload.get("subscription_acceptance_readiness", 0.0) or 0.0)
    capital_call_schedule_readiness = float(payload.get("capital_call_schedule_readiness", 0.0) or 0.0)
    open_exceptions = int(payload.get("open_exceptions", 0) or 0)
    pending_notices = int(payload.get("pending_notices", 0) or 0)

    score = 100.0
    reasons = []
    alerts = []

    def penalize(metric: float, minimum: float, weight: float, reason: str, code: str):
        nonlocal score
        if metric < minimum:
            score -= round((minimum - metric) * weight, 2)
            reasons.append(reason)
            alerts.append(code)

    penalize(commitment_coverage, float(policy.get("minimum_commitment_coverage", 0.95)), 120.0, "commitment coverage is below policy", "COMMITMENT_COVERAGE_WEAK")
    penalize(subscription_acceptance_readiness, float(policy.get("minimum_subscription_acceptance_readiness", 0.95)), 115.0, "subscription acceptance readiness is below policy", "SUBSCRIPTION_ACCEPTANCE_WEAK")
    penalize(capital_call_schedule_readiness, float(policy.get("minimum_capital_call_schedule_readiness", 0.95)), 125.0, "capital call scheduling readiness is below policy", "CAPITAL_CALL_SCHEDULE_WEAK")

    if open_exceptions > int(policy.get("maximum_open_exceptions", 0)):
        score -= min(open_exceptions * 8.0, 24.0)
        reasons.append("open investor-admission or funding exceptions remain unresolved")
        alerts.append("OPEN_EXCEPTIONS")
    if pending_notices > int(policy.get("maximum_pending_notices", 1)):
        score -= min((pending_notices - int(policy.get("maximum_pending_notices", 1))) * 6.0, 18.0)
        reasons.append("pending capital call notices exceed policy")
        alerts.append("PENDING_NOTICES_EXCEED_POLICY")

    active_onboarding = (ctx.get("onboarding_summary") or {}).get("active_count", 0) > 0
    signed_subscription = (ctx.get("subscription_summary") or {}).get("signed_documents", 0) >= 4
    admission_record = (ctx.get("admission_summary") or {}).get("admitted_entries", 0) > 0
    capital_call_notice = (ctx.get("capital_call_summary") or {}).get("total_notices", 0) > 0

    if policy.get("require_active_onboarding", True) and not active_onboarding:
        score -= 8.0
        reasons.append("active onboarding record is not available")
        alerts.append("ONBOARDING_NOT_ACTIVE")
    if policy.get("require_signed_subscription", True) and not signed_subscription:
        score -= 8.0
        reasons.append("signed subscription packet is incomplete")
        alerts.append("SUBSCRIPTION_NOT_SIGNED")
    if policy.get("require_admission_record", True) and not admission_record:
        score -= 8.0
        reasons.append("admission record is not available")
        alerts.append("ADMISSION_RECORD_MISSING")
    if policy.get("require_capital_call_notice", True) and not capital_call_notice:
        score -= 8.0
        reasons.append("capital call schedule has not been issued")
        alerts.append("CAPITAL_CALL_NOTICE_MISSING")

    score = max(round(score, 2), 0.0)
    posture = _band(score)
    operator_review_required = score < float(policy.get("minimum_score", 95.0)) or bool(alerts)
    run = {
        "captured_at": _now_iso(),
        "score": score,
        "band": _band(score),
        "posture": posture,
        "reasons": reasons,
        "alerts": alerts,
        "operator_review_required": operator_review_required,
        "metrics": {
            "commitment_coverage": commitment_coverage,
            "subscription_acceptance_readiness": subscription_acceptance_readiness,
            "capital_call_schedule_readiness": capital_call_schedule_readiness,
            "open_exceptions": open_exceptions,
            "pending_notices": pending_notices,
        },
    }
    _append(store, "runs", run, int(policy.get("retain_cycles", 365)))
    store["latest_run"] = run
    store["last_context"] = ctx
    if alerts:
        _append(store, "alerts", {
            "captured_at": _now_iso(),
            "alerts": alerts,
            "score": score,
            "posture": posture,
        }, int(policy.get("retain_cycles", 365)))
    _save(email, store)
    return run


@router.get("/summary")
def summary(user=Depends(_require_user)):
    return _summary_for_email(user.get("email"))


@router.post("/evaluate")
def evaluate(payload: dict = Body(...), user=Depends(_require_user)):
    return _evaluate(user.get("email"), payload)


@router.post("/record-commitment")
def record_commitment(payload: dict = Body(...), user=Depends(_require_user)):
    email = user.get("email")
    store = _load(email)
    investor_id = str(payload.get("investor_id") or f"inv_commit_{int(datetime.now(timezone.utc).timestamp())}")
    event = {
        "commitment_id": f"commit_{int(datetime.now(timezone.utc).timestamp())}",
        "investor_id": investor_id,
        "commitment_amount": round(float(payload.get("commitment_amount") or 0.0), 2),
        "currency": str(payload.get("currency") or "USD"),
        "captured_at": _now_iso(),
        "notes": str(payload.get("notes") or ""),
    }
    _append(store, "commitment_events", event, int((store.get("policy") or DEFAULT_POLICY).get("retain_cycles", 365)))
    _save(email, store)
    return {"ok": True, "event": event}


@router.post("/accept-subscription")
def accept_subscription(payload: dict = Body(...), user=Depends(_require_user)):
    email = user.get("email")
    store = _load(email)
    event = {
        "acceptance_id": f"accept_{int(datetime.now(timezone.utc).timestamp())}",
        "subscription_packet": str(payload.get("subscription_packet") or "default_packet"),
        "accepted_at": _now_iso(),
        "accepted_by": email,
        "notes": str(payload.get("notes") or ""),
    }
    _append(store, "subscription_acceptance_events", event, int((store.get("policy") or DEFAULT_POLICY).get("retain_cycles", 365)))
    _save(email, store)
    return {"ok": True, "event": event}


@router.post("/schedule-capital-call")
def schedule_capital_call(payload: dict = Body(...), user=Depends(_require_user)):
    email = user.get("email")
    store = _load(email)
    event = {
        "schedule_id": f"sched_{int(datetime.now(timezone.utc).timestamp())}",
        "amount": round(float(payload.get("amount") or 0.0), 2),
        "due_date": str(payload.get("due_date") or ""),
        "scheduled_at": _now_iso(),
        "notes": str(payload.get("notes") or ""),
    }
    _append(store, "capital_call_schedule_events", event, int((store.get("policy") or DEFAULT_POLICY).get("retain_cycles", 365)))
    _save(email, store)
    return {"ok": True, "event": event}


@router.get("/policy")
def policy(user=Depends(_require_user)):
    return {"policy": _load(user.get("email")).get("policy") or dict(DEFAULT_POLICY)}


@router.post("/policy")
def update_policy(payload: dict = Body(...), user=Depends(_require_user)):
    email = user.get("email")
    store = _load(email)
    store["policy"] = {**dict(DEFAULT_POLICY), **(store.get("policy") or {}), **payload}
    _save(email, store)
    return {"ok": True, "policy": store["policy"]}


@router.post("/bootstrap-demo")
def bootstrap_demo(user=Depends(_require_user)):
    email = user.get("email")
    # seed investor and make active
    inv = _onboarding().create_investor({"investor_id": "inv_qnt40006", "name": "Quantora LP", "commitment": 250000.0})
    for item in ["nda_signed", "subscription_agreement", "kyc_completed", "accreditation_verified", "capital_commitment"]:
        _onboarding().update_checklist({"investor_id": inv["investor"]["investor_id"], "item": item, "value": True})
    for doc_type in ["subscription_agreement", "investor_questionnaire", "risk_acknowledgement", "signature_packet"]:
        _subscription().subscription_send({"doc_type": doc_type, "notes": "bootstrap send"})
        _subscription().subscription_sign({"doc_type": doc_type, "notes": "bootstrap sign"})
    _fund_close().fund_close_create({"email": email, "admitted_capital": 250000.0, "title": "Initial LP Admission", "notes": "bootstrap admission"})
    fc = _fund_close().fund_close_summary()
    first_entry = (fc.get("entries") or [{}])[0]
    if first_entry.get("entry_id"):
        _fund_close().fund_close_admit({"entry_id": first_entry.get("entry_id"), "notes": "bootstrap admit"})
    _capital_calls().capital_calls_create({"email": email, "amount": 50000.0, "due_date": "2026-04-30", "title": "Initial Capital Call", "notes": "bootstrap schedule"})
    record_commitment({"investor_id": "inv_qnt40006", "commitment_amount": 250000.0, "currency": "USD", "notes": "bootstrap commitment"}, user)
    accept_subscription({"subscription_packet": "initial_lp_packet", "notes": "bootstrap acceptance"}, user)
    schedule_capital_call({"amount": 50000.0, "due_date": "2026-04-30", "notes": "bootstrap schedule"}, user)
    run = _evaluate(email, {
        "commitment_coverage": 1.0,
        "subscription_acceptance_readiness": 1.0,
        "capital_call_schedule_readiness": 0.98,
        "open_exceptions": 0,
        "pending_notices": 1,
    })
    return {"ok": True, "run": run, "summary": _summary_for_email(email)}
