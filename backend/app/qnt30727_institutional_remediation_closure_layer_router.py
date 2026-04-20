from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["institutional-remediation-closure-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "institutional_remediation_closure_layer"
DEFAULT_POLICY = {
    "retain_cycles": 180,
    "minimum_closure_score": 90.0,
    "require_operator_clear": True,
    "require_release_clear": True,
    "require_safety_clear": True,
    "require_recovery_clear": True,
    "require_exception_clearance_case": True,
    "require_verified_root_cause": True,
    "max_open_material_remediations": 1,
    "max_open_critical_remediations": 0,
    "operator_review_notional_threshold": 500000.0,
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


def _mandate():
    from backend.app import qnt30724_institutional_mandate_enforcement_layer_router as mandate
    return mandate


def _charter():
    from backend.app import qnt30723_institutional_allocation_execution_charter_layer_router as charter
    return charter


def _policy_layer():
    from backend.app import qnt30722_executive_capital_allocation_policy_layer_router as policy_layer
    return policy_layer


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
            "closure_runs": [],
            "alerts": [],
            "exception_book": [],
            "latest_closure_run": None,
            "last_context": {},
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))


def _save(email: str, data: dict):
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")


def _summary_for_email(email: str) -> dict:
    s = _load(email)
    latest = s.get("latest_closure_run") or {}
    return {
        "institutional_remediation_closure_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("closure_score"),
            "closure_band": latest.get("closure_band", "UNSET"),
            "resolution_run_count": len(s.get("closure_runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "operator_signoff_required": bool(latest.get("operator_signoff_required", False)),
        },
        "latest_closure_run": latest,
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
    exception_layer = _load(email)
    mandate = _mandate()._summary_for_email(email)
    charter = _charter()._summary_for_email(email)
    policy_layer = _policy_layer()._summary_for_email(email)
    return {
        "captured_at": _now_iso(),
        "operator": operator.get("operator_console_status") or {},
        "release": release.get("release_control_status") or {},
        "safety": safety.get("safety_layer_status") or {},
        "forensic": forensic.get("forensic_status") or {},
        "recovery": recovery.get("recovery_status") or {},
        "breach": breach.get("institutional_breach_escalation_layer_status") or {},
        "exception_resolution": exception_layer.get("latest_resolution_run") or {},
        "mandate": mandate.get("institutional_mandate_enforcement_layer_status") or {},
        "execution_charter": charter.get("institutional_allocation_execution_charter_layer_status") or {},
        "allocation_policy": policy_layer.get("executive_capital_allocation_policy_layer_status") or {},
    }


def _score_resolution(payload: dict, ctx: dict, policy: dict) -> dict:
    material_open = int(payload.get("open_material_remediations") or 0)
    critical_open = int(payload.get("open_critical_remediations") or 0)
    remediation_type = str(payload.get("remediation_type") or "CONTROL").upper()
    root_cause_verified = bool(payload.get("root_cause_verified", False))
    remediation_complete = bool(payload.get("remediation_complete", False))
    validation_complete = bool(payload.get("validation_complete", False))
    capital_impact_notional = float(payload.get("capital_impact_notional") or 0)
    requires_committee_reconfirmation = bool(payload.get("requires_committee_reconfirmation", False))
    evidence_complete = bool(payload.get("evidence_complete", False))

    score = 100.0
    blockers = []
    flags = []

    if critical_open > int(policy.get("max_open_critical_remediations", 0)):
        blockers.append("OPEN_CRITICAL_REMEDIATIONS_REMAIN")
        score -= 22
    if material_open > int(policy.get("max_open_material_remediations", 1)):
        flags.append("OPEN_MATERIAL_REMEDIATIONS_REMAIN")
        score -= 10
    if not root_cause_verified and bool(policy.get("require_verified_root_cause", True)):
        blockers.append("ROOT_CAUSE_NOT_CONFIRMED")
        score -= 16
    if not remediation_complete:
        blockers.append("REMEDIATION_NOT_COMPLETE")
        score -= 16
    if not validation_complete:
        blockers.append("VALIDATION_NOT_COMPLETE")
        score -= 12
    if not evidence_complete:
        flags.append("CLOSURE_EVIDENCE_NOT_COMPLETE")
        score -= 8
    if requires_committee_reconfirmation:
        flags.append("COMMITTEE_RECONFIRM_REQUIRED")
        score -= 7
    if remediation_type in {"MANDATE", "REGULATORY", "INVESTOR", "VALUATION"}:
        flags.append("HIGH_SENSITIVITY_REMEDIATION")
        score -= 6

    if bool(policy.get("require_exception_clearance_case", True)) and str(ctx["breach"].get("posture", "")).upper() not in {"CONTAINED", "ESCALATE", "CLEAR"}:
        blockers.append("BREACH_CONTEXT_NOT_ESTABLISHED")
        score -= 10
    if str(ctx["mandate"].get("posture", "")).upper() not in {"APPROVED", "ENFORCED", "CLEAR"}:
        blockers.append("MANDATE_NOT_CLEAR")
        score -= 10
    if str(ctx["execution_charter"].get("posture", "")).upper() not in {"APPROVED", "CHARTERED", "CLEAR"}:
        flags.append("EXECUTION_CHARTER_NOT_CLEAR")
        score -= 8
    if str(ctx["allocation_policy"].get("posture", "")).upper() not in {"APPROVED", "CLEAR", "ENFORCED"}:
        flags.append("ALLOCATION_POLICY_NOT_CLEAR")
        score -= 8
    if bool(policy.get("require_release_clear", True)) and not bool(ctx["release"].get("can_deploy", True)):
        blockers.append("RELEASE_NOT_CLEAR")
        score -= 8
    if bool(policy.get("require_safety_clear", True)) and str(ctx["safety"].get("posture", "")).upper() not in {"APPROVED", "READY", "CLEAR"}:
        blockers.append("SAFETY_NOT_CLEAR")
        score -= 10
    if bool(policy.get("require_recovery_clear", True)) and str(ctx["recovery"].get("posture", "")).upper() not in {"READY", "RECOVERED", "CLEAR"}:
        blockers.append("RECOVERY_NOT_CLEAR")
        score -= 10
    if bool(policy.get("require_operator_clear", True)) and not bool(ctx["operator"].get("can_resume", True)):
        blockers.append("OPERATOR_NOT_CLEAR")
        score -= 8

    operator_signoff_required = capital_impact_notional >= float(policy.get("operator_review_notional_threshold", 500000.0)) or requires_committee_reconfirmation
    if operator_signoff_required:
        flags.append("OPERATOR_REVIEW_REQUIRED")
        score -= 4

    score = max(score, 0.0)
    minimum = float(policy.get("minimum_closure_score", 92.0))
    if blockers:
        posture = "BLOCKED"
        band = "UNCLOSED"
    elif score >= minimum and not operator_signoff_required:
        posture = "CLOSED"
        band = "CLEARED"
    elif score >= max(minimum - 10.0, 75.0):
        posture = "OPERATOR_REVIEW"
        band = "SUPERVISED"
    else:
        posture = "WATCH"
        band = "PENDING"

    return {
        "closure_score": round(score, 2),
        "posture": posture,
        "closure_band": band,
        "blockers": blockers,
        "flags": flags,
        "operator_signoff_required": operator_signoff_required,
        "capital_impact_notional": round(capital_impact_notional, 2),
        "remediation_type": remediation_type,
        "open_material_remediations": material_open,
        "open_critical_remediations": critical_open,
    }


@router.get("/api/institutional-remediation-closure-layer/summary")
def summary(session=Depends(_require_user)):
    return _summary_for_email(session.get("email") or "demo@quantora.ai")


@router.post("/api/institutional-remediation-closure-layer/policy")
def policy(payload: dict = Body(default={}), session=Depends(_require_user)):
    email = session.get("email") or "demo@quantora.ai"
    s = _load(email)
    s["policy"] = {**dict(DEFAULT_POLICY), **(s.get("policy") or {}), **(payload or {})}
    _save(email, s)
    return {"ok": True, "policy": s["policy"]}


@router.post("/api/institutional-remediation-closure-layer/evaluate")
def evaluate(payload: dict = Body(default={}), session=Depends(_require_user)):
    email = session.get("email") or "demo@quantora.ai"
    s = _load(email)
    ctx = _cross_system_context(email)
    policy = s.get("policy") or dict(DEFAULT_POLICY)
    scored = _score_resolution(payload or {}, ctx, policy)
    ts = time.time_ns()
    run = {
        "resolution_run_id": f"exception-resolution-{ts}",
        "created_at": _now_iso(),
        "title": payload.get("title") or "resolve institutional exception",
        "summary": payload.get("summary") or "Evaluate exception clearance and operator supervision requirements.",
        **scored,
    }
    alert = {
        "created_at": run["created_at"],
        "severity": "critical" if run["posture"] == "BLOCKED" else "warning" if run["posture"] in {"WATCH", "OPERATOR_REVIEW"} else "info",
        "message": f"Institutional exception posture {run['posture']} ({run['closure_band']})",
        "resolution_run_id": run["resolution_run_id"],
    }
    retain = int(policy.get("retain_cycles", 180))
    _append(s, "closure_runs", run, retain)
    _append(s, "alerts", alert, retain)
    _append(s, "exception_book", {"created_at": run["created_at"], "run": run}, retain)
    s["latest_closure_run"] = run
    s["last_context"] = ctx
    _save(email, s)
    return {"ok": True, "resolution": run, "alert": alert, "context": ctx}


@router.post("/api/institutional-remediation-closure-layer/bootstrap-demo")
def bootstrap_demo(session=Depends(_require_user)):
    payload = {
        "title": "bootstrap institutional remediation closure",
        "summary": "Validate whether a mandate-sensitive exception can be cleared or requires supervised resolution.",
        "remediation_type": "MANDATE",
        "open_material_remediations": 1,
        "open_critical_remediations": 0,
        "root_cause_verified": True,
        "remediation_complete": True,
        "validation_complete": True,
        "evidence_complete": True,
        "capital_impact_notional": 420000.0,
        "requires_committee_reconfirmation": False,
    }
    return evaluate(payload=payload, session=session)
