from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(prefix="/api/institutional-continuity-restoration-layer", tags=["institutional-continuity-restoration-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "institutional_continuity_restoration_layer"
DEFAULT_POLICY = {
    "retain_cycles": 180,
    "minimum_restoration_score": 93.0,
    "require_operator_clear": True,
    "require_release_clear": True,
    "require_safety_clear": True,
    "require_recovery_clear": True,
    "require_reauthorization_clear": True,
    "max_open_critical_items": 0,
    "minimum_monitoring_days": 5,
    "max_unresolved_material_items": 0,
    "continuity_notional_threshold": 500000.0,
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
            "restoration_runs": [],
            "alerts": [],
            "continuity_book": [],
            "latest_restoration_run": None,
            "last_context": {},
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))


def _save(email: str, data: dict):
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")


def _summary_for_email(email: str) -> dict:
    s = _load(email)
    latest = s.get("latest_restoration_run") or {}
    return {
        "institutional_continuity_restoration_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("restoration_score"),
            "continuity_band": latest.get("continuity_band", "UNSET"),
            "restoration_run_count": len(s.get("restoration_runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_restoration_run": latest,
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
    }


def _score_band(score: float) -> str:
    if score >= 97:
        return "RESTORED"
    if score >= 93:
        return "SUPERVISED_RESTART"
    if score >= 86:
        return "LIMITED_CONTINUITY"
    return "BLOCKED"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _cross_system_context(email)

    open_critical_items = int(payload.get("open_critical_items", 0) or 0)
    unresolved_material_items = int(payload.get("unresolved_material_items", 0) or 0)
    monitoring_days = int(payload.get("monitoring_days", 0) or 0)
    services_restored = bool(payload.get("services_restored", False))
    capital_flows_resumed = bool(payload.get("capital_flows_resumed", False))
    investor_communications_complete = bool(payload.get("investor_communications_complete", False))
    backlog_normalized = bool(payload.get("backlog_normalized", False))
    continuity_notional = float(payload.get("continuity_notional", 0.0) or 0.0)

    score = 100.0
    reasons = []
    alerts = []

    if open_critical_items > int(policy.get("max_open_critical_items", 0)):
        score -= 36.0
        reasons.append("critical items remain open")
        alerts.append("CRITICAL_ITEMS_OPEN")
    if unresolved_material_items > int(policy.get("max_unresolved_material_items", 0)):
        score -= min(unresolved_material_items * 6.0, 18.0)
        reasons.append("material items remain unresolved")
    if monitoring_days < int(policy.get("minimum_monitoring_days", 0)):
        score -= 12.0
        reasons.append("monitoring window below policy minimum")
    if not services_restored:
        score -= 16.0
        reasons.append("services not fully restored")
    if not capital_flows_resumed:
        score -= 14.0
        reasons.append("capital flows not fully resumed")
    if not investor_communications_complete:
        score -= 10.0
        reasons.append("investor communication coverage incomplete")
    if not backlog_normalized:
        score -= 8.0
        reasons.append("operational backlog not normalized")

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
    if policy.get("require_reauthorization_clear") and ctx["reauthorization"].get("posture") not in {"REAUTHORIZED", "SUPERVISED_REAUTHORIZATION"}:
        score -= 16.0
        alerts.append("REAUTHORIZATION_NOT_CLEAR")
    if ctx["breach"].get("freeze_required"):
        score -= 15.0
        alerts.append("BREACH_FREEZE_ACTIVE")
    if ctx["forensic"].get("posture") in {"CHAIN_FAIL", "CRITICAL_OPEN"}:
        score -= 8.0
        alerts.append("FORENSIC_PRESSURE")

    score = max(round(score, 2), 0.0)
    band = _score_band(score)
    operator_review_required = continuity_notional >= float(policy.get("continuity_notional_threshold", 0.0)) or band != "RESTORED"
    posture = "APPROVED" if score >= float(policy.get("minimum_restoration_score", 0.0)) and not alerts else ("REVIEW" if score >= 86 else "BLOCKED")

    run = {
        "restoration_id": f"continuity_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "title": payload.get("title", "institutional continuity restoration review"),
        "summary": payload.get("summary", ""),
        "restoration_score": score,
        "continuity_band": band,
        "posture": posture,
        "operator_review_required": operator_review_required,
        "inputs": {
            "open_critical_items": open_critical_items,
            "unresolved_material_items": unresolved_material_items,
            "monitoring_days": monitoring_days,
            "services_restored": services_restored,
            "capital_flows_resumed": capital_flows_resumed,
            "investor_communications_complete": investor_communications_complete,
            "backlog_normalized": backlog_normalized,
            "continuity_notional": continuity_notional,
        },
        "reasons": reasons,
        "alerts": alerts,
        "context": ctx,
    }

    _append(store, "restoration_runs", run, int(policy.get("retain_cycles", 180)))
    for alert in alerts:
        _append(store, "alerts", {
            "captured_at": _now_iso(),
            "code": alert,
            "restoration_id": run["restoration_id"],
            "severity": "critical" if "CRITICAL" in alert or "FREEZE" in alert else "warning",
        }, int(policy.get("retain_cycles", 180)))
    _append(store, "continuity_book", {
        "captured_at": _now_iso(),
        "restoration_id": run["restoration_id"],
        "posture": posture,
        "continuity_band": band,
        "restoration_score": score,
    }, int(policy.get("retain_cycles", 180)))
    store["latest_restoration_run"] = run
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
        "title": "institutional continuity restoration review",
        "summary": "Evaluate whether Quantora can restore normal institutional continuity after reauthorization.",
        "open_critical_items": 0,
        "unresolved_material_items": 0,
        "monitoring_days": 7,
        "services_restored": True,
        "capital_flows_resumed": True,
        "investor_communications_complete": True,
        "backlog_normalized": True,
        "continuity_notional": 420000.0,
    }
    run = _evaluate(email, payload)
    return {"ok": True, "demo": run, "summary": _summary_for_email(email)}
