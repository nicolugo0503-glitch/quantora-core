from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(prefix="/api/regulatory-obligation-calendar-deadline-control-layer", tags=["regulatory-obligation-calendar-deadline-control-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "regulatory_obligation_calendar_deadline_control_layer"
DEFAULT_POLICY = {
    "retain_cycles": 180,
    "minimum_score": 96.0,
    "require_regulator_ready": True,
    "require_compliance_automated": True,
    "require_multi_jurisdiction_clear": True,
    "require_supervisory_exam_ready": True,
    "require_filing_submission_clear": True,
    "max_overdue_obligations": 0,
    "max_due_soon_obligations": 3,
    "minimum_calendar_coverage_score": 0.985,
    "minimum_deadline_integrity_score": 0.985,
    "minimum_control_attestation_score": 0.98,
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
            "obligation_calendar": [],
            "deadline_events": [],
            "attestations": [],
            "completed_obligations": [],
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
        "regulatory_obligation_calendar_deadline_control_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "obligation_calendar_count": len(s.get("obligation_calendar") or []),
            "deadline_event_count": len(s.get("deadline_events") or []),
            "attestation_count": len(s.get("attestations") or []),
            "completed_obligation_count": len(s.get("completed_obligations") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "obligation_calendar": s.get("obligation_calendar") or [],
        "deadline_events": s.get("deadline_events") or [],
        "attestations": s.get("attestations") or [],
        "completed_obligations": s.get("completed_obligations") or [],
    }


def _cross_system_context(email: str) -> dict:
    return {
        "captured_at": _now_iso(),
        "regulator_readiness": (_regulator_readiness()._summary_for_email(email).get("institutional_regulator_readiness_interface_status") or {}),
        "compliance_automation": (_compliance()._summary_for_email(email).get("regulatory_compliance_automation_layer_status") or {}),
        "multi_jurisdiction": (_multi_jurisdiction()._summary_for_email(email).get("multi_jurisdiction_governance_layer_status") or {}),
        "supervisory_exam": (_supervisory_exam()._summary_for_email(email).get("institutional_supervisory_examination_command_layer_status") or {}),
        "filing_submission": (_filing_submission()._summary_for_email(email).get("regulatory_filing_submission_orchestration_layer_status") or {}),
    }


def _band(score: float) -> str:
    if score >= 98.0:
        return "DEADLINE_DISCIPLINE_CLEAR"
    if score >= 96.0:
        return "CONTROLLED_TIMELINE"
    if score >= 92.0:
        return "WATCHLIST"
    return "BREACH_RISK"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _cross_system_context(email)
    calendar_coverage_score = float(payload.get("calendar_coverage_score", 0.0) or 0.0)
    deadline_integrity_score = float(payload.get("deadline_integrity_score", 0.0) or 0.0)
    control_attestation_score = float(payload.get("control_attestation_score", 0.0) or 0.0)
    overdue_obligations = int(payload.get("overdue_obligations", 0) or 0)
    due_soon_obligations = int(payload.get("due_soon_obligations", 0) or 0)
    regulator_notice_open = bool(payload.get("regulator_notice_open", False))

    score = 100.0
    reasons = []
    alerts = []
    for val, threshold, mult, reason, code in [
        (calendar_coverage_score, float(policy.get("minimum_calendar_coverage_score", 0.985)), 130.0, "calendar coverage is below policy", "CALENDAR_COVERAGE_WEAK"),
        (deadline_integrity_score, float(policy.get("minimum_deadline_integrity_score", 0.985)), 130.0, "deadline integrity is below policy", "DEADLINE_INTEGRITY_WEAK"),
        (control_attestation_score, float(policy.get("minimum_control_attestation_score", 0.98)), 120.0, "control attestation is below policy", "CONTROL_ATTESTATION_WEAK"),
    ]:
        if val < threshold:
            score -= round((threshold - val) * mult, 2)
            reasons.append(reason)
            alerts.append(code)
    if overdue_obligations > int(policy.get("max_overdue_obligations", 0)):
        score -= min(overdue_obligations * 18.0, 36.0)
        reasons.append("overdue obligations exceed policy")
        alerts.append("OVERDUE_OBLIGATIONS_PRESENT")
    if due_soon_obligations > int(policy.get("max_due_soon_obligations", 3)):
        score -= min((due_soon_obligations - int(policy.get("max_due_soon_obligations", 3))) * 4.0, 16.0)
        reasons.append("due soon obligations exceed controlled window")
        alerts.append("DUE_SOON_PRESSURE_HIGH")
    if regulator_notice_open:
        score -= 8.0
        reasons.append("regulator notice is open against the obligation calendar")
        alerts.append("REGULATOR_NOTICE_OPEN")

    regulator_posture = str(ctx.get("regulator_readiness", {}).get("posture", "UNINITIALIZED"))
    compliance_posture = str(ctx.get("compliance_automation", {}).get("posture", "UNINITIALIZED"))
    governance_posture = str(ctx.get("multi_jurisdiction", {}).get("posture", "UNINITIALIZED"))
    supervisory_posture = str(ctx.get("supervisory_exam", {}).get("posture", "UNINITIALIZED"))
    filing_posture = str(ctx.get("filing_submission", {}).get("posture", "UNINITIALIZED"))

    if policy.get("require_regulator_ready", True) and regulator_posture not in {"REGULATOR_READY", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("regulator readiness posture is not calendar clear"); alerts.append("REGULATOR_READINESS_NOT_CLEAR")
    if policy.get("require_compliance_automated", True) and compliance_posture not in {"AUTOMATED_CLEAR", "CONTROLLED_AUTOMATION", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("compliance automation posture is not calendar clear"); alerts.append("COMPLIANCE_AUTOMATION_NOT_CLEAR")
    if policy.get("require_multi_jurisdiction_clear", True) and governance_posture not in {"GLOBAL_GOVERNANCE_CLEAR", "CONTROLLED_EXPANSION", "UNINITIALIZED"}:
        score -= 7.0; reasons.append("multi-jurisdiction governance posture is not calendar clear"); alerts.append("MULTI_JURISDICTION_NOT_CLEAR")
    if policy.get("require_supervisory_exam_ready", True) and supervisory_posture not in {"EXAM_READY", "WATCH", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("supervisory examination posture is not calendar clear"); alerts.append("SUPERVISORY_EXAM_NOT_CLEAR")
    if policy.get("require_filing_submission_clear", True) and filing_posture not in {"SUBMISSION_CLEAR", "WATCH", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("filing submission posture is not calendar clear"); alerts.append("FILING_SUBMISSION_NOT_CLEAR")

    score = max(round(score, 2), 0.0)
    band = _band(score)
    posture = "DEADLINE_DISCIPLINE_CLEAR" if score >= float(policy.get("minimum_score", 96.0)) else ("WATCH" if score >= 92.0 else "BREACH_RISK")
    operator_review_required = posture != "DEADLINE_DISCIPLINE_CLEAR" or overdue_obligations > 0 or regulator_notice_open
    row = {
        "mission": "QNT30756",
        "evaluated_at": _now_iso(),
        "score": score,
        "band": band,
        "posture": posture,
        "operator_review_required": operator_review_required,
        "calendar_coverage_score": calendar_coverage_score,
        "deadline_integrity_score": deadline_integrity_score,
        "control_attestation_score": control_attestation_score,
        "overdue_obligations": overdue_obligations,
        "due_soon_obligations": due_soon_obligations,
        "regulator_notice_open": regulator_notice_open,
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


@router.post("/schedule-obligation")
def schedule_obligation(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "scheduled_at": _now_iso(),
        "obligation_code": payload.get("obligation_code", "FORM-ADV-UPDATE"),
        "jurisdiction": payload.get("jurisdiction", "US"),
        "entity_scope": payload.get("entity_scope", "quantora-master"),
        "owner": payload.get("owner", "regulatory-operations"),
        "deadline": payload.get("deadline", "2026-05-15T17:00:00Z"),
        "priority": payload.get("priority", "HIGH"),
        "status": payload.get("status", "SCHEDULED"),
        "evidence_pack": payload.get("evidence_pack", "calendar-linked"),
    }
    _append(store, "obligation_calendar", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "obligation": row, "summary": _summary_for_email(email)}


@router.post("/register-deadline")
def register_deadline(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "registered_at": _now_iso(),
        "deadline_code": payload.get("deadline_code", "ADV-AMENDMENT-DEADLINE"),
        "linked_obligation_code": payload.get("linked_obligation_code", "FORM-ADV-UPDATE"),
        "deadline": payload.get("deadline", "2026-05-15T17:00:00Z"),
        "days_remaining": int(payload.get("days_remaining", 12) or 0),
        "control_status": payload.get("control_status", "TRACKED"),
        "attestation_required": bool(payload.get("attestation_required", True)),
    }
    _append(store, "deadline_events", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "deadline_event": row, "summary": _summary_for_email(email)}


@router.post("/attest-control")
def attest_control(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "attested_at": _now_iso(),
        "control_code": payload.get("control_code", "CALENDAR-FOUR-EYES"),
        "attestor": payload.get("attestor", "chief-compliance-officer"),
        "status": payload.get("status", "ATTESTED"),
        "evidence_linkage": payload.get("evidence_linkage", "verified"),
        "notes": payload.get("notes", "control attested against current deadline register"),
    }
    _append(store, "attestations", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "attestation": row, "summary": _summary_for_email(email)}


@router.post("/complete-obligation")
def complete_obligation(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "completed_at": _now_iso(),
        "obligation_code": payload.get("obligation_code", "FORM-ADV-UPDATE"),
        "submission_reference": payload.get("submission_reference", "SUB-ADV-2026-001"),
        "outcome": payload.get("outcome", "ON_TIME"),
        "regulator_acknowledged": bool(payload.get("regulator_acknowledged", True)),
        "archived_evidence_pack": payload.get("archived_evidence_pack", "vault://regulatory/adv/2026/001"),
    }
    _append(store, "completed_obligations", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "completed_obligation": row, "summary": _summary_for_email(email)}


@router.get("/policy")
def policy(user=Depends(_require_user)):
    return {"ok": True, "policy": _load(user["email"]).get("policy") or dict(DEFAULT_POLICY)}


@router.post("/bootstrap-demo")
def bootstrap_demo(user=Depends(_require_user)):
    email = user["email"]
    schedule_obligation({
        "obligation_code": "AIFMD-ANNUAL-RETURN",
        "jurisdiction": "EU",
        "entity_scope": "quantora-eu-master",
        "owner": "regulatory-operations",
        "deadline": "2026-06-20T16:00:00Z",
        "priority": "HIGH",
        "status": "SCHEDULED",
        "evidence_pack": "eu-aifmd-2026",
    }, user)
    register_deadline({
        "deadline_code": "AIFMD-2026-FILING",
        "linked_obligation_code": "AIFMD-ANNUAL-RETURN",
        "deadline": "2026-06-20T16:00:00Z",
        "days_remaining": 21,
        "control_status": "TRACKED",
        "attestation_required": True,
    }, user)
    attest_control({
        "control_code": "CALENDAR-DEADLINE-RECON",
        "attestor": "chief-compliance-officer",
        "status": "ATTESTED",
        "evidence_linkage": "verified",
        "notes": "cross-jurisdiction obligation calendar reconciled to current filing plan",
    }, user)
    complete_obligation({
        "obligation_code": "AIFMD-ANNUAL-RETURN",
        "submission_reference": "EU-AIFMD-2026-020",
        "outcome": "READY_FOR_SUBMISSION",
        "regulator_acknowledged": False,
        "archived_evidence_pack": "vault://regulatory/eu/aifmd/2026/020",
    }, user)
    run = _evaluate(email, {
        "calendar_coverage_score": 0.995,
        "deadline_integrity_score": 0.993,
        "control_attestation_score": 0.991,
        "overdue_obligations": 0,
        "due_soon_obligations": 2,
        "regulator_notice_open": False,
    })
    return {"ok": True, "run": run, "summary": _summary_for_email(email)}
