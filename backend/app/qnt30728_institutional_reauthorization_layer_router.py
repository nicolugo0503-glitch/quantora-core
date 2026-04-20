from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["institutional-reauthorization-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "institutional_reauthorization_layer"
DEFAULT_POLICY = {
    "retain_cycles": 180,
    "minimum_reauthorization_score": 92.0,
    "require_operator_clear": True,
    "require_release_clear": True,
    "require_safety_clear": True,
    "require_recovery_clear": True,
    "require_closure_clear": True,
    "require_exception_clear": True,
    "require_breach_clear": True,
    "require_mandate_clear": True,
    "reauthorization_notional_threshold": 500000.0,
    "max_open_critical_items": 0,
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


def _mandate_layer():
    from backend.app import qnt30724_institutional_mandate_enforcement_layer_router as mandate_layer
    return mandate_layer


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
            "reauthorization_runs": [],
            "alerts": [],
            "reauthorization_book": [],
            "latest_reauthorization_run": None,
            "last_context": {},
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))


def _save(email: str, data: dict):
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")


def _summary_for_email(email: str) -> dict:
    s = _load(email)
    latest = s.get("latest_reauthorization_run") or {}
    return {
        "institutional_reauthorization_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("reauthorization_score"),
            "reauthorization_band": latest.get("reauthorization_band", "UNSET"),
            "reauthorization_run_count": len(s.get("reauthorization_runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "operator_signoff_required": bool(latest.get("operator_signoff_required", False)),
        },
        "latest_reauthorization_run": latest,
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
    mandate_layer = _mandate_layer()._summary_for_email(email)
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
        "mandate": mandate_layer.get("institutional_mandate_enforcement_layer_status") or {},
    }


def _score_band(score: float) -> str:
    if score >= 97:
        return "REAUTHORIZED"
    if score >= 92:
        return "SUPERVISED_REAUTHORIZATION"
    if score >= 85:
        return "HOLD_REVIEW"
    return "BLOCKED"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _cross_system_context(email)

    open_critical_items = int(payload.get("open_critical_items", 0) or 0)
    open_material_items = int(payload.get("open_material_items", 0) or 0)
    evidence_complete = bool(payload.get("evidence_complete", False))
    controls_restored = bool(payload.get("controls_restored", False))
    capital_impact_supervised = bool(payload.get("capital_impact_supervised", False))
    monitoring_active = bool(payload.get("monitoring_active", False))
    mandate_aligned = bool(payload.get("mandate_aligned", False))
    reauthorization_notional = float(payload.get("reauthorization_notional", 0.0) or 0.0)

    score = 100.0
    reasons = []
    alerts = []

    if open_critical_items > int(policy.get("max_open_critical_items", 0)):
        score -= 35.0
        reasons.append("open critical items exceed policy")
        alerts.append("CRITICAL_ITEMS_OPEN")
    if open_material_items > 0:
        score -= min(open_material_items * 6.0, 18.0)
        reasons.append("material items still open")
    if not evidence_complete:
        score -= 18.0
        reasons.append("reauthorization evidence incomplete")
    if not controls_restored:
        score -= 16.0
        reasons.append("controls not fully restored")
    if not capital_impact_supervised:
        score -= 12.0
        reasons.append("capital impact supervision incomplete")
    if not monitoring_active:
        score -= 9.0
        reasons.append("post-close monitoring not active")
    if not mandate_aligned:
        score -= 14.0
        reasons.append("mandate alignment not confirmed")

    if policy.get("require_operator_clear") and ctx["operator"].get("posture") in {"INCIDENT", "LOCKED", "STOPPED"}:
        score -= 10.0
        alerts.append("OPERATOR_NOT_CLEAR")
    if policy.get("require_release_clear") and ctx["release"].get("posture") in {"BLOCKED", "ROLLED_BACK", "PENDING"}:
        score -= 10.0
        alerts.append("RELEASE_NOT_CLEAR")
    if policy.get("require_safety_clear") and ctx["safety"].get("posture") in {"BLOCKED", "LOCKDOWN", "KILL_SWITCH"}:
        score -= 12.0
        alerts.append("SAFETY_NOT_CLEAR")
    if policy.get("require_recovery_clear") and ctx["recovery"].get("posture") in {"SAFE_MODE", "FAILED", "BLOCKED"}:
        score -= 12.0
        alerts.append("RECOVERY_NOT_CLEAR")
    if policy.get("require_breach_clear") and ctx["breach"].get("posture") in {"CRITICAL", "FREEZE_REQUIRED", "ESCALATED", "BLOCKED"}:
        score -= 14.0
        alerts.append("BREACH_NOT_CLEAR")
    if policy.get("require_exception_clear") and ctx["exception"].get("posture") in {"UNRESOLVED", "BLOCKED", "REMEDIATE"}:
        score -= 12.0
        alerts.append("EXCEPTION_NOT_CLEAR")
    if policy.get("require_closure_clear") and ctx["closure"].get("posture") in {"BLOCKED", "UNRESOLVED", "REMEDIATE"}:
        score -= 12.0
        alerts.append("CLOSURE_NOT_CLEAR")
    if policy.get("require_mandate_clear") and ctx["mandate"].get("posture") in {"BLOCKED", "BREACH", "ESCALATED"}:
        score -= 14.0
        alerts.append("MANDATE_NOT_CLEAR")

    operator_signoff_required = reauthorization_notional >= float(policy.get("reauthorization_notional_threshold", 0.0) or 0.0)
    if operator_signoff_required:
        reasons.append("operator signoff required due to notional size")

    score = max(round(score, 2), 0.0)
    minimum = float(policy.get("minimum_reauthorization_score", 92.0) or 92.0)
    posture = "REAUTHORIZED" if score >= minimum and not alerts else ("OPERATOR_REVIEW" if score >= minimum - 5 else "BLOCKED")
    band = _score_band(score)

    row = {
        "run_id": f"reauth_{int(time.time()*1000)}",
        "captured_at": _now_iso(),
        "title": payload.get("title") or "institutional reauthorization review",
        "summary": payload.get("summary") or "",
        "reauthorization_score": score,
        "reauthorization_band": band,
        "posture": posture,
        "reasons": reasons,
        "alerts": alerts,
        "operator_signoff_required": operator_signoff_required,
        "payload": payload,
    }

    _append(store, "reauthorization_runs", row, policy.get("retain_cycles", 180))
    _append(store, "reauthorization_book", {
        "captured_at": row["captured_at"],
        "posture": posture,
        "reauthorization_band": band,
        "reauthorization_score": score,
        "title": row["title"],
    }, policy.get("retain_cycles", 180))
    for alert in alerts:
        _append(store, "alerts", {"captured_at": row["captured_at"], "alert": alert, "run_id": row["run_id"]}, policy.get("retain_cycles", 180))
    store["latest_reauthorization_run"] = row
    store["last_context"] = ctx
    _save(email, store)
    return _summary_for_email(email)


@router.get("/api/institutional-reauthorization-layer/summary")
def institutional_reauthorization_layer_summary(user=Depends(_require_user)):
    return _summary_for_email(user["email"])


@router.post("/api/institutional-reauthorization-layer/evaluate")
def institutional_reauthorization_layer_evaluate(payload: dict = Body(default={}), user=Depends(_require_user)):
    return _evaluate(user["email"], payload or {})


@router.post("/api/institutional-reauthorization-layer/policy")
def institutional_reauthorization_layer_policy(payload: dict = Body(default={}), user=Depends(_require_user)):
    store = _load(user["email"])
    store["policy"] = {**dict(DEFAULT_POLICY), **(store.get("policy") or {}), **(payload or {})}
    _save(user["email"], store)
    return {"ok": True, "policy": store["policy"]}


@router.post("/api/institutional-reauthorization-layer/bootstrap-demo")
def institutional_reauthorization_layer_bootstrap_demo(user=Depends(_require_user)):
    payload = {
        "title": "bootstrap institutional reauthorization",
        "summary": "Evaluate whether the system can be formally reauthorized after remediation closure.",
        "open_critical_items": 0,
        "open_material_items": 0,
        "evidence_complete": True,
        "controls_restored": True,
        "capital_impact_supervised": True,
        "monitoring_active": True,
        "mandate_aligned": True,
        "reauthorization_notional": 420000.0,
    }
    return _evaluate(user["email"], payload)
