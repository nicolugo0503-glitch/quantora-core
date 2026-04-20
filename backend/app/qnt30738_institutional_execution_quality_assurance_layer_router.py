from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(prefix="/api/institutional-execution-quality-assurance-layer", tags=["institutional-execution-quality-assurance-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "institutional_execution_quality_assurance_layer"
DEFAULT_POLICY = {'retain_cycles': 180, 'minimum_score': 97.0, 'require_operator_clear': True, 'require_release_clear': True, 'require_safety_clear': True, 'require_recovery_clear': True, 'require_fund_admin_clear': True, 'require_liquidity_clear': True, 'require_routing_clear': True, 'max_open_exceptions': 0, 'max_unresolved_pressure': 0, 'minimum_fill_integrity_score': 0.98, 'minimum_slippage_quality_score': 0.97, 'minimum_timeliness_score': 0.97, 'minimum_settlement_integrity_score': 0.98, 'minimum_exception_readiness_score': 0.96}


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


def _routing():
    from backend.app import qnt30736_institutional_cross_venue_deployment_routing_layer_router as routing
    return routing


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
            "book": [],
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
        "institutional_execution_quality_assurance_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
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
        "routing": (_routing()._summary_for_email(email).get("institutional_cross_venue_deployment_routing_layer_status") or {}),
    }


def _band(score: float) -> str:
    if score >= 99:
        return "INSTITUTIONAL_QUALITY_CLEAR"
    if score >= 97:
        return "CONTROLLED_QUALITY"
    if score >= 94:
        return "LIMITED_QUALITY"
    return "DO_NOT_EXECUTE"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _cross_system_context(email)
    metrics = {k: float(payload.get(k, 0.0) or 0.0) for k in ['fill_integrity_score', 'slippage_quality_score', 'timeliness_score', 'settlement_integrity_score', 'exception_readiness_score']}
    unresolved_pressure = int(payload.get("unresolved_pressure", 0) or 0)
    open_exceptions = int(payload.get("open_exceptions", 0) or 0)
    monitoring_window_open = bool(payload.get("monitoring_window_open", False))
    controls_attested = bool(payload.get("controls_attested", False))

    score = 100.0
    reasons = []
    alerts = []
    thresholds = {'fill_integrity_score': ('POLICY', 0.98), 'slippage_quality_score': ('POLICY', 0.97), 'timeliness_score': ('POLICY', 0.97), 'settlement_integrity_score': ('POLICY', 0.98), 'exception_readiness_score': ('POLICY', 0.96)}
    penalties = {'fill_integrity_score': 120.0, 'slippage_quality_score': 115.0, 'timeliness_score': 110.0, 'settlement_integrity_score': 120.0, 'exception_readiness_score': 95.0}
    alerts_map = {'fill_integrity_score': 'FILL_INTEGRITY_WEAK', 'slippage_quality_score': 'SLIPPAGE_QUALITY_WEAK', 'timeliness_score': 'TIMELINESS_WEAK', 'settlement_integrity_score': 'SETTLEMENT_INTEGRITY_WEAK', 'exception_readiness_score': 'EXCEPTION_READINESS_WEAK'}
    reason_map = {'fill_integrity_score': 'fill integrity is below institutional threshold', 'slippage_quality_score': 'slippage quality is below institutional threshold', 'timeliness_score': 'execution timeliness is below policy', 'settlement_integrity_score': 'settlement integrity is below institutional threshold', 'exception_readiness_score': 'exception readiness is below institutional threshold'}

    for key, value in metrics.items():
        threshold = float(policy.get('minimum_' + key, thresholds[key][1]))
        if value < threshold:
            score -= round((threshold - value) * penalties[key], 2)
            reasons.append(reason_map[key])
            alerts.append(alerts_map[key])

    if unresolved_pressure > int(policy.get("max_unresolved_pressure", 0)):
        score -= min((unresolved_pressure - int(policy.get("max_unresolved_pressure", 0))) * 6.0, 18.0)
        reasons.append("unresolved institutional pressure remains too high")
        alerts.append("UNRESOLVED_PRESSURE_HIGH")
    if open_exceptions > int(policy.get("max_open_exceptions", 0)):
        score -= min(open_exceptions * 6.0, 18.0)
        reasons.append("open exceptions remain before approval")
        alerts.append("OPEN_EXCEPTIONS_REMAIN")
    if not monitoring_window_open:
        score -= 8.0
        reasons.append("monitoring window is not open")
        alerts.append("MONITORING_WINDOW_CLOSED")
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
    if policy.get("require_fund_admin_clear") and ctx["fund_admin"].get("posture") in {"BLOCKED", "REVIEW", "RECONCILE"}:
        score -= 10.0
        alerts.append("FUND_ADMIN_NOT_CLEAR")
    if policy.get("require_liquidity_clear") and ctx["liquidity"].get("posture") in {"BLOCKED", "STRESSED", "WATCH"}:
        score -= 10.0
        alerts.append("LIQUIDITY_NOT_CLEAR")
    if policy.get("require_routing_clear") and ctx["routing"].get("posture") in {"BLOCKED", "DO_NOT_ROUTE", "WATCH"}:
        score -= 10.0
        alerts.append("ROUTING_NOT_CLEAR")

    score = max(round(score, 2), 0.0)
    posture = "APPROVED" if score >= float(policy.get("minimum_score", 95.0)) and not alerts else ("WATCH" if score >= float(policy.get("minimum_score", 95.0)) - 3 else "BLOCKED")
    band = _band(score)
    operator_review_required = bool(score < 99 or len(alerts) > 0)
    run = {
        "captured_at": _now_iso(),
        "title": payload.get("title", "institutional execution quality assurance review"),
        "summary": payload.get("summary", "Evaluate whether Quantora can assure institutional execution quality after capacity balancing."),
        "score": score,
        "posture": posture,
        "band": band,
        "operator_review_required": operator_review_required,
        "metrics": metrics,
        "reasons": reasons,
        "alerts": alerts,
        "context_snapshot": ctx,
    }
    _append(store, "runs", run, int(policy.get("retain_cycles", 180) or 180))
    _append(store, "book", {"captured_at": run["captured_at"], "band": band, "score": score, "posture": posture}, int(policy.get("retain_cycles", 180) or 180))
    if alerts:
        _append(store, "alerts", {"captured_at": run["captured_at"], "alerts": alerts, "posture": posture}, int(policy.get("retain_cycles", 180) or 180))
    store["latest_run"] = run
    store["last_context"] = ctx
    store["policy"] = policy
    _save(email, store)
    return run

@router.get("/summary")
def summary(user=Depends(_require_user)):
    return _summary_for_email(user["email"])

@router.post("/evaluate")
def evaluate(payload: dict = Body(default={}), user=Depends(_require_user)):
    return _evaluate(user["email"], payload)

@router.post("/policy")
def policy(payload: dict = Body(default={}), user=Depends(_require_user)):
    store = _load(user["email"])
    store["policy"] = {**dict(DEFAULT_POLICY), **(store.get("policy") or {}), **(payload or {})}
    _save(user["email"], store)
    return {"ok": True, "policy": store["policy"]}

@router.post("/bootstrap-demo")
def bootstrap_demo(user=Depends(_require_user)):
    return _evaluate(user["email"], {"title": "institutional execution quality assurance review", "summary": "Evaluate whether Quantora can assure execution quality at institutional standard.", "fill_integrity_score": 0.989, "slippage_quality_score": 0.981, "timeliness_score": 0.979, "settlement_integrity_score": 0.988, "exception_readiness_score": 0.973, "unresolved_pressure": 0, "open_exceptions": 0, "monitoring_window_open": true, "controls_attested": true})
