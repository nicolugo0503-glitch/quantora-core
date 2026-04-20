from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(prefix="/api/regulatory-enforcement-response-consent-order-command-layer", tags=["regulatory-enforcement-response-consent-order-command-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "regulatory_enforcement_response_consent_order_command_layer"
DEFAULT_POLICY = {
    "retain_cycles": 180,
    "minimum_score": 96.0,
    "require_regulator_ready": True,
    "require_compliance_automated": True,
    "require_multi_jurisdiction_clear": True,
    "require_supervisory_exam_ready": True,
    "require_filing_submission_clear": True,
    "require_deadline_control_clear": True,
    "require_breach_command_clear": True,
    "max_open_enforcement_actions": 0,
    "max_unanswered_regulator_requests": 0,
    "minimum_response_timeliness_score": 0.985,
    "minimum_evidence_completeness_score": 0.985,
    "minimum_consent_order_readiness_score": 0.985,
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


def _breach_command():
    from backend.app import qnt30757_regulatory_breach_escalation_remediation_command_layer_router as breach_command
    return breach_command


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
            "actions": [],
            "responses": [],
            "consent_orders": [],
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
        "regulatory_enforcement_response_consent_order_command_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "action_count": len(s.get("actions") or []),
            "response_count": len(s.get("responses") or []),
            "consent_order_count": len(s.get("consent_orders") or []),
            "closure_count": len(s.get("closures") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "actions": s.get("actions") or [],
        "responses": s.get("responses") or [],
        "consent_orders": s.get("consent_orders") or [],
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
        "breach_command": (_breach_command()._summary_for_email(email).get("regulatory_breach_escalation_remediation_command_layer_status") or {}),
    }


def _band(score: float) -> str:
    if score >= 98.0:
        return "ENFORCEMENT_COMMAND_CLEAR"
    if score >= 96.0:
        return "CONTROLLED_RESPONSE"
    if score >= 92.0:
        return "WATCHLIST"
    return "REGULATORY_RESPONSE_ACTIVE"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _cross_system_context(email)
    response_timeliness_score = float(payload.get("response_timeliness_score", 0.0) or 0.0)
    evidence_completeness_score = float(payload.get("evidence_completeness_score", 0.0) or 0.0)
    consent_order_readiness_score = float(payload.get("consent_order_readiness_score", 0.0) or 0.0)
    open_enforcement_actions = int(payload.get("open_enforcement_actions", 0) or 0)
    unanswered_regulator_requests = int(payload.get("unanswered_regulator_requests", 0) or 0)
    active_consent_order = bool(payload.get("active_consent_order", False))

    score = 100.0
    reasons = []
    alerts = []
    for val, threshold, mult, reason, code in [
        (response_timeliness_score, float(policy.get("minimum_response_timeliness_score", 0.985)), 130.0, "response timeliness is below policy", "RESPONSE_TIMELINESS_WEAK"),
        (evidence_completeness_score, float(policy.get("minimum_evidence_completeness_score", 0.985)), 130.0, "evidence completeness is below policy", "EVIDENCE_COMPLETENESS_WEAK"),
        (consent_order_readiness_score, float(policy.get("minimum_consent_order_readiness_score", 0.985)), 130.0, "consent order readiness is below policy", "CONSENT_ORDER_READINESS_WEAK"),
    ]:
        if val < threshold:
            score -= round((threshold - val) * mult, 2)
            reasons.append(reason)
            alerts.append(code)
    if open_enforcement_actions > int(policy.get("max_open_enforcement_actions", 0)):
        score -= min(open_enforcement_actions * 18.0, 36.0)
        reasons.append("open enforcement actions exceed policy")
        alerts.append("OPEN_ENFORCEMENT_ACTIONS_PRESENT")
    if unanswered_regulator_requests > int(policy.get("max_unanswered_regulator_requests", 0)):
        score -= min(unanswered_regulator_requests * 12.0, 24.0)
        reasons.append("unanswered regulator requests exceed policy")
        alerts.append("UNANSWERED_REGULATOR_REQUESTS_PRESENT")
    if active_consent_order:
        score -= 10.0
        reasons.append("active consent order requires escalated response command")
        alerts.append("ACTIVE_CONSENT_ORDER")

    regulator_posture = str(ctx.get("regulator_readiness", {}).get("posture", "UNINITIALIZED"))
    compliance_posture = str(ctx.get("compliance_automation", {}).get("posture", "UNINITIALIZED"))
    governance_posture = str(ctx.get("multi_jurisdiction", {}).get("posture", "UNINITIALIZED"))
    supervisory_posture = str(ctx.get("supervisory_exam", {}).get("posture", "UNINITIALIZED"))
    filing_posture = str(ctx.get("filing_submission", {}).get("posture", "UNINITIALIZED"))
    deadline_posture = str(ctx.get("deadline_control", {}).get("posture", "UNINITIALIZED"))
    breach_posture = str(ctx.get("breach_command", {}).get("posture", "UNINITIALIZED"))

    if policy.get("require_regulator_ready", True) and regulator_posture not in {"REGULATOR_READY", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("regulator readiness posture is not enforcement-clear"); alerts.append("REGULATOR_READINESS_NOT_CLEAR")
    if policy.get("require_compliance_automated", True) and compliance_posture not in {"AUTOMATED_CLEAR", "CONTROLLED_AUTOMATION", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("compliance automation posture is not enforcement-clear"); alerts.append("COMPLIANCE_AUTOMATION_NOT_CLEAR")
    if policy.get("require_multi_jurisdiction_clear", True) and governance_posture not in {"GLOBAL_GOVERNANCE_CLEAR", "CONTROLLED_EXPANSION", "UNINITIALIZED"}:
        score -= 7.0; reasons.append("multi-jurisdiction governance posture is not enforcement-clear"); alerts.append("MULTI_JURISDICTION_NOT_CLEAR")
    if policy.get("require_supervisory_exam_ready", True) and supervisory_posture not in {"EXAM_READY", "WATCH", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("supervisory examination posture is not enforcement-clear"); alerts.append("SUPERVISORY_EXAM_NOT_CLEAR")
    if policy.get("require_filing_submission_clear", True) and filing_posture not in {"SUBMISSION_CLEAR", "WATCH", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("filing submission posture is not enforcement-clear"); alerts.append("FILING_SUBMISSION_NOT_CLEAR")
    if policy.get("require_deadline_control_clear", True) and deadline_posture not in {"DEADLINE_DISCIPLINE_CLEAR", "WATCH", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("deadline control posture is not enforcement-clear"); alerts.append("DEADLINE_CONTROL_NOT_CLEAR")
    if policy.get("require_breach_command_clear", True) and breach_posture not in {"BREACH_COMMAND_CLEAR", "WATCH", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("breach command posture is not enforcement-clear"); alerts.append("BREACH_COMMAND_NOT_CLEAR")

    score = max(round(score, 2), 0.0)
    band = _band(score)
    posture = "ENFORCEMENT_COMMAND_CLEAR" if score >= float(policy.get("minimum_score", 96.0)) else ("WATCH" if score >= 92.0 else "REGULATORY_RESPONSE_ACTIVE")
    operator_review_required = posture != "ENFORCEMENT_COMMAND_CLEAR" or open_enforcement_actions > 0 or unanswered_regulator_requests > 0 or active_consent_order
    row = {
        "mission": "QNT30758",
        "evaluated_at": _now_iso(),
        "score": score,
        "band": band,
        "posture": posture,
        "operator_review_required": operator_review_required,
        "response_timeliness_score": response_timeliness_score,
        "evidence_completeness_score": evidence_completeness_score,
        "consent_order_readiness_score": consent_order_readiness_score,
        "open_enforcement_actions": open_enforcement_actions,
        "unanswered_regulator_requests": unanswered_regulator_requests,
        "active_consent_order": active_consent_order,
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


@router.post("/register-action")
def register_action(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "registered_at": _now_iso(),
        "action_code": payload.get("action_code", "REGULATORY_ENFORCEMENT_NOTICE"),
        "authority": payload.get("authority", "SEC"),
        "jurisdiction": payload.get("jurisdiction", "US"),
        "entity_scope": payload.get("entity_scope", "quantora-master"),
        "severity": payload.get("severity", "HIGH"),
        "status": payload.get("status", "OPEN"),
        "owner": payload.get("owner", "chief-compliance-officer"),
    }
    _append(store, "actions", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "action": row, "summary": _summary_for_email(email)}


@router.post("/respond")
def respond(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "responded_at": _now_iso(),
        "action_code": payload.get("action_code", "REGULATORY_ENFORCEMENT_NOTICE"),
        "response_owner": payload.get("response_owner", "regulatory-operations"),
        "response_route": payload.get("response_route", "executive-ai-command-and-counsel"),
        "evidence_pack": payload.get("evidence_pack", "vault://regulatory/enforcement/2026/001"),
        "response_status": payload.get("response_status", "SUBMITTED"),
    }
    _append(store, "responses", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "response": row, "summary": _summary_for_email(email)}


@router.post("/issue-consent-order")
def issue_consent_order(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "issued_at": _now_iso(),
        "action_code": payload.get("action_code", "REGULATORY_ENFORCEMENT_NOTICE"),
        "consent_order_code": payload.get("consent_order_code", "CONSENT-ORDER-001"),
        "remediation_program": payload.get("remediation_program", "governance-remediation-and-reporting"),
        "oversight_owner": payload.get("oversight_owner", "institutional-governance"),
        "status": payload.get("status", "ACTIVE"),
    }
    _append(store, "consent_orders", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "consent_order": row, "summary": _summary_for_email(email)}


@router.post("/close-action")
def close_action(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "closed_at": _now_iso(),
        "action_code": payload.get("action_code", "REGULATORY_ENFORCEMENT_NOTICE"),
        "closure_status": payload.get("closure_status", "CLOSED"),
        "closure_basis": payload.get("closure_basis", "regulator satisfied and controls restored"),
        "regulator_confirmed": bool(payload.get("regulator_confirmed", True)),
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
    register_action({
        "action_code": "CONSENT_ORDER_WARNING",
        "authority": "SEC",
        "jurisdiction": "US",
        "entity_scope": "quantora-master",
        "severity": "HIGH",
        "status": "OPEN",
        "owner": "chief-compliance-officer",
    }, user)
    respond({
        "action_code": "CONSENT_ORDER_WARNING",
        "response_owner": "regulatory-operations",
        "response_route": "executive-ai-command-and-counsel",
        "evidence_pack": "vault://regulatory/enforcement/us/2026/011",
        "response_status": "SUBMITTED",
    }, user)
    issue_consent_order({
        "action_code": "CONSENT_ORDER_WARNING",
        "consent_order_code": "SEC-CO-2026-011",
        "remediation_program": "independent-review-and-control-recertification",
        "oversight_owner": "institutional-governance",
        "status": "ACTIVE",
    }, user)
    close_action({
        "action_code": "CONSENT_ORDER_WARNING",
        "closure_status": "CONTROLLED_CLOSURE",
        "closure_basis": "remediation delivered and regulator acceptance recorded",
        "regulator_confirmed": True,
    }, user)
    run = _evaluate(email, {
        "response_timeliness_score": 0.992,
        "evidence_completeness_score": 0.993,
        "consent_order_readiness_score": 0.991,
        "open_enforcement_actions": 0,
        "unanswered_regulator_requests": 0,
        "active_consent_order": False,
    })
    return {"ok": True, "run": run, "summary": _summary_for_email(email)}
