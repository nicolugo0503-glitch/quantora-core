from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(prefix="/api/regulatory-compliance-automation-layer", tags=["regulatory-compliance-automation-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "regulatory_compliance_automation_layer"
DEFAULT_POLICY = {
    "retain_cycles": 180,
    "minimum_score": 96.0,
    "require_regulator_ready": True,
    "require_audit_ready": True,
    "minimum_filing_accuracy_score": 0.985,
    "minimum_monitoring_coverage_score": 0.985,
    "minimum_exception_clearance_score": 0.98,
    "max_overdue_filings": 0,
    "max_open_exceptions": 2,
}

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu
def _regulator_readiness():
    from backend.app import qnt30749_institutional_regulator_readiness_interface_router as regulator_readiness
    return regulator_readiness
def _audit_ready():
    from backend.app import qnt30747_institutional_audit_readiness_certification_layer_router as audit_ready
    return audit_ready
def _auditor_interface():
    from backend.app import qnt30748_institutional_external_auditor_interface_layer_router as auditor_interface
    return auditor_interface
def _reporting():
    from backend.app import qnt30715_reporting_disclosure_automation_layer_router as reporting
    return reporting


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
            "filings": [],
            "monitoring_events": [],
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
        "regulatory_compliance_automation_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "filing_count": len(s.get("filings") or []),
            "monitoring_event_count": len(s.get("monitoring_events") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "filings": s.get("filings") or [],
        "monitoring_events": s.get("monitoring_events") or [],
    }

def _cross_system_context(email: str) -> dict:
    return {
        "captured_at": _now_iso(),
        "regulator_readiness": (_regulator_readiness()._summary_for_email(email).get("institutional_regulator_readiness_interface_status") or {}),
        "audit_readiness": (_audit_ready()._summary_for_email(email).get("institutional_audit_readiness_certification_layer_status") or {}),
        "external_auditor_interface": (_auditor_interface()._summary_for_email(email).get("institutional_external_auditor_interface_layer_status") or {}),
        "reporting": (_reporting()._summary_for_email(email).get("reporting_disclosure_automation_layer_status") or {}),
    }

def _band(score: float) -> str:
    if score >= 98.0:
        return "AUTOMATED_CLEAR"
    if score >= 96.0:
        return "CONTROLLED_AUTOMATION"
    if score >= 92.0:
        return "MANUAL_INTERVENTION"
    return "BLOCKED"

def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _cross_system_context(email)
    filing_accuracy_score = float(payload.get("filing_accuracy_score", 0.0) or 0.0)
    monitoring_coverage_score = float(payload.get("monitoring_coverage_score", 0.0) or 0.0)
    exception_clearance_score = float(payload.get("exception_clearance_score", 0.0) or 0.0)
    overdue_filings = int(payload.get("overdue_filings", 0) or 0)
    open_exceptions = int(payload.get("open_exceptions", 0) or 0)
    auto_submission_enabled = bool(payload.get("auto_submission_enabled", False))

    score = 100.0
    reasons = []
    alerts = []
    for val, threshold, mult, reason, code in [
        (filing_accuracy_score, float(policy.get("minimum_filing_accuracy_score", 0.985)), 130.0, "filing accuracy is below policy", "FILING_ACCURACY_WEAK"),
        (monitoring_coverage_score, float(policy.get("minimum_monitoring_coverage_score", 0.985)), 120.0, "monitoring coverage is below policy", "MONITORING_COVERAGE_WEAK"),
        (exception_clearance_score, float(policy.get("minimum_exception_clearance_score", 0.98)), 110.0, "exception clearance is below policy", "EXCEPTION_CLEARANCE_WEAK"),
    ]:
        if val < threshold:
            score -= round((threshold - val) * mult, 2)
            reasons.append(reason)
            alerts.append(code)
    if overdue_filings > int(policy.get("max_overdue_filings", 0)):
        score -= min((overdue_filings - int(policy.get("max_overdue_filings", 0))) * 10.0, 30.0)
        reasons.append("overdue filings exceed policy")
        alerts.append("OVERDUE_FILINGS_OPEN")
    if open_exceptions > int(policy.get("max_open_exceptions", 2)):
        score -= min((open_exceptions - int(policy.get("max_open_exceptions", 2))) * 4.0, 16.0)
        reasons.append("open compliance exceptions exceed policy")
        alerts.append("OPEN_EXCEPTIONS_HIGH")
    if not auto_submission_enabled:
        score -= 5.0
        reasons.append("automated submission is not enabled")
        alerts.append("AUTO_SUBMISSION_DISABLED")

    regulator_posture = str(ctx.get("regulator_readiness", {}).get("posture", "UNINITIALIZED"))
    audit_posture = str(ctx.get("audit_readiness", {}).get("posture", "UNINITIALIZED"))
    auditor_posture = str(ctx.get("external_auditor_interface", {}).get("posture", "UNINITIALIZED"))
    reporting_posture = str(ctx.get("reporting", {}).get("posture", "UNINITIALIZED"))
    if policy.get("require_regulator_ready", True) and regulator_posture not in {"REGULATOR_READY", "UNINITIALIZED"}:
        score -= 10.0; reasons.append("regulator readiness posture is not clear"); alerts.append("REGULATOR_READINESS_NOT_CLEAR")
    if policy.get("require_audit_ready", True) and audit_posture not in {"AUDIT_READY", "UNINITIALIZED"}:
        score -= 10.0; reasons.append("audit readiness posture is not clear"); alerts.append("AUDIT_NOT_CLEAR")
    if auditor_posture not in {"EXTERNAL_AUDITOR_READY", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("external auditor interface posture is not clear"); alerts.append("AUDITOR_INTERFACE_NOT_CLEAR")
    if reporting_posture not in {"AUTOMATED_CLEAR", "CONTROLLED", "APPROVED", "UNINITIALIZED"}:
        score -= 6.0; reasons.append("reporting posture is not compliance clear"); alerts.append("REPORTING_NOT_CLEAR")

    score = max(round(score, 2), 0.0)
    band = _band(score)
    posture = "AUTOMATED_CLEAR" if score >= float(policy.get("minimum_score", 96.0)) else ("WATCH" if score >= 92.0 else "BLOCKED")
    operator_review_required = posture != "AUTOMATED_CLEAR" or overdue_filings > 0
    row = {
        "mission": "QNT30750",
        "evaluated_at": _now_iso(),
        "score": score,
        "band": band,
        "posture": posture,
        "operator_review_required": operator_review_required,
        "filing_accuracy_score": filing_accuracy_score,
        "monitoring_coverage_score": monitoring_coverage_score,
        "exception_clearance_score": exception_clearance_score,
        "overdue_filings": overdue_filings,
        "open_exceptions": open_exceptions,
        "auto_submission_enabled": auto_submission_enabled,
        "reasons": reasons,
        "alerts": alerts,
        "context": ctx,
    }
    _append(store, "runs", row, policy.get("retain_cycles", 180))
    for a in alerts:
        _append(store, "alerts", {"at": _now_iso(), "code": a, "score": score}, policy.get("retain_cycles", 180))
    store["latest_run"] = row
    store["last_context"] = ctx
    _save(email, store)
    return row

@router.get("/summary")
def summary(user=Depends(_require_user)):
    return _summary_for_email(user["email"])

@router.post("/evaluate")
def evaluate(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    run = _evaluate(email, payload)
    return {"ok": True, "run": run, "summary": _summary_for_email(email)}

@router.post("/file-report")
def file_report(payload: dict = Body(default={}), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    row = {
        "at": _now_iso(),
        "filing_type": str(payload.get("filing_type") or "Form PF"),
        "jurisdiction": str(payload.get("jurisdiction") or "US"),
        "status": str(payload.get("status") or "queued"),
        "automation_mode": str(payload.get("automation_mode") or "automatic"),
    }
    _append(store, "filings", row, (store.get("policy") or {}).get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "filing": row, "summary": _summary_for_email(email)}

@router.post("/monitor")
def monitor(payload: dict = Body(default={}), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    row = {
        "at": _now_iso(),
        "control_domain": str(payload.get("control_domain") or "trade-surveillance"),
        "status": str(payload.get("status") or "clear"),
        "exceptions_detected": int(payload.get("exceptions_detected", 0) or 0),
    }
    _append(store, "monitoring_events", row, (store.get("policy") or {}).get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "monitoring_event": row, "summary": _summary_for_email(email)}

@router.post("/policy")
def policy(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    store["policy"] = {**dict(DEFAULT_POLICY), **(store.get("policy") or {}), **payload}
    _save(email, store)
    return {"ok": True, "policy": store["policy"], "summary": _summary_for_email(email)}

@router.post("/bootstrap-demo")
def bootstrap_demo(user=Depends(_require_user)):
    email = user["email"]
    _load(email)
    file_report({"filing_type": "Form PF", "jurisdiction": "US", "status": "queued", "automation_mode": "automatic"}, {"email": email})
    monitor({"control_domain": "marketing-rule", "status": "clear", "exceptions_detected": 0}, {"email": email})
    _evaluate(email, {
        "filing_accuracy_score": 0.992,
        "monitoring_coverage_score": 0.991,
        "exception_clearance_score": 0.988,
        "overdue_filings": 0,
        "open_exceptions": 1,
        "auto_submission_enabled": True,
    })
    return {"ok": True, "summary": _summary_for_email(email)}
