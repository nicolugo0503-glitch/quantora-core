from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(prefix="/api/institutional-deployment-capacity-scaling-layer", tags=["institutional-deployment-capacity-scaling-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "institutional_deployment_capacity_scaling_layer"
DEFAULT_POLICY = {
    "retain_cycles": 180,
    "minimum_scaling_score": 96.0,
    "require_operator_clear": True,
    "require_release_clear": True,
    "require_safety_clear": True,
    "require_recovery_clear": True,
    "require_fund_admin_clear": True,
    "require_reinstatement_clear": True,
    "require_liquidity_clear": True,
    "require_mandate_clear": True,
    "max_open_actions": 0,
    "max_reporting_staleness_days": 1,
    "minimum_liquidity_headroom_ratio": 0.30,
    "minimum_execution_capacity_score": 0.97,
    "minimum_operator_supervision_score": 0.98,
    "minimum_monitoring_coverage_score": 0.98,
    "maximum_scale_step_ratio": 0.30,
    "minimum_auto_scale_notional": 750000.0,
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


def _reinstatement():
    from backend.app import qnt30733_institutional_capital_deployment_reinstatement_layer_router as reinstatement
    return reinstatement


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
            "scaling_runs": [],
            "alerts": [],
            "capacity_book": [],
            "latest_scaling_run": None,
            "last_context": {},
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))


def _save(email: str, data: dict):
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")


def _summary_for_email(email: str) -> dict:
    s = _load(email)
    latest = s.get("latest_scaling_run") or {}
    return {
        "institutional_deployment_capacity_scaling_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("scaling_score"),
            "capacity_band": latest.get("capacity_band", "UNSET"),
            "scaling_run_count": len(s.get("scaling_runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_scaling_run": latest,
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
    reinstatement = _reinstatement()._summary_for_email(email)
    return {
        "captured_at": _now_iso(),
        "operator": operator.get("operator_console_status") or {},
        "release": release.get("release_control_status") or {},
        "safety": safety.get("safety_layer_status") or {},
        "recovery": recovery.get("recovery_status") or {},
        "fund_admin": fund_admin.get("fund_admin_control_center_status") or {},
        "liquidity": liquidity.get("liquidity_intelligence_system_status") or {},
        "mandate": mandate.get("institutional_mandate_enforcement_layer_status") or {},
        "reinstatement": reinstatement.get("institutional_capital_deployment_reinstatement_layer_status") or {},
    }


def _score_band(score: float) -> str:
    if score >= 99:
        return "INSTITUTIONAL_SCALE"
    if score >= 97:
        return "CONTROLLED_EXPANSION"
    if score >= 94:
        return "LIMITED_SCALE"
    return "DO_NOT_SCALE"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _cross_system_context(email)

    liquidity_headroom_ratio = float(payload.get("liquidity_headroom_ratio", 0.0) or 0.0)
    execution_capacity_score = float(payload.get("execution_capacity_score", 0.0) or 0.0)
    operator_supervision_score = float(payload.get("operator_supervision_score", 0.0) or 0.0)
    monitoring_coverage_score = float(payload.get("monitoring_coverage_score", 0.0) or 0.0)
    reporting_staleness_days = int(payload.get("reporting_staleness_days", 0) or 0)
    open_actions = int(payload.get("open_actions", 0) or 0)
    proposed_scale_notional = float(payload.get("proposed_scale_notional", 0.0) or 0.0)
    scale_step_ratio = float(payload.get("scale_step_ratio", 0.0) or 0.0)
    capacity_window_open = bool(payload.get("capacity_window_open", False))
    controls_attested = bool(payload.get("controls_attested", False))
    investor_notice_complete = bool(payload.get("investor_notice_complete", False))

    score = 100.0
    reasons = []
    alerts = []

    if liquidity_headroom_ratio < float(policy.get("minimum_liquidity_headroom_ratio", 0.0)):
        score -= round((float(policy.get("minimum_liquidity_headroom_ratio", 0.0)) - liquidity_headroom_ratio) * 110.0, 2)
        reasons.append("liquidity headroom ratio below scaling threshold")
        alerts.append("LIQUIDITY_HEADROOM_THIN")
    if execution_capacity_score < float(policy.get("minimum_execution_capacity_score", 0.0)):
        score -= round((float(policy.get("minimum_execution_capacity_score", 0.0)) - execution_capacity_score) * 120.0, 2)
        reasons.append("execution capacity score below threshold")
        alerts.append("EXECUTION_CAPACITY_WEAK")
    if operator_supervision_score < float(policy.get("minimum_operator_supervision_score", 0.0)):
        score -= round((float(policy.get("minimum_operator_supervision_score", 0.0)) - operator_supervision_score) * 120.0, 2)
        reasons.append("operator supervision score below threshold")
        alerts.append("OPERATOR_SUPERVISION_WEAK")
    if monitoring_coverage_score < float(policy.get("minimum_monitoring_coverage_score", 0.0)):
        score -= round((float(policy.get("minimum_monitoring_coverage_score", 0.0)) - monitoring_coverage_score) * 100.0, 2)
        reasons.append("monitoring coverage score below threshold")
        alerts.append("MONITORING_COVERAGE_WEAK")
    if reporting_staleness_days > int(policy.get("max_reporting_staleness_days", 0)):
        score -= min((reporting_staleness_days - int(policy.get("max_reporting_staleness_days", 0))) * 5.0, 15.0)
        reasons.append("reporting staleness exceeds scaling policy")
        alerts.append("REPORTING_STALE")
    if open_actions > int(policy.get("max_open_actions", 0)):
        score -= min(open_actions * 7.0, 21.0)
        reasons.append("open actions remain before scaling")
        alerts.append("OPEN_ACTIONS_REMAIN")
    if scale_step_ratio > float(policy.get("maximum_scale_step_ratio", 1.0)):
        score -= min((scale_step_ratio - float(policy.get("maximum_scale_step_ratio", 1.0))) * 100.0, 18.0)
        reasons.append("proposed scale step exceeds governed step ratio")
        alerts.append("SCALE_STEP_TOO_LARGE")
    if not capacity_window_open:
        score -= 10.0
        reasons.append("capacity scaling window is not open")
        alerts.append("CAPACITY_WINDOW_CLOSED")
    if not controls_attested:
        score -= 12.0
        reasons.append("controls attestation not complete")
        alerts.append("CONTROLS_NOT_ATTESTED")
    if not investor_notice_complete:
        score -= 5.0
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
    if policy.get("require_reinstatement_clear") and ctx["reinstatement"].get("posture") not in {"APPROVED", "REVIEW"}:
        score -= 16.0
        alerts.append("REINSTATEMENT_NOT_CLEAR")
    if policy.get("require_liquidity_clear") and ctx["liquidity"].get("posture") in {"BLOCKED", "STRESSED", "UNINITIALIZED"}:
        score -= 12.0
        alerts.append("LIQUIDITY_NOT_CLEAR")
    if policy.get("require_mandate_clear") and ctx["mandate"].get("posture") in {"BLOCKED", "REVIEW", "UNINITIALIZED"}:
        score -= 14.0
        alerts.append("MANDATE_NOT_CLEAR")

    score = max(round(score, 2), 0.0)
    band = _score_band(score)
    operator_review_required = proposed_scale_notional >= float(policy.get("minimum_auto_scale_notional", 0.0)) or band != "INSTITUTIONAL_SCALE"
    posture = "APPROVED" if score >= float(policy.get("minimum_scaling_score", 0.0)) and not alerts else ("REVIEW" if score >= 92 else "BLOCKED")

    run = {
        "scaling_id": f"deployment_capacity_scaling_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "title": payload.get("title", "institutional deployment capacity scaling review"),
        "summary": payload.get("summary", ""),
        "scaling_score": score,
        "capacity_band": band,
        "posture": posture,
        "operator_review_required": operator_review_required,
        "inputs": {
            "liquidity_headroom_ratio": liquidity_headroom_ratio,
            "execution_capacity_score": execution_capacity_score,
            "operator_supervision_score": operator_supervision_score,
            "monitoring_coverage_score": monitoring_coverage_score,
            "reporting_staleness_days": reporting_staleness_days,
            "open_actions": open_actions,
            "proposed_scale_notional": proposed_scale_notional,
            "scale_step_ratio": scale_step_ratio,
            "capacity_window_open": capacity_window_open,
            "controls_attested": controls_attested,
            "investor_notice_complete": investor_notice_complete,
        },
        "reasons": reasons,
        "alerts": alerts,
        "context": ctx,
    }

    _append(store, "scaling_runs", run, int(policy.get("retain_cycles", 180)))
    for alert in alerts:
        _append(store, "alerts", {
            "captured_at": _now_iso(),
            "code": alert,
            "scaling_id": run["scaling_id"],
            "severity": "critical" if any(k in alert for k in ["SAFETY", "RECOVERY", "MANDATE", "CONTROLS"]) else "warning",
        }, int(policy.get("retain_cycles", 180)))
    _append(store, "capacity_book", {
        "captured_at": _now_iso(),
        "scaling_id": run["scaling_id"],
        "posture": posture,
        "capacity_band": band,
        "scaling_score": score,
    }, int(policy.get("retain_cycles", 180)))
    store["latest_scaling_run"] = run
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
        "title": "institutional deployment capacity scaling review",
        "summary": "Evaluate whether Quantora can scale governed capital deployment capacity.",
        "liquidity_headroom_ratio": 0.36,
        "execution_capacity_score": 0.985,
        "operator_supervision_score": 0.99,
        "monitoring_coverage_score": 0.99,
        "reporting_staleness_days": 0,
        "open_actions": 0,
        "proposed_scale_notional": 680000.0,
        "scale_step_ratio": 0.22,
        "capacity_window_open": True,
        "controls_attested": True,
        "investor_notice_complete": True,
    }
    run = _evaluate(email, payload)
    return {"ok": True, "demo": run, "summary": _summary_for_email(email)}
