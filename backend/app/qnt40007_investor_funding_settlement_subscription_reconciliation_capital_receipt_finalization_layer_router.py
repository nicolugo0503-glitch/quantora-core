from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(
    prefix="/api/investor-funding-settlement-subscription-reconciliation-capital-receipt-finalization-layer",
    tags=["investor-funding-settlement-subscription-reconciliation-capital-receipt-finalization-layer"],
)

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "investor_funding_settlement_subscription_reconciliation_capital_receipt_finalization_layer"
DEFAULT_POLICY = {
    "retain_cycles": 365,
    "minimum_score": 95.0,
    "minimum_settlement_readiness": 0.95,
    "minimum_reconciliation_readiness": 0.95,
    "minimum_receipt_finalization_readiness": 0.95,
    "maximum_unreconciled_items": 0,
    "maximum_outstanding_receipts": 0,
    "require_paid_capital_call": True,
    "require_completed_funding": True,
    "require_capital_ledger_entry": True,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _require_user():
    return _mu()._require_session()


def _capital_calls():
    from backend.app import qnt30579_capital_call_router as module
    return module


def _funding():
    from backend.app import qnt30565_funding_router as module
    return module


def _capital_ledger():
    from backend.app import qnt30624_capital_ledger_router as module
    return module


def _capital_activity():
    from backend.app import qnt30595_capital_activity_router as module
    return module


def _commitments_layer():
    from backend.app import qnt40006_investor_commitments_subscription_acceptance_capital_call_scheduling_layer_router as module
    return module


def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]


def _path(email: str) -> Path:
    ENGINE_DIR.mkdir(parents=True, exist_ok=True)
    return ENGINE_DIR / f"{_safe(email)}.json"


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
            "funding_settlement_events": [],
            "subscription_reconciliation_events": [],
            "capital_receipt_finalization_events": [],
            "latest_run": None,
            "last_context": {},
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))


def _save(email: str, data: dict):
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")


def _context(email: str) -> dict:
    commitments = _commitments_layer().summary({"email": email})
    calls = _capital_calls().capital_calls_summary()
    funding = _funding().user_funding_summary()
    ledger = _capital_ledger().capital_ledger_summary()
    activity = _capital_activity().capital_activity_summary()

    notices = calls.get("notices") or []
    paid_notices = [n for n in notices if str(n.get("status", "")).startswith("paid")]
    profile = funding.get("profile") or {}
    intents = (funding.get("recent_intents") or [])
    completed_intents = [i for i in intents if i.get("status") == "completed"]
    entries = ledger.get("entries") or []
    funding_entries = [e for e in entries if str(e.get("entry_type")) in {"funding", "subscription_receipt"}]
    processed_requests = [r for r in (activity.get("requests") or []) if r.get("status") == "processed"]

    return {
        "captured_at": _now_iso(),
        "commitments_layer_status": (commitments.get("investor_commitments_subscription_acceptance_capital_call_scheduling_layer_status") or {}),
        "capital_call_summary": {
            "total_notices": calls.get("total_notices", 0),
            "issued_notices": calls.get("issued_notices", 0),
            "paid_notices": calls.get("paid_notices", 0),
            "total_amount": calls.get("total_amount", 0.0),
            "paid_amount": calls.get("paid_amount", 0.0),
            "latest_notice_id": (paid_notices[0] if paid_notices else (notices[0] if notices else {})).get("notice_id"),
        },
        "funding_summary": {
            "funding_status": profile.get("funding_status"),
            "kyc_status": profile.get("kyc_status"),
            "payment_method_count": len(profile.get("payment_methods") or []),
            "intent_count": len(intents),
            "completed_intent_count": len(completed_intents),
            "completed_amount": round(sum(float(i.get("amount") or 0.0) for i in completed_intents), 2),
            "latest_completed_intent_id": (completed_intents[0] if completed_intents else {}).get("intent_id"),
        },
        "capital_ledger_summary": {
            "account_count": ledger.get("account_count", 0),
            "entry_count": ledger.get("entry_count", 0),
            "allocation_count": ledger.get("allocation_count", 0),
            "total_committed_capital": ledger.get("total_committed_capital", 0.0),
            "total_funded_capital": ledger.get("total_funded_capital", 0.0),
            "total_unfunded_capital": ledger.get("total_unfunded_capital", 0.0),
            "latest_account_id": (ledger.get("latest_account") or {}).get("account_id"),
            "latest_funding_entry_id": (funding_entries[0] if funding_entries else (entries[0] if entries else {})).get("entry_id"),
        },
        "capital_activity_summary": {
            "request_count": activity.get("request_count", 0),
            "processed_count": activity.get("processed_count", 0),
            "total_subscriptions": activity.get("total_subscriptions", 0.0),
            "total_redemptions": activity.get("total_redemptions", 0.0),
            "latest_processed_request_id": (processed_requests[0] if processed_requests else {}).get("request_id"),
        },
    }


def _summary_for_email(email: str) -> dict:
    s = _load(email)
    latest = s.get("latest_run") or {}
    return {
        "investor_funding_settlement_subscription_reconciliation_capital_receipt_finalization_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "funding_settlement_event_count": len(s.get("funding_settlement_events") or []),
            "subscription_reconciliation_event_count": len(s.get("subscription_reconciliation_events") or []),
            "capital_receipt_finalization_event_count": len(s.get("capital_receipt_finalization_events") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "funding_settlement_events": s.get("funding_settlement_events") or [],
        "subscription_reconciliation_events": s.get("subscription_reconciliation_events") or [],
        "capital_receipt_finalization_events": s.get("capital_receipt_finalization_events") or [],
    }


def _band(score: float) -> str:
    if score >= 98.0:
        return "INSTITUTIONAL_RECEIPT_FINALIZED"
    if score >= 95.0:
        return "CAPITAL_RECEIPT_FINALIZATION_CLEAR"
    if score >= 91.0:
        return "RECEIPT_RECONCILIATION_WATCH"
    return "RECEIPT_REMEDIATION_REQUIRED"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _context(email)

    settlement_readiness = float(payload.get("settlement_readiness", 0.0) or 0.0)
    reconciliation_readiness = float(payload.get("reconciliation_readiness", 0.0) or 0.0)
    receipt_finalization_readiness = float(payload.get("receipt_finalization_readiness", 0.0) or 0.0)
    unreconciled_items = int(payload.get("unreconciled_items", 0) or 0)
    outstanding_receipts = int(payload.get("outstanding_receipts", 0) or 0)

    score = 100.0
    reasons = []
    alerts = []

    def penalize(metric: float, minimum: float, weight: float, reason: str, code: str):
        nonlocal score
        if metric < minimum:
            score -= round((minimum - metric) * weight, 2)
            reasons.append(reason)
            alerts.append(code)

    penalize(settlement_readiness, float(policy.get("minimum_settlement_readiness", 0.95)), 120.0, "funding settlement readiness is below policy", "SETTLEMENT_READINESS_WEAK")
    penalize(reconciliation_readiness, float(policy.get("minimum_reconciliation_readiness", 0.95)), 120.0, "subscription reconciliation readiness is below policy", "RECONCILIATION_READINESS_WEAK")
    penalize(receipt_finalization_readiness, float(policy.get("minimum_receipt_finalization_readiness", 0.95)), 125.0, "capital receipt finalization readiness is below policy", "RECEIPT_FINALIZATION_WEAK")

    if unreconciled_items > int(policy.get("maximum_unreconciled_items", 0)):
        score -= min(unreconciled_items * 8.0, 24.0)
        reasons.append("unreconciled subscription items remain open")
        alerts.append("UNRECONCILED_ITEMS")
    if outstanding_receipts > int(policy.get("maximum_outstanding_receipts", 0)):
        score -= min(outstanding_receipts * 8.0, 24.0)
        reasons.append("outstanding capital receipts remain unresolved")
        alerts.append("OUTSTANDING_RECEIPTS")

    paid_capital_call = (ctx.get("capital_call_summary") or {}).get("paid_notices", 0) > 0
    completed_funding = (ctx.get("funding_summary") or {}).get("completed_intent_count", 0) > 0
    capital_ledger_entry = (ctx.get("capital_ledger_summary") or {}).get("entry_count", 0) > 0

    if policy.get("require_paid_capital_call", True) and not paid_capital_call:
        score -= 8.0
        reasons.append("paid capital call record is not available")
        alerts.append("PAID_CAPITAL_CALL_MISSING")
    if policy.get("require_completed_funding", True) and not completed_funding:
        score -= 8.0
        reasons.append("completed funding settlement is not available")
        alerts.append("FUNDING_SETTLEMENT_MISSING")
    if policy.get("require_capital_ledger_entry", True) and not capital_ledger_entry:
        score -= 8.0
        reasons.append("capital ledger receipt entry is not available")
        alerts.append("CAPITAL_LEDGER_ENTRY_MISSING")

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
            "settlement_readiness": settlement_readiness,
            "reconciliation_readiness": reconciliation_readiness,
            "receipt_finalization_readiness": receipt_finalization_readiness,
            "unreconciled_items": unreconciled_items,
            "outstanding_receipts": outstanding_receipts,
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


@router.post("/record-funding-settlement")
def record_funding_settlement(payload: dict = Body(...), user=Depends(_require_user)):
    email = user.get("email")
    store = _load(email)
    event = {
        "settlement_id": f"settle_{int(datetime.now(timezone.utc).timestamp())}",
        "notice_id": str(payload.get("notice_id") or ""),
        "intent_id": str(payload.get("intent_id") or ""),
        "amount": round(float(payload.get("amount") or 0.0), 2),
        "currency": str(payload.get("currency") or "USD"),
        "settled_at": _now_iso(),
        "notes": str(payload.get("notes") or ""),
    }
    _append(store, "funding_settlement_events", event, int((store.get("policy") or DEFAULT_POLICY).get("retain_cycles", 365)))
    _save(email, store)
    return {"ok": True, "event": event}


@router.post("/reconcile-subscription")
def reconcile_subscription(payload: dict = Body(...), user=Depends(_require_user)):
    email = user.get("email")
    store = _load(email)
    event = {
        "reconciliation_id": f"recon_{int(datetime.now(timezone.utc).timestamp())}",
        "investor_id": str(payload.get("investor_id") or ""),
        "matched_amount": round(float(payload.get("matched_amount") or 0.0), 2),
        "variance_amount": round(float(payload.get("variance_amount") or 0.0), 2),
        "reconciled_at": _now_iso(),
        "notes": str(payload.get("notes") or ""),
    }
    _append(store, "subscription_reconciliation_events", event, int((store.get("policy") or DEFAULT_POLICY).get("retain_cycles", 365)))
    _save(email, store)
    return {"ok": True, "event": event}


@router.post("/finalize-capital-receipt")
def finalize_capital_receipt(payload: dict = Body(...), user=Depends(_require_user)):
    email = user.get("email")
    store = _load(email)
    event = {
        "receipt_id": f"receipt_{int(datetime.now(timezone.utc).timestamp())}",
        "investor_id": str(payload.get("investor_id") or ""),
        "ledger_entry_id": str(payload.get("ledger_entry_id") or ""),
        "finalized_amount": round(float(payload.get("finalized_amount") or 0.0), 2),
        "finalized_at": _now_iso(),
        "notes": str(payload.get("notes") or ""),
    }
    _append(store, "capital_receipt_finalization_events", event, int((store.get("policy") or DEFAULT_POLICY).get("retain_cycles", 365)))
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
    _commitments_layer().bootstrap_demo(user)

    profile = _funding().user_funding_profile()
    if not profile.get("payment_methods"):
        _funding().user_funding_add_method({"method_type": "wire", "nickname": "Primary LP Wire"})
    if profile.get("kyc_status") != "approved_simulated":
        _funding().user_funding_kyc_start()
        _funding().user_funding_kyc_approve()

    calls = _capital_calls().capital_calls_summary()
    notices = calls.get("notices") or []
    paid_notice = next((n for n in notices if str(n.get("status", "")).startswith("paid")), None)
    target_notice = paid_notice or (notices[0] if notices else None)
    if target_notice and not str(target_notice.get("status", "")).startswith("paid"):
        _capital_calls().capital_calls_pay({"notice_id": target_notice.get("notice_id")})
        calls = _capital_calls().capital_calls_summary()
        notices = calls.get("notices") or []
        target_notice = next((n for n in notices if str(n.get("status", "")).startswith("paid")), target_notice)

    funding = _funding().user_funding_summary()
    if funding.get("completed_intent_count", 0) == 0:
        intent_resp = _funding().user_funding_deposit_intent({"amount": 50000.0})
        _funding().user_funding_deposit_confirm({"intent_id": intent_resp["intent"]["intent_id"]})
        funding = _funding().user_funding_summary()

    ledger = _capital_ledger().capital_ledger_summary()
    investor_id = "inv_qnt40006"
    if ledger.get("account_count", 0) == 0:
        _capital_ledger().create_account({"investor_id": investor_id, "committed_capital": 250000.0})
    ledger = _capital_ledger().capital_ledger_summary()
    if ledger.get("entry_count", 0) == 0:
        _capital_ledger().add_entry({
            "investor_id": investor_id,
            "entry_type": "funding",
            "amount": 50000.0,
            "description": "bootstrap capital receipt",
        })
        _capital_ledger().recalculate()
        ledger = _capital_ledger().capital_ledger_summary()

    activities = _capital_activity().capital_activity_summary()
    if activities.get("processed_count", 0) == 0:
        req = _capital_activity().capital_activity_request({"activity_type": "subscription", "amount": 50000.0, "notes": "bootstrap subscription"})
        _capital_activity().capital_activity_review({"email": email, "request_id": req["request"]["request_id"], "decision": "approved", "notes": "bootstrap approve"})
        _capital_activity().capital_activity_process({"request_id": req["request"]["request_id"], "notes": "bootstrap process"})
        activities = _capital_activity().capital_activity_summary()

    funding_summary = _funding().user_funding_summary()
    paid_notice = next((n for n in (_capital_calls().capital_calls_summary().get("notices") or []) if str(n.get("status", "")).startswith("paid")), None)
    completed_intent = next((i for i in (funding_summary.get("recent_intents") or []) if i.get("status") == "completed"), None)
    latest_entry = (_capital_ledger().capital_ledger_summary().get("latest_entry") or {})

    record_funding_settlement({
        "notice_id": (paid_notice or {}).get("notice_id", ""),
        "intent_id": (completed_intent or {}).get("intent_id", ""),
        "amount": 50000.0,
        "currency": "USD",
        "notes": "bootstrap settlement",
    }, user)
    reconcile_subscription({
        "investor_id": investor_id,
        "matched_amount": 50000.0,
        "variance_amount": 0.0,
        "notes": "bootstrap reconciliation",
    }, user)
    finalize_capital_receipt({
        "investor_id": investor_id,
        "ledger_entry_id": latest_entry.get("entry_id", ""),
        "finalized_amount": 50000.0,
        "notes": "bootstrap receipt finalization",
    }, user)

    run = _evaluate(email, {
        "settlement_readiness": 0.99,
        "reconciliation_readiness": 0.99,
        "receipt_finalization_readiness": 0.99,
        "unreconciled_items": 0,
        "outstanding_receipts": 0,
    })
    return {"ok": True, "run": run, "summary": _summary_for_email(email)}
