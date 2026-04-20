from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(prefix="/api/institutional-multi-channel-deployment-orchestration-layer", tags=["institutional-multi-channel-deployment-orchestration-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "institutional_multi_channel_deployment_orchestration_layer"
DEFAULT_POLICY = {
    "retain_cycles": 180,
    "minimum_orchestration_score": 96.0,
    "require_operator_clear": True,
    "require_release_clear": True,
    "require_safety_clear": True,
    "require_recovery_clear": True,
    "require_fund_admin_clear": True,
    "require_scaling_clear": True,
    "require_delivery_clear": True,
    "require_reporting_clear": True,
    "require_transparency_clear": True,
    "max_open_exceptions": 0,
    "max_delivery_staleness_days": 1,
    "minimum_channel_readiness_score": 0.97,
    "minimum_settlement_coordination_score": 0.97,
    "minimum_notice_coverage_score": 0.98,
    "minimum_execution_window_score": 0.97,
    "minimum_orchestration_channels": 2,
    "maximum_channel_concentration_ratio": 0.65,
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


def _delivery():
    from backend.app import qnt30704_investor_delivery_pack_system_router as delivery
    return delivery


def _reporting():
    from backend.app import qnt30715_reporting_disclosure_automation_layer_router as reporting
    return reporting


def _transparency():
    from backend.app import qnt30714_investor_transparency_engine_router as transparency
    return transparency


def _scaling():
    from backend.app import qnt30734_institutional_deployment_capacity_scaling_layer_router as scaling
    return scaling


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
            "orchestration_runs": [],
            "alerts": [],
            "orchestration_book": [],
            "latest_orchestration_run": None,
            "last_context": {},
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))


def _save(email: str, data: dict):
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")


def _summary_for_email(email: str) -> dict:
    s = _load(email)
    latest = s.get("latest_orchestration_run") or {}
    return {
        "institutional_multi_channel_deployment_orchestration_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("orchestration_score"),
            "orchestration_band": latest.get("orchestration_band", "UNSET"),
            "orchestration_run_count": len(s.get("orchestration_runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_orchestration_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
    }


def _cross_system_context(email: str) -> dict:
    return {
        "captured_at": _now_iso(),
        "operator": (_operator()._summary_for_email(email).get("operator_console_status") or {}),
        "release": (_release()._summary_for_email(email).get("release_control_status") or {}),
        "safety": (_safety()._summary_for_email(email).get("safety_layer_status") or {}),
        "recovery": (_recovery()._summary_for_email(email).get("recovery_status") or {}),
        "fund_admin": (_fund_admin()._summary_for_email(email).get("fund_admin_control_center_status") or {}),
        "delivery": (_delivery()._summary_for_email(email).get("investor_delivery_pack_system_status") or {}),
        "reporting": (_reporting()._summary_for_email(email).get("reporting_disclosure_automation_layer_status") or {}),
        "transparency": (_transparency()._summary_for_email(email).get("investor_transparency_engine_status") or {}),
        "scaling": (_scaling()._summary_for_email(email).get("institutional_deployment_capacity_scaling_layer_status") or {}),
    }


def _band(score: float) -> str:
    if score >= 99:
        return "FULLY_ORCHESTRATED"
    if score >= 97:
        return "CONTROLLED_MULTI_CHANNEL"
    if score >= 94:
        return "LIMITED_MULTI_CHANNEL"
    return "DO_NOT_ORCHESTRATE"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _cross_system_context(email)

    active_channels = int(payload.get("active_channels", 0) or 0)
    channel_readiness_score = float(payload.get("channel_readiness_score", 0.0) or 0.0)
    settlement_coordination_score = float(payload.get("settlement_coordination_score", 0.0) or 0.0)
    notice_coverage_score = float(payload.get("notice_coverage_score", 0.0) or 0.0)
    execution_window_score = float(payload.get("execution_window_score", 0.0) or 0.0)
    channel_concentration_ratio = float(payload.get("channel_concentration_ratio", 1.0) or 1.0)
    delivery_staleness_days = int(payload.get("delivery_staleness_days", 0) or 0)
    open_exceptions = int(payload.get("open_exceptions", 0) or 0)
    orchestration_window_open = bool(payload.get("orchestration_window_open", False))
    notices_confirmed = bool(payload.get("notices_confirmed", False))
    controls_attested = bool(payload.get("controls_attested", False))

    score = 100.0
    reasons = []
    alerts = []

    if active_channels < int(policy.get("minimum_orchestration_channels", 1)):
        score -= min((int(policy.get("minimum_orchestration_channels", 1)) - active_channels) * 9.0, 18.0)
        reasons.append("active channels below orchestration minimum")
        alerts.append("INSUFFICIENT_CHANNELS")
    if channel_readiness_score < float(policy.get("minimum_channel_readiness_score", 0.0)):
        score -= round((float(policy.get("minimum_channel_readiness_score", 0.0)) - channel_readiness_score) * 120.0, 2)
        reasons.append("channel readiness score below threshold")
        alerts.append("CHANNEL_READINESS_WEAK")
    if settlement_coordination_score < float(policy.get("minimum_settlement_coordination_score", 0.0)):
        score -= round((float(policy.get("minimum_settlement_coordination_score", 0.0)) - settlement_coordination_score) * 110.0, 2)
        reasons.append("settlement coordination score below threshold")
        alerts.append("SETTLEMENT_COORDINATION_WEAK")
    if notice_coverage_score < float(policy.get("minimum_notice_coverage_score", 0.0)):
        score -= round((float(policy.get("minimum_notice_coverage_score", 0.0)) - notice_coverage_score) * 100.0, 2)
        reasons.append("notice coverage score below threshold")
        alerts.append("NOTICE_COVERAGE_WEAK")
    if execution_window_score < float(policy.get("minimum_execution_window_score", 0.0)):
        score -= round((float(policy.get("minimum_execution_window_score", 0.0)) - execution_window_score) * 100.0, 2)
        reasons.append("execution window score below threshold")
        alerts.append("EXECUTION_WINDOW_WEAK")
    if channel_concentration_ratio > float(policy.get("maximum_channel_concentration_ratio", 1.0)):
        score -= min((channel_concentration_ratio - float(policy.get("maximum_channel_concentration_ratio", 1.0))) * 100.0, 18.0)
        reasons.append("channel concentration exceeds diversification policy")
        alerts.append("CHANNEL_CONCENTRATION_HIGH")
    if delivery_staleness_days > int(policy.get("max_delivery_staleness_days", 0)):
        score -= min((delivery_staleness_days - int(policy.get("max_delivery_staleness_days", 0))) * 5.0, 15.0)
        reasons.append("delivery staleness exceeds orchestration policy")
        alerts.append("DELIVERY_STALE")
    if open_exceptions > int(policy.get("max_open_exceptions", 0)):
        score -= min(open_exceptions * 7.0, 21.0)
        reasons.append("open exceptions remain before orchestration")
        alerts.append("OPEN_EXCEPTIONS_REMAIN")
    if not orchestration_window_open:
        score -= 10.0
        reasons.append("multi-channel orchestration window is not open")
        alerts.append("ORCHESTRATION_WINDOW_CLOSED")
    if not notices_confirmed:
        score -= 6.0
        reasons.append("channel notices are not fully confirmed")
        alerts.append("CHANNEL_NOTICES_UNCONFIRMED")
    if not controls_attested:
        score -= 10.0
        reasons.append("control attestation not complete")
        alerts.append("CONTROLS_NOT_ATTESTED")

    if policy.get("require_operator_clear") and ctx["operator"].get("posture") in {"INCIDENT", "LOCKED", "STOPPED"}:
        score -= 10.0
        alerts.append("OPERATOR_NOT_CLEAR")
    if policy.get("require_release_clear") and ctx["release"].get("posture") in {"BLOCKED", "ROLLED_BACK", "PENDING"}:
        score -= 10.0
        alerts.append("RELEASE_NOT_CLEAR")
    if policy.get("require_safety_clear") and ctx["safety"].get("posture") in {"BLOCKED", "KILL_SWITCH", "PAUSED"}:
        score -= 12.0
        alerts.append("SAFETY_NOT_CLEAR")
    if policy.get("require_recovery_clear") and ctx["recovery"].get("posture") in {"SAFE_MODE", "FAILED", "RECOVERING"}:
        score -= 12.0
        alerts.append("RECOVERY_NOT_CLEAR")
    if policy.get("require_fund_admin_clear") and ctx["fund_admin"].get("posture") in {"BLOCKED", "UNRECONCILED"}:
        score -= 10.0
        alerts.append("FUND_ADMIN_NOT_CLEAR")
    if policy.get("require_scaling_clear") and ctx["scaling"].get("posture") not in {"APPROVED", "READY", "CLEARED"}:
        score -= 8.0
        alerts.append("SCALING_NOT_CLEAR")
    if policy.get("require_delivery_clear") and ctx["delivery"].get("posture") in {"BLOCKED", "FAILED", "EXCEPTION"}:
        score -= 8.0
        alerts.append("DELIVERY_NOT_CLEAR")
    if policy.get("require_reporting_clear") and ctx["reporting"].get("posture") in {"BLOCKED", "EXCEPTION", "STALE"}:
        score -= 8.0
        alerts.append("REPORTING_NOT_CLEAR")
    if policy.get("require_transparency_clear") and ctx["transparency"].get("posture") in {"BLOCKED", "EXCEPTION", "GAP"}:
        score -= 8.0
        alerts.append("TRANSPARENCY_NOT_CLEAR")

    score = max(0.0, round(score, 2))
    posture = "APPROVED" if score >= float(policy.get("minimum_orchestration_score", 0.0)) and not alerts else ("WATCH" if score >= float(policy.get("minimum_orchestration_score", 0.0)) else "BLOCKED")
    operator_review_required = posture != "APPROVED" or channel_concentration_ratio > 0.50 or active_channels >= 4

    run = {
        "recorded_at": _now_iso(),
        "title": payload.get("title") or "institutional multi-channel deployment orchestration review",
        "summary": payload.get("summary") or "Evaluate whether Quantora can coordinate governed multi-channel deployment.",
        "orchestration_score": score,
        "posture": posture,
        "orchestration_band": _band(score),
        "operator_review_required": operator_review_required,
        "inputs": {
            "active_channels": active_channels,
            "channel_readiness_score": channel_readiness_score,
            "settlement_coordination_score": settlement_coordination_score,
            "notice_coverage_score": notice_coverage_score,
            "execution_window_score": execution_window_score,
            "channel_concentration_ratio": channel_concentration_ratio,
            "delivery_staleness_days": delivery_staleness_days,
            "open_exceptions": open_exceptions,
            "orchestration_window_open": orchestration_window_open,
            "notices_confirmed": notices_confirmed,
            "controls_attested": controls_attested,
        },
        "reasons": reasons,
        "alerts": alerts,
    }
    store["latest_orchestration_run"] = run
    store["last_context"] = ctx
    _append(store, "orchestration_runs", run, int(policy.get("retain_cycles", 180)))
    if alerts:
        _append(store, "alerts", {"recorded_at": _now_iso(), "alerts": alerts, "posture": posture}, int(policy.get("retain_cycles", 180)))
    _append(store, "orchestration_book", {
        "recorded_at": _now_iso(),
        "posture": posture,
        "orchestration_band": run["orchestration_band"],
        "orchestration_score": score,
    }, int(policy.get("retain_cycles", 180)))
    _save(email, store)
    return run


@router.get("/summary")
def summary(session=Depends(_require_user)):
    return _summary_for_email(session.get("email") or "unknown@example.com")


@router.post("/evaluate")
def evaluate(payload: dict = Body(default={}), session=Depends(_require_user)):
    email = session.get("email") or "unknown@example.com"
    run = _evaluate(email, payload or {})
    return {"ok": True, "orchestration_run": run, **_summary_for_email(email)}


@router.post("/policy")
def policy(payload: dict = Body(default={}), session=Depends(_require_user)):
    email = session.get("email") or "unknown@example.com"
    store = _load(email)
    store["policy"] = {**dict(DEFAULT_POLICY), **(store.get("policy") or {}), **(payload or {})}
    _save(email, store)
    return {"ok": True, "policy": store["policy"]}


@router.post("/bootstrap-demo")
def bootstrap_demo(session=Depends(_require_user)):
    email = session.get("email") or "unknown@example.com"
    payload = {
        "title": "institutional multi-channel deployment orchestration review",
        "summary": "Evaluate whether Quantora can coordinate governed multi-channel deployment across multiple capital channels.",
        "active_channels": 3,
        "channel_readiness_score": 0.985,
        "settlement_coordination_score": 0.982,
        "notice_coverage_score": 0.991,
        "execution_window_score": 0.984,
        "channel_concentration_ratio": 0.46,
        "delivery_staleness_days": 0,
        "open_exceptions": 0,
        "orchestration_window_open": True,
        "notices_confirmed": True,
        "controls_attested": True,
    }
    run = _evaluate(email, payload)
    return {"ok": True, "orchestration_run": run, **_summary_for_email(email)}
