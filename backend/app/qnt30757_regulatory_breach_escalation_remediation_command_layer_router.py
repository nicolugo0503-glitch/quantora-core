from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(prefix="/api/regulatory-breach-escalation-remediation-command-layer", tags=["regulatory-breach-escalation-remediation-command-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "regulatory_breach_escalation_remediation_command_layer"
DEFAULT_POLICY = {
    "retain_cycles": 180,
    "minimum_score": 96.0,
    "require_regulator_ready": True,
    "require_compliance_automated": True,
    "require_multi_jurisdiction_clear": True,
    "require_supervisory_exam_ready": True,
    "require_filing_submission_clear": True,
    "require_deadline_control_clear": True,
    "max_open_breaches": 0,
    "max_high_severity_breaches": 0,
    "minimum_remediation_coverage_score": 0.985,
    "minimum_escalation_timeliness_score": 0.985,
    "minimum_closure_integrity_score": 0.985,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _regulator_readiness():
    from backend.app import qnt30749_institutional_regulator_readiness_interface_router as regulator_readiness
    return regulator_readiness


def _compliance():
    from backend.app import qnt30750_regulatory_compliance_automation_layer_router as compliance
    return compliance


def _multi_jurisdiction():
    from backend.app import qnt30751_multi_jurisdiction_governance_layer_router as multi_jurisdiction
    return multi_jurisdiction


def _supervisory_exam():
    from backend.app import qnt30754_institutional_supervisory_examination_command_layer_router as supervisory_exam
    return supervisory_exam


def _filing_submission():
    from backend.app import qnt30755_regulatory_filing_submission_orchestration_layer_router as filing_submission
    return filing_submission


def _deadline_control():
    from backend.app import qnt30756_regulatory_obligation_calendar_deadline_control_layer_router as deadline_control
    return deadline_control


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
            "breaches": [],
            "escalations": [],
            "remediations": [],
            "closures": [],
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
        "regulatory_breach_escalation_remediation_command_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "breach_count": len(s.get("breaches") or []),
            "escalation_count": len(s.get("escalations") or []),
            "remediation_count": len(s.get("remediations") or []),
            "closure_count": len(s.get("closures") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "breaches": s.get("breaches") or [],
        "escalations": s.get("escalations") or [],
        "remediations": s.get("remediations") or [],
        "closures": s.get("closures") or [],
    }


def _cross_system_context(email: str) -> dict:
    return {
        "captured_at": _now_iso(),
        "regulator_readiness": (_regulator_readiness()._summary_for_email(email).get("institutional_regulator_readiness_interface_status") or {}),
        "compliance_automation": (_compliance()._summary_for_email(email).get("regulatory_compliance_automation_layer_status") or {}),
        "multi_jurisdiction": (_multi_jurisdiction()._summary_for_email(email).get("multi_jurisdiction_governance_layer_status") or {}),
        "supervisory_exam": (_supervisory_exam()._summary_for_email(email).get("institutional_supervisory_examination_command_layer_status") or {}),
        "filing_submission": (_filing_submission()._summary_for_email(email).get("regulatory_filing_submission_orchestration_layer_status") or {}),
        "deadline_control": (_deadline_control()._summary_for_email(email).get("regulatory_obligation_calendar_deadline_control_layer_status") or {}),
    }


def _band(score: float) -> str:
    if score >= 98.0:
        return "BREACH_COMMAND_CLEAR"
    if score >= 96.0:
        return "CONTROLLED_REMEDIATION"
    if score >= 92.0:
        return "WATCHLIST"
    return "ESCALATION_ACTIVE"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _cross_system_context(email)
    remediation_coverage_score = float(payload.get("remediation_coverage_score", 0.0) or 0.0)
    escalation_timeliness_score = float(payload.get("escalation_timeliness_score", 0.0) or 0.0)
    closure_integrity_score = float(payload.get("closure_integrity_score", 0.0) or 0.0)
    open_breaches = int(payload.get("open_breaches", 0) or 0)
    high_severity_breaches = int(payload.get("high_severity_breaches", 0) or 0)
    regulator_watch_active = bool(payload.get("regulator_watch_active", False))

    score = 100.0
    reasons = []
    alerts = []
    for val, threshold, mult, reason, code in [
        (remediation_coverage_score, float(policy.get("minimum_remediation_coverage_score", 0.985)), 130.0, "remediation coverage is below policy", "REMEDIATION_COVERAGE_WEAK"),
        (escalation_timeliness_score, float(policy.get("minimum_escalation_timeliness_score", 0.985)), 130.0, "escalation timeliness is below policy", "ESCALATION_TIMELINESS_WEAK"),
        (closure_integrity_score, float(policy.get("minimum_closure_integrity_score", 0.985)), 130.0, "closure integrity is below policy", "CLOSURE_INTEGRITY_WEAK"),
    ]:
        if val < threshold:
            score -= round((threshold - val) * mult, 2)
            reasons.append(reason)
            alerts.append(code)
    if open_breaches > int(policy.get("max_open_breaches", 0)):
        score -= min(open_breaches * 18.0, 36.0)
        reasons.append("open breaches exceed policy")
        alerts.append("OPEN_BREACHES_PRESENT")
    if high_severity_breaches > int(policy.get("max_high_severity_breaches", 0)):
        score -= min(high_severity_breaches * 14.0, 28.0)
        reasons.append("high severity breaches exceed policy")
        alerts.append("HIGH_SEVERITY_BREACH_PRESENT")
    if regulator_watch_active:
        score -= 10.0
        reasons.append("regulatory watch status is active")
        alerts.append("REGULATOR_WATCH_ACTIVE")

    regulator_posture = str(ctx.get("regulator_readiness", {}).get("posture", "UNINITIALIZED"))
    compliance_posture = str(ctx.get("compliance_automation", {}).get("posture", "UNINITIALIZED"))
    governance_posture = str(ctx.get("multi_jurisdiction", {}).get("posture", "UNINITIALIZED"))
    supervisory_posture = str(ctx.get("supervisory_exam", {}).get("posture", "UNINITIALIZED"))
    filing_posture = str(ctx.get("filing_submission", {}).get("posture", "UNINITIALIZED"))
    deadline_posture = str(ctx.get("deadline_control", {}).get("posture", "UNINITIALIZED"))

    if policy.get("require_regulator_ready", True) and regulator_posture not in {"REGULATOR_READY", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("regulator readiness posture is not breach-clear"); alerts.append("REGULATOR_READINESS_NOT_CLEAR")
    if policy.get("require_compliance_automated", True) and compliance_posture not in {"AUTOMATED_CLEAR", "CONTROLLED_AUTOMATION", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("compliance automation posture is not breach-clear"); alerts.append("COMPLIANCE_AUTOMATION_NOT_CLEAR")
    if policy.get("require_multi_jurisdiction_clear", True) and governance_posture not in {"GLOBAL_GOVERNANCE_CLEAR", "CONTROLLED_EXPANSION", "UNINITIALIZED"}:
        score -= 7.0; reasons.append("multi-jurisdiction governance posture is not breach-clear"); alerts.append("MULTI_JURISDICTION_NOT_CLEAR")
    if policy.get("require_supervisory_exam_ready", True) and supervisory_posture not in {"EXAM_READY", "WATCH", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("supervisory examination posture is not breach-clear"); alerts.append("SUPERVISORY_EXAM_NOT_CLEAR")
    if policy.get("require_filing_submission_clear", True) and filing_posture not in {"SUBMISSION_CLEAR", "WATCH", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("filing submission posture is not breach-clear"); alerts.append("FILING_SUBMISSION_NOT_CLEAR")
    if policy.get("require_deadline_control_clear", True) and deadline_posture not in {"DEADLINE_DISCIPLINE_CLEAR", "WATCH", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("deadline control posture is not breach-clear"); alerts.append("DEADLINE_CONTROL_NOT_CLEAR")

    score = max(round(score, 2), 0.0)
    band = _band(score)
    posture = "BREACH_COMMAND_CLEAR" if score >= float(policy.get("minimum_score", 96.0)) else ("WATCH" if score >= 92.0 else "ESCALATION_ACTIVE")
    operator_review_required = posture != "BREACH_COMMAND_CLEAR" or open_breaches > 0 or high_severity_breaches > 0 or regulator_watch_active
    row = {
        "mission": "QNT30757",
        "evaluated_at": _now_iso(),
        "score": score,
        "band": band,
        "posture": posture,
        "operator_review_required": operator_review_required,
        "remediation_coverage_score": remediation_coverage_score,
        "escalation_timeliness_score": escalation_timeliness_score,
        "closure_integrity_score": closure_integrity_score,
        "open_breaches": open_breaches,
        "high_severity_breaches": high_severity_breaches,
        "regulator_watch_active": regulator_watch_active,
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


@router.post("/register-breach")
def register_breach(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "registered_at": _now_iso(),
        "breach_code": payload.get("breach_code", "LATE_REGULATORY_FILING"),
        "severity": payload.get("severity", "HIGH"),
        "jurisdiction": payload.get("jurisdiction", "US"),
        "entity_scope": payload.get("entity_scope", "quantora-master"),
        "owner": payload.get("owner", "chief-compliance-officer"),
        "status": payload.get("status", "OPEN"),
        "source": payload.get("source", "deadline-control-layer"),
        "impact": payload.get("impact", "regulatory timetable deviation"),
    }
    _append(store, "breaches", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "breach": row, "summary": _summary_for_email(email)}


@router.post("/launch-remediation")
def launch_remediation(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    escalation = {
        "escalated_at": _now_iso(),
        "breach_code": payload.get("breach_code", "LATE_REGULATORY_FILING"),
        "escalation_route": payload.get("escalation_route", "capital-committee-and-compliance"),
        "escalation_owner": payload.get("escalation_owner", "institutional-governance"),
        "status": payload.get("escalation_status", "ESCALATED"),
        "deadline_extension_required": bool(payload.get("deadline_extension_required", False)),
    }
    remediation = {
        "launched_at": _now_iso(),
        "breach_code": payload.get("breach_code", "LATE_REGULATORY_FILING"),
        "remediation_plan": payload.get("remediation_plan", "root-cause-fix-and-regulator-notice"),
        "control_owner": payload.get("control_owner", "regulatory-operations"),
        "target_closure_date": payload.get("target_closure_date", "2026-06-30T17:00:00Z"),
        "status": payload.get("remediation_status", "IN_PROGRESS"),
    }
    _append(store, "escalations", escalation, policy.get("retain_cycles", 180))
    _append(store, "remediations", remediation, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "escalation": escalation, "remediation": remediation, "summary": _summary_for_email(email)}


@router.post("/close-remediation")
def close_remediation(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "closed_at": _now_iso(),
        "breach_code": payload.get("breach_code", "LATE_REGULATORY_FILING"),
        "closure_status": payload.get("closure_status", "CLOSED"),
        "closure_basis": payload.get("closure_basis", "control-restored-and-governance-approved"),
        "regulator_confirmed": bool(payload.get("regulator_confirmed", True)),
        "closure_evidence_pack": payload.get("closure_evidence_pack", "vault://regulatory/breaches/2026/001"),
    }
    _append(store, "closures", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "closure": row, "summary": _summary_for_email(email)}


@router.get("/policy")
def policy(user=Depends(_require_user)):
    return {"ok": True, "policy": _load(user["email"]).get("policy") or dict(DEFAULT_POLICY)}


@router.post("/bootstrap-demo")
def bootstrap_demo(user=Depends(_require_user)):
    email = user["email"]
    register_breach({
        "breach_code": "AIFMD-DEADLINE-MISS",
        "severity": "HIGH",
        "jurisdiction": "EU",
        "entity_scope": "quantora-eu-master",
        "owner": "chief-compliance-officer",
        "status": "OPEN",
        "source": "obligation-calendar",
        "impact": "regulatory filing submitted outside controlled window",
    }, user)
    launch_remediation({
        "breach_code": "AIFMD-DEADLINE-MISS",
        "escalation_route": "executive-ai-command-and-compliance",
        "escalation_owner": "institutional-governance",
        "escalation_status": "ESCALATED",
        "deadline_extension_required": True,
        "remediation_plan": "submit extension notice and restore deadline controls",
        "control_owner": "regulatory-operations",
        "target_closure_date": "2026-07-05T17:00:00Z",
        "remediation_status": "IN_PROGRESS",
    }, user)
    close_remediation({
        "breach_code": "AIFMD-DEADLINE-MISS",
        "closure_status": "CONTROLLED_CLOSURE",
        "closure_basis": "root cause fixed and governance reauthorized",
        "regulator_confirmed": True,
        "closure_evidence_pack": "vault://regulatory/eu/breaches/2026/005",
    }, user)
    run = _evaluate(email, {
        "remediation_coverage_score": 0.993,
        "escalation_timeliness_score": 0.992,
        "closure_integrity_score": 0.991,
        "open_breaches": 0,
        "high_severity_breaches": 0,
        "regulator_watch_active": False,
    })
    return {"ok": True, "run": run, "summary": _summary_for_email(email)}
