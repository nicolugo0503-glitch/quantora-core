from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(prefix="/api/institutional-treasury-confirmation-layer", tags=["institutional-treasury-confirmation-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "institutional_treasury_confirmation_layer"
DEFAULT_POLICY = {
    "retain_cycles": 180,
    "minimum_score": 96.0,
    "require_operator_clear": True,
    "require_release_clear": True,
    "require_safety_clear": True,
    "require_recovery_clear": True,
    "require_cash_closure_clear": True,
    "require_fund_admin_ready": True,
    "max_open_discrepancies": 1,
    "max_critical_discrepancies": 0,
    "minimum_cash_position_score": 0.985,
    "minimum_ledger_match_score": 0.985,
    "minimum_bank_venue_confirmation_score": 0.98,
    "minimum_pending_settlement_coverage_score": 0.97,
    "minimum_attestation_quality_score": 0.98,
}

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _operator():
    from backend.app import qnt30702_operator_command_console_router as operator
    return operator

def _release():
    from backend.app import qnt30700_institutional_release_control_router as release
    return release

def _safety():
    from backend.app import qnt30703_live_broker_safety_layer_router as safety
    return safety

def _recovery():
    from backend.app import qnt30707_recovery_system_router as recovery
    return recovery

def _cash_closure():
    from backend.app import qnt30744_institutional_cash_reconciliation_closure_layer_router as cash_closure
    return cash_closure

def _fund_admin():
    from backend.app import qnt30705_fund_admin_control_center_router as fund_admin
    return fund_admin

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
            "treasury_book": [],
            "attestations": [],
            "latest_run": None,
            "last_context": {},
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))

def _save(email: str, data: dict):
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")

def _summary_for_email(email: str) -> dict:
    s = _load(email)
    latest = s.get("latest_run") or {}
    return {
        "institutional_treasury_confirmation_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "attestation_count": len(s.get("attestations") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "attestations": s.get("attestations") or [],
    }

def _cross_system_context(email: str) -> dict:
    return {
        "captured_at": _now_iso(),
        "operator": (_operator()._summary_for_email(email).get("operator_console_status") or {}),
        "release": (_release()._summary_for_email(email).get("release_control_status") or {}),
        "safety": (_safety()._summary_for_email(email).get("safety_layer_status") or {}),
        "recovery": (_recovery()._summary_for_email(email).get("recovery_status") or {}),
        "cash_closure": (_cash_closure()._summary_for_email(email).get("institutional_cash_reconciliation_closure_layer_status") or {}),
        "fund_admin": (_fund_admin()._summary_for_email(email).get("fund_admin_status") or {}),
    }

def _band(score: float) -> str:
    if score >= 98.0:
        return "TREASURY_CONFIRMED"
    if score >= 96.0:
        return "TREASURY_CONTROLLED"
    if score >= 93.0:
        return "TREASURY_WATCH"
    return "TREASURY_BLOCKED"

def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _cross_system_context(email)
    metrics = {k: float(payload.get(k, 0.0) or 0.0) for k in [
        "cash_position_score", "ledger_match_score", "bank_venue_confirmation_score",
        "pending_settlement_coverage_score", "attestation_quality_score"
    ]}
    open_discrepancies = int(payload.get("open_discrepancies", 0) or 0)
    critical_discrepancies = int(payload.get("critical_discrepancies", 0) or 0)
    external_attestation_complete = bool(payload.get("external_attestation_complete", False))
    pending_settlements_confirmed = bool(payload.get("pending_settlements_confirmed", False))
    manual_override_used = bool(payload.get("manual_override_used", False))

    score = 100.0
    reasons = []
    alerts = []
    penalties = {
        "cash_position_score": 125.0,
        "ledger_match_score": 120.0,
        "bank_venue_confirmation_score": 100.0,
        "pending_settlement_coverage_score": 90.0,
        "attestation_quality_score": 110.0,
    }
    reason_map = {
        "cash_position_score": "cash position confidence is below institutional threshold",
        "ledger_match_score": "ledger to treasury match is below policy",
        "bank_venue_confirmation_score": "bank or venue confirmations are below policy",
        "pending_settlement_coverage_score": "pending settlement coverage is incomplete",
        "attestation_quality_score": "treasury attestation quality is below policy",
    }
    alert_map = {
        "cash_position_score": "CASH_POSITION_WEAK",
        "ledger_match_score": "LEDGER_MATCH_WEAK",
        "bank_venue_confirmation_score": "BANK_VENUE_CONFIRMATION_WEAK",
        "pending_settlement_coverage_score": "PENDING_SETTLEMENT_COVERAGE_WEAK",
        "attestation_quality_score": "ATTESTATION_QUALITY_WEAK",
    }
    threshold_map = {
        "cash_position_score": "minimum_cash_position_score",
        "ledger_match_score": "minimum_ledger_match_score",
        "bank_venue_confirmation_score": "minimum_bank_venue_confirmation_score",
        "pending_settlement_coverage_score": "minimum_pending_settlement_coverage_score",
        "attestation_quality_score": "minimum_attestation_quality_score",
    }
    for key, value in metrics.items():
        threshold = float(policy.get(threshold_map[key], 0.97))
        if value < threshold:
            score -= round((threshold - value) * penalties[key], 2)
            reasons.append(reason_map[key])
            alerts.append(alert_map[key])

    if open_discrepancies > int(policy.get("max_open_discrepancies", 1)):
        score -= min((open_discrepancies - int(policy.get("max_open_discrepancies", 1))) * 5.0, 20.0)
        reasons.append("open treasury discrepancies exceed policy")
        alerts.append("OPEN_TREASURY_DISCREPANCIES")
    if critical_discrepancies > int(policy.get("max_critical_discrepancies", 0)):
        score -= min(critical_discrepancies * 12.0, 30.0)
        reasons.append("critical treasury discrepancies remain unresolved")
        alerts.append("CRITICAL_TREASURY_DISCREPANCIES")
    if not external_attestation_complete:
        score -= 6.0
        reasons.append("external treasury attestation is incomplete")
        alerts.append("EXTERNAL_ATTESTATION_INCOMPLETE")
    if not pending_settlements_confirmed:
        score -= 5.0
        reasons.append("pending settlements are not fully confirmed")
        alerts.append("PENDING_SETTLEMENTS_UNCONFIRMED")
    if manual_override_used:
        score -= 4.0
        reasons.append("manual override was used in treasury confirmation flow")
        alerts.append("MANUAL_OVERRIDE_USED")

    operator_posture = str(ctx.get("operator", {}).get("posture", "UNINITIALIZED"))
    release_posture = str(ctx.get("release", {}).get("posture", "UNINITIALIZED"))
    safety_posture = str(ctx.get("safety", {}).get("posture", "UNINITIALIZED"))
    recovery_posture = str(ctx.get("recovery", {}).get("posture", "UNINITIALIZED"))
    cash_closure_posture = str(ctx.get("cash_closure", {}).get("posture", "UNINITIALIZED"))
    fund_admin_posture = str(ctx.get("fund_admin", {}).get("readiness", "UNINITIALIZED"))

    if policy.get("require_operator_clear", True) and operator_posture not in {"READY", "HEALTHY", "OPERATIONAL", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("operator posture is not clear"); alerts.append("OPERATOR_NOT_CLEAR")
    if policy.get("require_release_clear", True) and release_posture not in {"DEPLOYED", "APPROVED", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("release posture is not clear"); alerts.append("RELEASE_NOT_CLEAR")
    if policy.get("require_safety_clear", True) and safety_posture not in {"APPROVED", "READY", "UNINITIALIZED"}:
        score -= 10.0; reasons.append("safety posture is not clear"); alerts.append("SAFETY_NOT_CLEAR")
    if policy.get("require_recovery_clear", True) and recovery_posture not in {"RECOVERED", "READY", "UNINITIALIZED"}:
        score -= 10.0; reasons.append("recovery posture is not clear"); alerts.append("RECOVERY_NOT_CLEAR")
    if policy.get("require_cash_closure_clear", True) and cash_closure_posture not in {"CLEAR", "CASH_CLOSED", "CASH_CONTROLLED", "UNINITIALIZED"}:
        score -= 12.0; reasons.append("cash reconciliation closure posture is not clear"); alerts.append("CASH_CLOSURE_NOT_CLEAR")
    if policy.get("require_fund_admin_ready", True) and fund_admin_posture not in {"ready", "READY", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("fund admin readiness is not clear"); alerts.append("FUND_ADMIN_NOT_READY")

    score = max(round(score, 2), 0.0)
    band = _band(score)
    posture = "CONFIRMED" if score >= float(policy.get("minimum_score", 96.0)) else ("WATCH" if score >= 93.0 else "BLOCKED")
    operator_review_required = posture != "CONFIRMED" or critical_discrepancies > 0
    row = {
        "mission": "QNT30745",
        "evaluated_at": _now_iso(),
        "score": score,
        "band": band,
        "posture": posture,
        "operator_review_required": operator_review_required,
        "metrics": metrics,
        "open_discrepancies": open_discrepancies,
        "critical_discrepancies": critical_discrepancies,
        "reasons": reasons,
        "alerts": alerts,
        "context": ctx,
    }
    _append(store, "runs", row, policy.get("retain_cycles", 180))
    _append(store, "treasury_book", {"at": _now_iso(), "score": score, "band": band, "posture": posture}, policy.get("retain_cycles", 180))
    for a in alerts:
        _append(store, "alerts", {"at": _now_iso(), "code": a, "score": score}, policy.get("retain_cycles", 180))
    store["latest_run"] = row
    store["last_context"] = ctx
    _save(email, store)
    return row

@router.get("/summary")
def summary(user=Depends(_require_user)):
    return _summary_for_email(user["email"])

@router.post("/evaluate")
def evaluate(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    run = _evaluate(email, payload)
    return {"ok": True, "run": run, "summary": _summary_for_email(email)}

@router.post("/attest")
def attest(payload: dict = Body(default={}), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    row = {
        "at": _now_iso(),
        "status": str(payload.get("status") or "CONFIRMED"),
        "signed_by": str(payload.get("signed_by") or user.get("email") or email),
        "note": str(payload.get("note") or "treasury attestation recorded"),
    }
    _append(store, "attestations", row, (store.get("policy") or {}).get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "attestation": row, "summary": _summary_for_email(email)}

@router.post("/policy")
def policy(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    store["policy"] = {**dict(DEFAULT_POLICY), **(store.get("policy") or {}), **payload}
    _save(email, store)
    return {"ok": True, "policy": store["policy"], "summary": _summary_for_email(email)}

@router.post("/bootstrap-demo")
def bootstrap_demo(user=Depends(_require_user)):
    email = user["email"]
    run = _evaluate(email, {
        "cash_position_score": 0.994,
        "ledger_match_score": 0.992,
        "bank_venue_confirmation_score": 0.991,
        "pending_settlement_coverage_score": 0.986,
        "attestation_quality_score": 0.993,
        "open_discrepancies": 0,
        "critical_discrepancies": 0,
        "external_attestation_complete": True,
        "pending_settlements_confirmed": True,
        "manual_override_used": False,
    })
    return {"ok": True, "run": run, "summary": _summary_for_email(email)}
