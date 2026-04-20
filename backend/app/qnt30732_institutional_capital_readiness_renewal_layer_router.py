from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(prefix="/api/institutional-capital-readiness-renewal-layer", tags=["institutional-capital-readiness-renewal-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "institutional_capital_readiness_renewal_layer"
DEFAULT_POLICY = {
    "retain_cycles": 180,
    "minimum_readiness_score": 95.0,
    "require_operator_clear": True,
    "require_release_clear": True,
    "require_safety_clear": True,
    "require_recovery_clear": True,
    "require_operating_confidence_clear": True,
    "require_fund_admin_clear": True,
    "max_open_actions": 0,
    "max_reporting_staleness_days": 2,
    "minimum_capital_buffer_ratio": 0.15,
    "minimum_cash_reconciliation_score": 0.97,
    "minimum_allocation_integrity_score": 0.96,
    "minimum_readiness_notional_for_auto_clear": 750000.0,
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


def _fund_admin():
    from backend.app import qnt30705_fund_admin_control_center_router as fund_admin
    return fund_admin


def _confidence():
    from backend.app import qnt30731_institutional_operating_confidence_layer_router as confidence
    return confidence


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
            "renewal_runs": [],
            "alerts": [],
            "renewal_book": [],
            "latest_renewal_run": None,
            "last_context": {},
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))


def _save(email: str, data: dict):
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")


def _summary_for_email(email: str) -> dict:
    s = _load(email)
    latest = s.get("latest_renewal_run") or {}
    return {
        "institutional_capital_readiness_renewal_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("renewal_score"),
            "renewal_band": latest.get("renewal_band", "UNSET"),
            "renewal_run_count": len(s.get("renewal_runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_renewal_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
    }


def _cross_system_context(email: str) -> dict:
    operator = _operator()._summary_for_email(email)
    release = _release()._summary_for_email(email)
    safety = _safety()._summary_for_email(email)
    recovery = _recovery()._summary_for_email(email)
    confidence = _confidence()._summary_for_email(email)
    fund_admin = _fund_admin()._summary_for_email(email)
    return {
        "captured_at": _now_iso(),
        "operator": operator.get("operator_console_status") or {},
        "release": release.get("release_control_status") or {},
        "safety": safety.get("safety_layer_status") or {},
        "recovery": recovery.get("recovery_status") or {},
        "confidence": confidence.get("institutional_operating_confidence_layer_status") or {},
        "fund_admin": fund_admin.get("fund_admin_control_center_status") or {},
    }


def _score_band(score: float) -> str:
    if score >= 98:
        return "READY"
    if score >= 95:
        return "RENEWED"
    if score >= 90:
        return "SUPERVISED"
    return "RESTRICTED"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _cross_system_context(email)

    capital_buffer_ratio = float(payload.get("capital_buffer_ratio", 0.0) or 0.0)
    cash_reconciliation_score = float(payload.get("cash_reconciliation_score", 0.0) or 0.0)
    allocation_integrity_score = float(payload.get("allocation_integrity_score", 0.0) or 0.0)
    reporting_staleness_days = int(payload.get("reporting_staleness_days", 0) or 0)
    open_actions = int(payload.get("open_actions", 0) or 0)
    pending_investor_notices = int(payload.get("pending_investor_notices", 0) or 0)
    readiness_notional = float(payload.get("readiness_notional", 0.0) or 0.0)
    liquidity_buffer_ready = bool(payload.get("liquidity_buffer_ready", False))
    mandate_attestations_complete = bool(payload.get("mandate_attestations_complete", False))

    score = 100.0
    reasons = []
    alerts = []

    if capital_buffer_ratio < float(policy.get("minimum_capital_buffer_ratio", 0.0)):
        score -= round((float(policy.get("minimum_capital_buffer_ratio", 0.0)) - capital_buffer_ratio) * 80.0, 2)
        reasons.append("capital buffer ratio below renewal threshold")
        alerts.append("CAPITAL_BUFFER_THIN")
    if cash_reconciliation_score < float(policy.get("minimum_cash_reconciliation_score", 0.0)):
        score -= round((float(policy.get("minimum_cash_reconciliation_score", 0.0)) - cash_reconciliation_score) * 100.0, 2)
        reasons.append("cash reconciliation score below threshold")
        alerts.append("CASH_RECONCILIATION_WEAK")
    if allocation_integrity_score < float(policy.get("minimum_allocation_integrity_score", 0.0)):
        score -= round((float(policy.get("minimum_allocation_integrity_score", 0.0)) - allocation_integrity_score) * 100.0, 2)
        reasons.append("allocation integrity score below threshold")
        alerts.append("ALLOCATION_INTEGRITY_WEAK")
    if reporting_staleness_days > int(policy.get("max_reporting_staleness_days", 0)):
        score -= min((reporting_staleness_days - int(policy.get("max_reporting_staleness_days", 0))) * 4.0, 16.0)
        reasons.append("reporting staleness exceeds policy")
        alerts.append("REPORTING_STALE")
    if open_actions > int(policy.get("max_open_actions", 0)):
        score -= min(open_actions * 6.0, 18.0)
        reasons.append("open readiness actions remain")
        alerts.append("OPEN_ACTIONS_REMAIN")
    if pending_investor_notices > 0:
        score -= min(pending_investor_notices * 2.0, 10.0)
        reasons.append("pending investor notices reduce capital readiness")
    if not liquidity_buffer_ready:
        score -= 10.0
        reasons.append("liquidity buffer not explicitly ready")
        alerts.append("LIQUIDITY_BUFFER_NOT_READY")
    if not mandate_attestations_complete:
        score -= 8.0
        reasons.append("mandate attestations incomplete")
        alerts.append("MANDATE_ATTESTATIONS_INCOMPLETE")

    if policy.get("require_operator_clear") and ctx["operator"].get("posture") in {"INCIDENT", "LOCKED", "STOPPED"}:
        score -= 10.0
        alerts.append("OPERATOR_NOT_CLEAR")
    if policy.get("require_release_clear") and ctx["release"].get("posture") in {"BLOCKED", "ROLLED_BACK", "PENDING"}:
        score -= 10.0
        alerts.append("RELEASE_NOT_CLEAR")
    if policy.get("require_safety_clear") and ctx["safety"].get("posture") in {"BLOCKED", "KILL_SWITCH", "PAUSED"}:
        score -= 12.0
        alerts.append("SAFETY_NOT_CLEAR")
    if policy.get("require_recovery_clear") and ctx["recovery"].get("posture") in {"FAILED", "SAFE_MODE", "CORRUPTED"}:
        score -= 12.0
        alerts.append("RECOVERY_NOT_CLEAR")
    if policy.get("require_operating_confidence_clear") and ctx["confidence"].get("posture") not in {"APPROVED", "REVIEW"}:
        score -= 16.0
        alerts.append("OPERATING_CONFIDENCE_NOT_CLEAR")
    if policy.get("require_fund_admin_clear") and ctx["fund_admin"].get("posture") in {"UNINITIALIZED", "BLOCKED", "REVIEW_REQUIRED"}:
        score -= 12.0
        alerts.append("FUND_ADMIN_NOT_CLEAR")

    score = max(round(score, 2), 0.0)
    band = _score_band(score)
    operator_review_required = readiness_notional >= float(policy.get("minimum_readiness_notional_for_auto_clear", 0.0)) or band != "READY"
    posture = "APPROVED" if score >= float(policy.get("minimum_readiness_score", 0.0)) and not alerts else ("REVIEW" if score >= 90 else "BLOCKED")

    run = {
        "renewal_id": f"capital_readiness_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "title": payload.get("title", "institutional capital readiness renewal review"),
        "summary": payload.get("summary", ""),
        "renewal_score": score,
        "renewal_band": band,
        "posture": posture,
        "operator_review_required": operator_review_required,
        "inputs": {
            "capital_buffer_ratio": capital_buffer_ratio,
            "cash_reconciliation_score": cash_reconciliation_score,
            "allocation_integrity_score": allocation_integrity_score,
            "reporting_staleness_days": reporting_staleness_days,
            "open_actions": open_actions,
            "pending_investor_notices": pending_investor_notices,
            "readiness_notional": readiness_notional,
            "liquidity_buffer_ready": liquidity_buffer_ready,
            "mandate_attestations_complete": mandate_attestations_complete,
        },
        "reasons": reasons,
        "alerts": alerts,
        "context": ctx,
    }

    _append(store, "renewal_runs", run, int(policy.get("retain_cycles", 180)))
    for alert in alerts:
        _append(store, "alerts", {
            "captured_at": _now_iso(),
            "code": alert,
            "renewal_id": run["renewal_id"],
            "severity": "critical" if any(k in alert for k in ["SAFETY", "RECOVERY", "FUND_ADMIN"]) else "warning",
        }, int(policy.get("retain_cycles", 180)))
    _append(store, "renewal_book", {
        "captured_at": _now_iso(),
        "renewal_id": run["renewal_id"],
        "posture": posture,
        "renewal_band": band,
        "renewal_score": score,
    }, int(policy.get("retain_cycles", 180)))
    store["latest_renewal_run"] = run
    store["last_context"] = ctx
    _save(email, store)
    return run


@router.get("/summary")
def summary(session=Depends(_require_user)):
    email = session.get("email") or "demo@quantora.local"
    return _summary_for_email(email)


@router.post("/evaluate")
def evaluate(payload: dict = Body(default={}), session=Depends(_require_user)):
    email = session.get("email") or "demo@quantora.local"
    return _evaluate(email, payload or {})


@router.post("/policy")
def policy(payload: dict = Body(default={}), session=Depends(_require_user)):
    email = session.get("email") or "demo@quantora.local"
    store = _load(email)
    store["policy"] = {**dict(DEFAULT_POLICY), **(store.get("policy") or {}), **(payload or {})}
    _save(email, store)
    return {"ok": True, "policy": store["policy"]}


@router.post("/bootstrap-demo")
def bootstrap_demo(session=Depends(_require_user)):
    email = session.get("email") or "demo@quantora.local"
    payload = {
        "title": "institutional capital readiness renewal review",
        "summary": "Renew formal capital readiness after operating confidence is restored.",
        "capital_buffer_ratio": 0.19,
        "cash_reconciliation_score": 0.985,
        "allocation_integrity_score": 0.978,
        "reporting_staleness_days": 1,
        "open_actions": 0,
        "pending_investor_notices": 0,
        "readiness_notional": 640000.0,
        "liquidity_buffer_ready": True,
        "mandate_attestations_complete": True,
    }
    run = _evaluate(email, payload)
    return {"ok": True, "demo": run, "summary": _summary_for_email(email)}
