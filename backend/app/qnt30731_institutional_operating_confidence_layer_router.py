from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(prefix="/api/institutional-operating-confidence-layer", tags=["institutional-operating-confidence-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "institutional_operating_confidence_layer"
DEFAULT_POLICY = {
    "retain_cycles": 180,
    "minimum_confidence_score": 96.0,
    "require_operator_clear": True,
    "require_release_clear": True,
    "require_safety_clear": True,
    "require_recovery_clear": True,
    "require_stability_clear": True,
    "max_active_warnings": 1,
    "max_open_exceptions": 0,
    "minimum_observation_days": 15,
    "operating_notional_threshold": 1000000.0,
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


def _stability():
    from backend.app import qnt30730_institutional_stability_reconfirmation_layer_router as stability
    return stability


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
            "confidence_runs": [],
            "alerts": [],
            "confidence_book": [],
            "latest_confidence_run": None,
            "last_context": {},
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))


def _save(email: str, data: dict):
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")


def _summary_for_email(email: str) -> dict:
    s = _load(email)
    latest = s.get("latest_confidence_run") or {}
    return {
        "institutional_operating_confidence_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("confidence_score"),
            "confidence_band": latest.get("confidence_band", "UNSET"),
            "confidence_run_count": len(s.get("confidence_runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_confidence_run": latest,
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
    stability = _stability()._summary_for_email(email)
    return {
        "captured_at": _now_iso(),
        "operator": operator.get("operator_console_status") or {},
        "release": release.get("release_control_status") or {},
        "safety": safety.get("safety_layer_status") or {},
        "forensic": forensic.get("forensic_status") or {},
        "recovery": recovery.get("recovery_status") or {},
        "stability": stability.get("institutional_stability_reconfirmation_layer_status") or {},
    }


def _score_band(score: float) -> str:
    if score >= 98:
        return "TRUSTED"
    if score >= 96:
        return "AUTHORIZED"
    if score >= 90:
        return "SUPERVISED"
    return "RESTRICTED"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _cross_system_context(email)

    observation_days = int(payload.get("observation_days", 0) or 0)
    active_warnings = int(payload.get("active_warnings", 0) or 0)
    open_exceptions = int(payload.get("open_exceptions", 0) or 0)
    unresolved_actions = int(payload.get("unresolved_actions", 0) or 0)
    reporting_delay_days = int(payload.get("reporting_delay_days", 0) or 0)
    capital_resilience_score = float(payload.get("capital_resilience_score", 0.0) or 0.0)
    operating_notional = float(payload.get("operating_notional", 0.0) or 0.0)
    monitoring_coverage = bool(payload.get("monitoring_coverage", False))
    control_attestations_complete = bool(payload.get("control_attestations_complete", False))

    score = 100.0
    reasons = []
    alerts = []

    if observation_days < int(policy.get("minimum_observation_days", 0)):
        score -= 14.0
        reasons.append("observation window below policy minimum")
        alerts.append("OBSERVATION_WINDOW_SHORT")
    if active_warnings > int(policy.get("max_active_warnings", 0)):
        score -= min(active_warnings * 7.0, 21.0)
        reasons.append("active warnings exceed tolerance")
        alerts.append("ACTIVE_WARNINGS_EXCEEDED")
    if open_exceptions > int(policy.get("max_open_exceptions", 0)):
        score -= min(open_exceptions * 10.0, 30.0)
        reasons.append("open exceptions remain")
        alerts.append("OPEN_EXCEPTIONS_REMAIN")
    if unresolved_actions > 0:
        score -= min(unresolved_actions * 4.0, 16.0)
        reasons.append("unresolved operating actions remain")
    if reporting_delay_days > 0:
        score -= min(reporting_delay_days * 2.0, 10.0)
        reasons.append("reporting delays reduce operating confidence")
    if capital_resilience_score < 0.9:
        score -= round((0.9 - capital_resilience_score) * 20.0, 2)
        reasons.append("capital resilience score below strong threshold")
    if not monitoring_coverage:
        score -= 10.0
        reasons.append("monitoring coverage incomplete")
    if not control_attestations_complete:
        score -= 8.0
        reasons.append("control attestations incomplete")

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
    if policy.get("require_stability_clear") and ctx["stability"].get("posture") not in {"APPROVED", "REVIEW"}:
        score -= 16.0
        alerts.append("STABILITY_NOT_CLEAR")
    if ctx["forensic"].get("posture") in {"CHAIN_FAIL", "CRITICAL_OPEN"}:
        score -= 8.0
        alerts.append("FORENSIC_PRESSURE")

    score = max(round(score, 2), 0.0)
    band = _score_band(score)
    operator_review_required = operating_notional >= float(policy.get("operating_notional_threshold", 0.0)) or band != "TRUSTED"
    posture = "APPROVED" if score >= float(policy.get("minimum_confidence_score", 0.0)) and not alerts else ("REVIEW" if score >= 90 else "BLOCKED")

    run = {
        "confidence_id": f"confidence_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "title": payload.get("title", "institutional operating confidence review"),
        "summary": payload.get("summary", ""),
        "confidence_score": score,
        "confidence_band": band,
        "posture": posture,
        "operator_review_required": operator_review_required,
        "inputs": {
            "observation_days": observation_days,
            "active_warnings": active_warnings,
            "open_exceptions": open_exceptions,
            "unresolved_actions": unresolved_actions,
            "reporting_delay_days": reporting_delay_days,
            "capital_resilience_score": capital_resilience_score,
            "operating_notional": operating_notional,
            "monitoring_coverage": monitoring_coverage,
            "control_attestations_complete": control_attestations_complete,
        },
        "reasons": reasons,
        "alerts": alerts,
        "context": ctx,
    }

    _append(store, "confidence_runs", run, int(policy.get("retain_cycles", 180)))
    for alert in alerts:
        _append(store, "alerts", {
            "captured_at": _now_iso(),
            "code": alert,
            "confidence_id": run["confidence_id"],
            "severity": "critical" if "EXCEPTION" in alert or "SAFETY" in alert else "warning",
        }, int(policy.get("retain_cycles", 180)))
    _append(store, "confidence_book", {
        "captured_at": _now_iso(),
        "confidence_id": run["confidence_id"],
        "posture": posture,
        "confidence_band": band,
        "confidence_score": score,
    }, int(policy.get("retain_cycles", 180)))
    store["latest_confidence_run"] = run
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
        "title": "institutional operating confidence review",
        "summary": "Evaluate whether Quantora has restored trusted day-two operating confidence.",
        "observation_days": 18,
        "active_warnings": 0,
        "open_exceptions": 0,
        "unresolved_actions": 1,
        "reporting_delay_days": 0,
        "capital_resilience_score": 0.96,
        "operating_notional": 820000.0,
        "monitoring_coverage": True,
        "control_attestations_complete": True,
    }
    run = _evaluate(email, payload)
    return {"ok": True, "demo": run, "summary": _summary_for_email(email)}
