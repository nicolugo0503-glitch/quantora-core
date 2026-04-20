from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(prefix="/api/institutional-cross-venue-deployment-routing-layer", tags=["institutional-cross-venue-deployment-routing-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "institutional_cross_venue_deployment_routing_layer"
DEFAULT_POLICY = {
    "retain_cycles": 180,
    "minimum_routing_score": 96.0,
    "require_operator_clear": True,
    "require_release_clear": True,
    "require_safety_clear": True,
    "require_recovery_clear": True,
    "require_fund_admin_clear": True,
    "require_liquidity_clear": True,
    "require_mandate_clear": True,
    "require_orchestration_clear": True,
    "max_open_exceptions": 0,
    "max_routing_staleness_days": 1,
    "minimum_active_venues": 2,
    "minimum_venue_capacity_score": 0.97,
    "minimum_execution_quality_score": 0.97,
    "minimum_settlement_quality_score": 0.97,
    "minimum_failover_coverage_score": 0.96,
    "maximum_venue_concentration_ratio": 0.60,
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


def _orchestration():
    from backend.app import qnt30735_institutional_multi_channel_deployment_orchestration_layer_router as orchestration
    return orchestration


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
            "routing_runs": [],
            "alerts": [],
            "routing_book": [],
            "latest_routing_run": None,
            "last_context": {},
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))


def _save(email: str, data: dict):
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")


def _summary_for_email(email: str) -> dict:
    s = _load(email)
    latest = s.get("latest_routing_run") or {}
    return {
        "institutional_cross_venue_deployment_routing_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("routing_score"),
            "routing_band": latest.get("routing_band", "UNSET"),
            "routing_run_count": len(s.get("routing_runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_routing_run": latest,
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
        "liquidity": (_liquidity()._summary_for_email(email).get("liquidity_intelligence_system_status") or {}),
        "mandate": (_mandate()._summary_for_email(email).get("institutional_mandate_enforcement_layer_status") or {}),
        "orchestration": (_orchestration()._summary_for_email(email).get("institutional_multi_channel_deployment_orchestration_layer_status") or {}),
    }


def _band(score: float) -> str:
    if score >= 99:
        return "INSTITUTIONAL_ROUTE_CLEAR"
    if score >= 97:
        return "CONTROLLED_ROUTE"
    if score >= 94:
        return "LIMITED_ROUTE"
    return "DO_NOT_ROUTE"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _cross_system_context(email)

    active_venues = int(payload.get("active_venues", 0) or 0)
    venue_capacity_score = float(payload.get("venue_capacity_score", 0.0) or 0.0)
    execution_quality_score = float(payload.get("execution_quality_score", 0.0) or 0.0)
    settlement_quality_score = float(payload.get("settlement_quality_score", 0.0) or 0.0)
    failover_coverage_score = float(payload.get("failover_coverage_score", 0.0) or 0.0)
    venue_concentration_ratio = float(payload.get("venue_concentration_ratio", 1.0) or 1.0)
    routing_staleness_days = int(payload.get("routing_staleness_days", 0) or 0)
    open_exceptions = int(payload.get("open_exceptions", 0) or 0)
    routing_window_open = bool(payload.get("routing_window_open", False))
    venues_synced = bool(payload.get("venues_synced", False))
    controls_attested = bool(payload.get("controls_attested", False))

    score = 100.0
    reasons = []
    alerts = []

    if active_venues < int(policy.get("minimum_active_venues", 1)):
        score -= min((int(policy.get("minimum_active_venues", 1)) - active_venues) * 9.0, 18.0)
        reasons.append("active venues below routing minimum")
        alerts.append("INSUFFICIENT_VENUES")
    if venue_capacity_score < float(policy.get("minimum_venue_capacity_score", 0.0)):
        score -= round((float(policy.get("minimum_venue_capacity_score", 0.0)) - venue_capacity_score) * 120.0, 2)
        reasons.append("venue capacity score below threshold")
        alerts.append("VENUE_CAPACITY_WEAK")
    if execution_quality_score < float(policy.get("minimum_execution_quality_score", 0.0)):
        score -= round((float(policy.get("minimum_execution_quality_score", 0.0)) - execution_quality_score) * 120.0, 2)
        reasons.append("execution quality score below threshold")
        alerts.append("EXECUTION_QUALITY_WEAK")
    if settlement_quality_score < float(policy.get("minimum_settlement_quality_score", 0.0)):
        score -= round((float(policy.get("minimum_settlement_quality_score", 0.0)) - settlement_quality_score) * 110.0, 2)
        reasons.append("settlement quality score below threshold")
        alerts.append("SETTLEMENT_QUALITY_WEAK")
    if failover_coverage_score < float(policy.get("minimum_failover_coverage_score", 0.0)):
        score -= round((float(policy.get("minimum_failover_coverage_score", 0.0)) - failover_coverage_score) * 100.0, 2)
        reasons.append("failover coverage score below threshold")
        alerts.append("FAILOVER_COVERAGE_WEAK")
    if venue_concentration_ratio > float(policy.get("maximum_venue_concentration_ratio", 1.0)):
        score -= min((venue_concentration_ratio - float(policy.get("maximum_venue_concentration_ratio", 1.0))) * 100.0, 18.0)
        reasons.append("venue concentration exceeds diversification policy")
        alerts.append("VENUE_CONCENTRATION_HIGH")
    if routing_staleness_days > int(policy.get("max_routing_staleness_days", 0)):
        score -= min((routing_staleness_days - int(policy.get("max_routing_staleness_days", 0))) * 5.0, 15.0)
        reasons.append("routing data staleness exceeds policy")
        alerts.append("ROUTING_STALE")
    if open_exceptions > int(policy.get("max_open_exceptions", 0)):
        score -= min(open_exceptions * 7.0, 21.0)
        reasons.append("open exceptions remain before routing")
        alerts.append("OPEN_EXCEPTIONS_REMAIN")
    if not routing_window_open:
        score -= 10.0
        reasons.append("cross-venue routing window is not open")
        alerts.append("ROUTING_WINDOW_CLOSED")
    if not venues_synced:
        score -= 6.0
        reasons.append("venue synchronization is incomplete")
        alerts.append("VENUES_NOT_SYNCED")
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
    if policy.get("require_liquidity_clear") and ctx["liquidity"].get("posture") in {"BLOCKED", "STRESSED", "FRAGILE"}:
        score -= 10.0
        alerts.append("LIQUIDITY_NOT_CLEAR")
    if policy.get("require_mandate_clear") and ctx["mandate"].get("posture") in {"BLOCKED", "VIOLATION", "BREACH"}:
        score -= 10.0
        alerts.append("MANDATE_NOT_CLEAR")
    if policy.get("require_orchestration_clear") and ctx["orchestration"].get("posture") not in {"APPROVED", "READY", "CLEARED"}:
        score -= 8.0
        alerts.append("ORCHESTRATION_NOT_CLEAR")

    score = max(0.0, round(score, 2))
    posture = "APPROVED" if score >= float(policy.get("minimum_routing_score", 0.0)) and not alerts else ("WATCH" if score >= float(policy.get("minimum_routing_score", 0.0) - 2.0) else "BLOCKED")
    operator_review_required = posture != "APPROVED" or venue_concentration_ratio > 0.50 or active_venues >= 4

    run = {
        "recorded_at": _now_iso(),
        "title": payload.get("title") or "institutional cross-venue deployment routing review",
        "summary": payload.get("summary") or "Evaluate whether Quantora can route governed deployment across multiple execution venues.",
        "routing_score": score,
        "posture": posture,
        "routing_band": _band(score),
        "operator_review_required": operator_review_required,
        "inputs": {
            "active_venues": active_venues,
            "venue_capacity_score": venue_capacity_score,
            "execution_quality_score": execution_quality_score,
            "settlement_quality_score": settlement_quality_score,
            "failover_coverage_score": failover_coverage_score,
            "venue_concentration_ratio": venue_concentration_ratio,
            "routing_staleness_days": routing_staleness_days,
            "open_exceptions": open_exceptions,
            "routing_window_open": routing_window_open,
            "venues_synced": venues_synced,
            "controls_attested": controls_attested,
        },
        "reasons": reasons,
        "alerts": alerts,
    }
    store["latest_routing_run"] = run
    store["last_context"] = ctx
    _append(store, "routing_runs", run, int(policy.get("retain_cycles", 180)))
    if alerts:
        _append(store, "alerts", {"recorded_at": _now_iso(), "alerts": alerts, "posture": posture}, int(policy.get("retain_cycles", 180)))
    _append(store, "routing_book", {
        "recorded_at": _now_iso(),
        "posture": posture,
        "routing_band": run["routing_band"],
        "routing_score": score,
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
    return {"ok": True, "routing_run": run, **_summary_for_email(email)}


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
        "title": "institutional cross-venue deployment routing review",
        "summary": "Evaluate whether Quantora can route governed deployment across multiple execution venues.",
        "active_venues": 3,
        "venue_capacity_score": 0.986,
        "execution_quality_score": 0.984,
        "settlement_quality_score": 0.982,
        "failover_coverage_score": 0.979,
        "venue_concentration_ratio": 0.44,
        "routing_staleness_days": 0,
        "open_exceptions": 0,
        "routing_window_open": True,
        "venues_synced": True,
        "controls_attested": True,
    }
    run = _evaluate(email, payload)
    return {"ok": True, "routing_run": run, **_summary_for_email(email)}
