from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(prefix="/api/institutional-stability-reconfirmation-layer", tags=["institutional-stability-reconfirmation-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "institutional_stability_reconfirmation_layer"
DEFAULT_POLICY = {
    "retain_cycles": 180,
    "minimum_reconfirmation_score": 95.0,
    "require_operator_clear": True,
    "require_release_clear": True,
    "require_safety_clear": True,
    "require_recovery_clear": True,
    "require_continuity_clear": True,
    "max_monitoring_breaches": 0,
    "max_reconciliation_breaks": 0,
    "max_open_investor_complaints": 0,
    "minimum_stability_window_days": 10,
    "stability_notional_threshold": 750000.0,
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


def _forensic():
    from backend.app import qnt30706_forensic_audit_system_router as forensic
    return forensic


def _recovery():
    from backend.app import qnt30707_recovery_system_router as recovery
    return recovery


def _breach():
    from backend.app import qnt30725_institutional_breach_escalation_layer_router as breach
    return breach


def _exception_layer():
    from backend.app import qnt30726_institutional_exception_resolution_layer_router as exception_layer
    return exception_layer


def _closure_layer():
    from backend.app import qnt30727_institutional_remediation_closure_layer_router as closure_layer
    return closure_layer


def _reauth_layer():
    from backend.app import qnt30728_institutional_reauthorization_layer_router as reauth_layer
    return reauth_layer


def _continuity_layer():
    from backend.app import qnt30729_institutional_continuity_restoration_layer_router as continuity_layer
    return continuity_layer


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
            "reconfirmation_runs": [],
            "alerts": [],
            "stability_book": [],
            "latest_reconfirmation_run": None,
            "last_context": {},
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))


def _save(email: str, data: dict):
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")


def _summary_for_email(email: str) -> dict:
    s = _load(email)
    latest = s.get("latest_reconfirmation_run") or {}
    return {
        "institutional_stability_reconfirmation_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("reconfirmation_score"),
            "stability_band": latest.get("stability_band", "UNSET"),
            "reconfirmation_run_count": len(s.get("reconfirmation_runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_reconfirmation_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
    }


def _cross_system_context(email: str) -> dict:
    operator = _operator()._summary_for_email(email)
    release = _release()._summary_for_email(email)
    safety = _safety()._summary_for_email(email)
    forensic = _forensic()._summary_for_email(email)
    recovery = _recovery()._summary_for_email(email)
    breach = _breach()._summary_for_email(email)
    exception_layer = _exception_layer()._summary_for_email(email)
    closure_layer = _closure_layer()._summary_for_email(email)
    reauth_layer = _reauth_layer()._summary_for_email(email)
    continuity_layer = _continuity_layer()._summary_for_email(email)
    return {
        "captured_at": _now_iso(),
        "operator": operator.get("operator_console_status") or {},
        "release": release.get("release_control_status") or {},
        "safety": safety.get("safety_layer_status") or {},
        "forensic": forensic.get("forensic_status") or {},
        "recovery": recovery.get("recovery_status") or {},
        "breach": breach.get("institutional_breach_escalation_layer_status") or {},
        "exception": exception_layer.get("institutional_exception_resolution_layer_status") or {},
        "closure": closure_layer.get("institutional_remediation_closure_layer_status") or {},
        "reauthorization": reauth_layer.get("institutional_reauthorization_layer_status") or {},
        "continuity": continuity_layer.get("institutional_continuity_restoration_layer_status") or {},
    }


def _score_band(score: float) -> str:
    if score >= 98:
        return "CONFIRMED"
    if score >= 95:
        return "SUPERVISED_STABLE"
    if score >= 88:
        return "PROBATIONARY"
    return "BLOCKED"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _cross_system_context(email)

    stability_window_days = int(payload.get("stability_window_days", 0) or 0)
    monitoring_breaches = int(payload.get("monitoring_breaches", 0) or 0)
    volatility_events = int(payload.get("volatility_events", 0) or 0)
    reconciliation_breaks = int(payload.get("reconciliation_breaks", 0) or 0)
    investor_complaints_open = int(payload.get("investor_complaints_open", 0) or 0)
    service_degradation_open = int(payload.get("service_degradation_open", 0) or 0)
    operational_incident_pressure = float(payload.get("operational_incident_pressure", 0.0) or 0.0)
    capital_resumption_stable = bool(payload.get("capital_resumption_stable", False))
    reporting_cycles_on_time = bool(payload.get("reporting_cycles_on_time", False))
    stability_notional = float(payload.get("stability_notional", 0.0) or 0.0)

    score = 100.0
    reasons = []
    alerts = []

    if stability_window_days < int(policy.get("minimum_stability_window_days", 0)):
        score -= 14.0
        reasons.append("stability window below policy minimum")
        alerts.append("STABILITY_WINDOW_SHORT")
    if monitoring_breaches > int(policy.get("max_monitoring_breaches", 0)):
        score -= min(monitoring_breaches * 10.0, 30.0)
        reasons.append("monitoring breaches detected")
        alerts.append("MONITORING_BREACHES")
    if reconciliation_breaks > int(policy.get("max_reconciliation_breaks", 0)):
        score -= min(reconciliation_breaks * 12.0, 30.0)
        reasons.append("reconciliation breaks remain")
        alerts.append("RECON_BREAKS")
    if investor_complaints_open > int(policy.get("max_open_investor_complaints", 0)):
        score -= min(investor_complaints_open * 6.0, 18.0)
        reasons.append("open investor complaints exceed tolerance")
    if service_degradation_open > 0:
        score -= min(service_degradation_open * 5.0, 15.0)
        reasons.append("service degradation remains open")
    if volatility_events > 0:
        score -= min(volatility_events * 3.0, 12.0)
        reasons.append("stability window experienced volatility events")
    if operational_incident_pressure > 0:
        score -= min(operational_incident_pressure * 10.0, 12.0)
        reasons.append("operational incident pressure remains elevated")
    if not capital_resumption_stable:
        score -= 10.0
        reasons.append("capital resumption not yet stable")
    if not reporting_cycles_on_time:
        score -= 8.0
        reasons.append("reporting cycles not consistently on time")

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
    if policy.get("require_continuity_clear") and ctx["continuity"].get("posture") not in {"APPROVED", "REVIEW"}:
        score -= 16.0
        alerts.append("CONTINUITY_NOT_CLEAR")
    if ctx["breach"].get("freeze_required"):
        score -= 15.0
        alerts.append("BREACH_FREEZE_ACTIVE")
    if ctx["forensic"].get("posture") in {"CHAIN_FAIL", "CRITICAL_OPEN"}:
        score -= 8.0
        alerts.append("FORENSIC_PRESSURE")
    if ctx["reauthorization"].get("posture") not in {"REAUTHORIZED", "SUPERVISED_REAUTHORIZATION"}:
        score -= 8.0
        alerts.append("REAUTHORIZATION_NOT_CLEAR")

    score = max(round(score, 2), 0.0)
    band = _score_band(score)
    operator_review_required = stability_notional >= float(policy.get("stability_notional_threshold", 0.0)) or band != "CONFIRMED"
    posture = "APPROVED" if score >= float(policy.get("minimum_reconfirmation_score", 0.0)) and not alerts else ("REVIEW" if score >= 88 else "BLOCKED")

    run = {
        "reconfirmation_id": f"stability_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "title": payload.get("title", "institutional stability reconfirmation review"),
        "summary": payload.get("summary", ""),
        "reconfirmation_score": score,
        "stability_band": band,
        "posture": posture,
        "operator_review_required": operator_review_required,
        "inputs": {
            "stability_window_days": stability_window_days,
            "monitoring_breaches": monitoring_breaches,
            "volatility_events": volatility_events,
            "reconciliation_breaks": reconciliation_breaks,
            "investor_complaints_open": investor_complaints_open,
            "service_degradation_open": service_degradation_open,
            "operational_incident_pressure": operational_incident_pressure,
            "capital_resumption_stable": capital_resumption_stable,
            "reporting_cycles_on_time": reporting_cycles_on_time,
            "stability_notional": stability_notional,
        },
        "reasons": reasons,
        "alerts": alerts,
        "context": ctx,
    }

    _append(store, "reconfirmation_runs", run, int(policy.get("retain_cycles", 180)))
    for alert in alerts:
        _append(store, "alerts", {
            "captured_at": _now_iso(),
            "code": alert,
            "reconfirmation_id": run["reconfirmation_id"],
            "severity": "critical" if "BREACH" in alert or "RECON" in alert else "warning",
        }, int(policy.get("retain_cycles", 180)))
    _append(store, "stability_book", {
        "captured_at": _now_iso(),
        "reconfirmation_id": run["reconfirmation_id"],
        "posture": posture,
        "stability_band": band,
        "reconfirmation_score": score,
    }, int(policy.get("retain_cycles", 180)))
    store["latest_reconfirmation_run"] = run
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
        "title": "institutional stability reconfirmation review",
        "summary": "Evaluate whether Quantora has reconfirmed stable institutional operations after continuity restoration.",
        "stability_window_days": 14,
        "monitoring_breaches": 0,
        "volatility_events": 1,
        "reconciliation_breaks": 0,
        "investor_complaints_open": 0,
        "service_degradation_open": 0,
        "operational_incident_pressure": 0.05,
        "capital_resumption_stable": True,
        "reporting_cycles_on_time": True,
        "stability_notional": 560000.0,
    }
    run = _evaluate(email, payload)
    return {"ok": True, "demo": run, "summary": _summary_for_email(email)}
