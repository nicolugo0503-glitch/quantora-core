from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(prefix="/api/institutional-capital-deployment-reinstatement-layer", tags=["institutional-capital-deployment-reinstatement-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "institutional_capital_deployment_reinstatement_layer"
DEFAULT_POLICY = {
    "retain_cycles": 180,
    "minimum_reinstatement_score": 95.0,
    "require_operator_clear": True,
    "require_release_clear": True,
    "require_safety_clear": True,
    "require_recovery_clear": True,
    "require_fund_admin_clear": True,
    "require_readiness_renewal_clear": True,
    "require_liquidity_clear": True,
    "require_mandate_clear": True,
    "max_open_actions": 0,
    "max_reporting_staleness_days": 1,
    "minimum_deployment_liquidity_ratio": 0.20,
    "minimum_execution_window_score": 0.96,
    "minimum_operator_attestation_score": 0.98,
    "minimum_auto_reinstate_notional": 500000.0,
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


def _liquidity():
    from backend.app import qnt30709_liquidity_intelligence_system_router as liquidity
    return liquidity


def _mandate():
    from backend.app import qnt30724_institutional_mandate_enforcement_layer_router as mandate
    return mandate


def _renewal():
    from backend.app import qnt30732_institutional_capital_readiness_renewal_layer_router as renewal
    return renewal


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
            "reinstatement_runs": [],
            "alerts": [],
            "reinstatement_book": [],
            "latest_reinstatement_run": None,
            "last_context": {},
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))


def _save(email: str, data: dict):
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")


def _summary_for_email(email: str) -> dict:
    s = _load(email)
    latest = s.get("latest_reinstatement_run") or {}
    return {
        "institutional_capital_deployment_reinstatement_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("reinstatement_score"),
            "reinstatement_band": latest.get("reinstatement_band", "UNSET"),
            "reinstatement_run_count": len(s.get("reinstatement_runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_reinstatement_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
    }


def _cross_system_context(email: str) -> dict:
    operator = _operator()._summary_for_email(email)
    release = _release()._summary_for_email(email)
    safety = _safety()._summary_for_email(email)
    recovery = _recovery()._summary_for_email(email)
    fund_admin = _fund_admin()._summary_for_email(email)
    liquidity = _liquidity()._summary_for_email(email)
    mandate = _mandate()._summary_for_email(email)
    renewal = _renewal()._summary_for_email(email)
    return {
        "captured_at": _now_iso(),
        "operator": operator.get("operator_console_status") or {},
        "release": release.get("release_control_status") or {},
        "safety": safety.get("safety_layer_status") or {},
        "recovery": recovery.get("recovery_status") or {},
        "fund_admin": fund_admin.get("fund_admin_control_center_status") or {},
        "liquidity": liquidity.get("liquidity_intelligence_system_status") or {},
        "mandate": mandate.get("institutional_mandate_enforcement_layer_status") or {},
        "renewal": renewal.get("institutional_capital_readiness_renewal_layer_status") or {},
    }


def _score_band(score: float) -> str:
    if score >= 98:
        return "REINSTATED"
    if score >= 95:
        return "SUPERVISED"
    if score >= 90:
        return "LIMITED"
    return "BLOCKED"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _cross_system_context(email)

    deployment_liquidity_ratio = float(payload.get("deployment_liquidity_ratio", 0.0) or 0.0)
    execution_window_score = float(payload.get("execution_window_score", 0.0) or 0.0)
    operator_attestation_score = float(payload.get("operator_attestation_score", 0.0) or 0.0)
    reporting_staleness_days = int(payload.get("reporting_staleness_days", 0) or 0)
    open_actions = int(payload.get("open_actions", 0) or 0)
    reinstatement_notional = float(payload.get("reinstatement_notional", 0.0) or 0.0)
    deployment_window_open = bool(payload.get("deployment_window_open", False))
    capital_controls_active = bool(payload.get("capital_controls_active", False))
    investor_notice_complete = bool(payload.get("investor_notice_complete", False))

    score = 100.0
    reasons = []
    alerts = []

    if deployment_liquidity_ratio < float(policy.get("minimum_deployment_liquidity_ratio", 0.0)):
        score -= round((float(policy.get("minimum_deployment_liquidity_ratio", 0.0)) - deployment_liquidity_ratio) * 100.0, 2)
        reasons.append("deployment liquidity ratio below reinstatement threshold")
        alerts.append("DEPLOYMENT_LIQUIDITY_THIN")
    if execution_window_score < float(policy.get("minimum_execution_window_score", 0.0)):
        score -= round((float(policy.get("minimum_execution_window_score", 0.0)) - execution_window_score) * 120.0, 2)
        reasons.append("execution window score below threshold")
        alerts.append("EXECUTION_WINDOW_WEAK")
    if operator_attestation_score < float(policy.get("minimum_operator_attestation_score", 0.0)):
        score -= round((float(policy.get("minimum_operator_attestation_score", 0.0)) - operator_attestation_score) * 120.0, 2)
        reasons.append("operator attestation score below threshold")
        alerts.append("OPERATOR_ATTESTATION_WEAK")
    if reporting_staleness_days > int(policy.get("max_reporting_staleness_days", 0)):
        score -= min((reporting_staleness_days - int(policy.get("max_reporting_staleness_days", 0))) * 5.0, 15.0)
        reasons.append("reporting staleness exceeds reinstatement policy")
        alerts.append("REPORTING_STALE")
    if open_actions > int(policy.get("max_open_actions", 0)):
        score -= min(open_actions * 7.0, 21.0)
        reasons.append("open deployment actions remain")
        alerts.append("OPEN_ACTIONS_REMAIN")
    if not deployment_window_open:
        score -= 10.0
        reasons.append("deployment window is not open")
        alerts.append("DEPLOYMENT_WINDOW_CLOSED")
    if capital_controls_active:
        score -= 14.0
        reasons.append("capital controls remain active")
        alerts.append("CAPITAL_CONTROLS_ACTIVE")
    if not investor_notice_complete:
        score -= 6.0
        reasons.append("investor notice completion not confirmed")
        alerts.append("INVESTOR_NOTICE_INCOMPLETE")

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
    if policy.get("require_fund_admin_clear") and ctx["fund_admin"].get("posture") in {"UNINITIALIZED", "BLOCKED", "REVIEW_REQUIRED"}:
        score -= 12.0
        alerts.append("FUND_ADMIN_NOT_CLEAR")
    if policy.get("require_readiness_renewal_clear") and ctx["renewal"].get("posture") not in {"APPROVED", "REVIEW"}:
        score -= 16.0
        alerts.append("READINESS_RENEWAL_NOT_CLEAR")
    if policy.get("require_liquidity_clear") and ctx["liquidity"].get("posture") in {"BLOCKED", "STRESSED", "UNINITIALIZED"}:
        score -= 12.0
        alerts.append("LIQUIDITY_NOT_CLEAR")
    if policy.get("require_mandate_clear") and ctx["mandate"].get("posture") in {"BLOCKED", "REVIEW", "UNINITIALIZED"}:
        score -= 14.0
        alerts.append("MANDATE_NOT_CLEAR")

    score = max(round(score, 2), 0.0)
    band = _score_band(score)
    operator_review_required = reinstatement_notional >= float(policy.get("minimum_auto_reinstate_notional", 0.0)) or band != "REINSTATED"
    posture = "APPROVED" if score >= float(policy.get("minimum_reinstatement_score", 0.0)) and not alerts else ("REVIEW" if score >= 90 else "BLOCKED")

    run = {
        "reinstatement_id": f"capital_deployment_reinstatement_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "title": payload.get("title", "institutional capital deployment reinstatement review"),
        "summary": payload.get("summary", ""),
        "reinstatement_score": score,
        "reinstatement_band": band,
        "posture": posture,
        "operator_review_required": operator_review_required,
        "inputs": {
            "deployment_liquidity_ratio": deployment_liquidity_ratio,
            "execution_window_score": execution_window_score,
            "operator_attestation_score": operator_attestation_score,
            "reporting_staleness_days": reporting_staleness_days,
            "open_actions": open_actions,
            "reinstatement_notional": reinstatement_notional,
            "deployment_window_open": deployment_window_open,
            "capital_controls_active": capital_controls_active,
            "investor_notice_complete": investor_notice_complete,
        },
        "reasons": reasons,
        "alerts": alerts,
        "context": ctx,
    }

    _append(store, "reinstatement_runs", run, int(policy.get("retain_cycles", 180)))
    for alert in alerts:
        _append(store, "alerts", {
            "captured_at": _now_iso(),
            "code": alert,
            "reinstatement_id": run["reinstatement_id"],
            "severity": "critical" if any(k in alert for k in ["SAFETY", "RECOVERY", "MANDATE", "CAPITAL_CONTROLS"]) else "warning",
        }, int(policy.get("retain_cycles", 180)))
    _append(store, "reinstatement_book", {
        "captured_at": _now_iso(),
        "reinstatement_id": run["reinstatement_id"],
        "posture": posture,
        "reinstatement_band": band,
        "reinstatement_score": score,
    }, int(policy.get("retain_cycles", 180)))
    store["latest_reinstatement_run"] = run
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
        "title": "institutional capital deployment reinstatement review",
        "summary": "Evaluate whether Quantora can formally resume governed capital deployment.",
        "deployment_liquidity_ratio": 0.24,
        "execution_window_score": 0.985,
        "operator_attestation_score": 0.99,
        "reporting_staleness_days": 0,
        "open_actions": 0,
        "reinstatement_notional": 420000.0,
        "deployment_window_open": True,
        "capital_controls_active": False,
        "investor_notice_complete": True,
    }
    run = _evaluate(email, payload)
    return {"ok": True, "demo": run, "summary": _summary_for_email(email)}
