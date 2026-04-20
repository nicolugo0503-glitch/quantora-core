from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(prefix="/api/regulatory-filing-submission-orchestration-layer", tags=["regulatory-filing-submission-orchestration-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "regulatory_filing_submission_orchestration_layer"
DEFAULT_POLICY = {
    "retain_cycles": 180,
    "minimum_score": 96.0,
    "require_regulator_ready": True,
    "require_compliance_automated": True,
    "require_multi_jurisdiction_clear": True,
    "require_supervisory_exam_ready": True,
    "minimum_submission_integrity_score": 0.99,
    "minimum_evidence_linkage_score": 0.985,
    "minimum_regulator_ack_readiness_score": 0.98,
    "max_pending_submissions": 2,
    "max_rejected_submissions": 0,
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


def _global_deployment():
    from backend.app import qnt30753_global_strategy_deployment_layer_router as global_deployment
    return global_deployment


def _supervisory_exam():
    from backend.app import qnt30754_institutional_supervisory_examination_command_layer_router as supervisory_exam
    return supervisory_exam


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
            "filing_queue": [],
            "submissions": [],
            "acknowledgements": [],
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
        "regulatory_filing_submission_orchestration_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "filing_queue_count": len(s.get("filing_queue") or []),
            "submission_count": len(s.get("submissions") or []),
            "acknowledgement_count": len(s.get("acknowledgements") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "filing_queue": s.get("filing_queue") or [],
        "submissions": s.get("submissions") or [],
        "acknowledgements": s.get("acknowledgements") or [],
    }


def _cross_system_context(email: str) -> dict:
    return {
        "captured_at": _now_iso(),
        "regulator_readiness": (_regulator_readiness()._summary_for_email(email).get("institutional_regulator_readiness_interface_status") or {}),
        "compliance_automation": (_compliance()._summary_for_email(email).get("regulatory_compliance_automation_layer_status") or {}),
        "multi_jurisdiction": (_multi_jurisdiction()._summary_for_email(email).get("multi_jurisdiction_governance_layer_status") or {}),
        "global_deployment": (_global_deployment()._summary_for_email(email).get("global_strategy_deployment_layer_status") or {}),
        "supervisory_exam": (_supervisory_exam()._summary_for_email(email).get("institutional_supervisory_examination_command_layer_status") or {}),
    }


def _band(score: float) -> str:
    if score >= 98.0:
        return "SUBMISSION_CLEAR"
    if score >= 96.0:
        return "CONTROLLED_RELEASE"
    if score >= 92.0:
        return "REVIEW_REQUIRED"
    return "BLOCKED"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _cross_system_context(email)
    submission_integrity_score = float(payload.get("submission_integrity_score", 0.0) or 0.0)
    evidence_linkage_score = float(payload.get("evidence_linkage_score", 0.0) or 0.0)
    regulator_ack_readiness_score = float(payload.get("regulator_ack_readiness_score", 0.0) or 0.0)
    pending_submissions = int(payload.get("pending_submissions", 0) or 0)
    rejected_submissions = int(payload.get("rejected_submissions", 0) or 0)
    release_window_open = bool(payload.get("release_window_open", False))

    score = 100.0
    reasons = []
    alerts = []
    for val, threshold, mult, reason, code in [
        (submission_integrity_score, float(policy.get("minimum_submission_integrity_score", 0.99)), 140.0, "submission integrity is below policy", "SUBMISSION_INTEGRITY_WEAK"),
        (evidence_linkage_score, float(policy.get("minimum_evidence_linkage_score", 0.985)), 120.0, "evidence linkage is below policy", "EVIDENCE_LINKAGE_WEAK"),
        (regulator_ack_readiness_score, float(policy.get("minimum_regulator_ack_readiness_score", 0.98)), 110.0, "regulator acknowledgement readiness is below policy", "ACK_READINESS_WEAK"),
    ]:
        if val < threshold:
            score -= round((threshold - val) * mult, 2)
            reasons.append(reason)
            alerts.append(code)
    if pending_submissions > int(policy.get("max_pending_submissions", 2)):
        score -= min((pending_submissions - int(policy.get("max_pending_submissions", 2))) * 5.0, 20.0)
        reasons.append("pending submissions exceed policy")
        alerts.append("PENDING_SUBMISSIONS_HIGH")
    if rejected_submissions > int(policy.get("max_rejected_submissions", 0)):
        score -= min(rejected_submissions * 15.0, 30.0)
        reasons.append("rejected submissions remain open")
        alerts.append("REJECTED_SUBMISSIONS_OPEN")
    if not release_window_open:
        score -= 5.0
        reasons.append("submission release window is not open")
        alerts.append("RELEASE_WINDOW_CLOSED")

    regulator_posture = str(ctx.get("regulator_readiness", {}).get("posture", "UNINITIALIZED"))
    compliance_posture = str(ctx.get("compliance_automation", {}).get("posture", "UNINITIALIZED"))
    governance_posture = str(ctx.get("multi_jurisdiction", {}).get("posture", "UNINITIALIZED"))
    deployment_posture = str(ctx.get("global_deployment", {}).get("posture", "UNINITIALIZED"))
    supervisory_posture = str(ctx.get("supervisory_exam", {}).get("posture", "UNINITIALIZED"))

    if policy.get("require_regulator_ready", True) and regulator_posture not in {"REGULATOR_READY", "UNINITIALIZED"}:
        score -= 10.0; reasons.append("regulator readiness posture is not submission clear"); alerts.append("REGULATOR_READINESS_NOT_CLEAR")
    if policy.get("require_compliance_automated", True) and compliance_posture not in {"AUTOMATED_CLEAR", "CONTROLLED_AUTOMATION", "UNINITIALIZED"}:
        score -= 10.0; reasons.append("compliance automation posture is not submission clear"); alerts.append("COMPLIANCE_AUTOMATION_NOT_CLEAR")
    if policy.get("require_multi_jurisdiction_clear", True) and governance_posture not in {"GLOBAL_GOVERNANCE_CLEAR", "CONTROLLED_EXPANSION", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("multi-jurisdiction governance posture is not submission clear"); alerts.append("MULTI_JURISDICTION_NOT_CLEAR")
    if deployment_posture not in {"GLOBAL_DEPLOYMENT_CLEAR", "CONTROLLED_DEPLOYMENT", "UNINITIALIZED"}:
        score -= 6.0; reasons.append("global deployment posture is not submission clear"); alerts.append("GLOBAL_DEPLOYMENT_NOT_CLEAR")
    if policy.get("require_supervisory_exam_ready", True) and supervisory_posture not in {"EXAM_READY", "WATCH", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("supervisory examination posture is not submission clear"); alerts.append("SUPERVISORY_EXAM_NOT_CLEAR")

    score = max(round(score, 2), 0.0)
    band = _band(score)
    posture = "SUBMISSION_CLEAR" if score >= float(policy.get("minimum_score", 96.0)) else ("WATCH" if score >= 92.0 else "BLOCKED")
    operator_review_required = posture != "SUBMISSION_CLEAR" or rejected_submissions > 0
    row = {
        "mission": "QNT30755",
        "evaluated_at": _now_iso(),
        "score": score,
        "band": band,
        "posture": posture,
        "operator_review_required": operator_review_required,
        "submission_integrity_score": submission_integrity_score,
        "evidence_linkage_score": evidence_linkage_score,
        "regulator_ack_readiness_score": regulator_ack_readiness_score,
        "pending_submissions": pending_submissions,
        "rejected_submissions": rejected_submissions,
        "release_window_open": release_window_open,
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


@router.post("/stage-filing")
def stage_filing(payload: dict = Body(default={}), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    row = {
        "at": _now_iso(),
        "filing_type": str(payload.get("filing_type") or "Form PF"),
        "jurisdiction": str(payload.get("jurisdiction") or "US"),
        "release_window": str(payload.get("release_window") or "current-cycle"),
        "status": str(payload.get("status") or "staged"),
    }
    _append(store, "filing_queue", row, (store.get("policy") or {}).get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "filing_queue_item": row, "summary": _summary_for_email(email)}


@router.post("/submit")
def submit(payload: dict = Body(default={}), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    row = {
        "at": _now_iso(),
        "filing_type": str(payload.get("filing_type") or "Form PF"),
        "jurisdiction": str(payload.get("jurisdiction") or "US"),
        "submission_reference": str(payload.get("submission_reference") or f"SUB-{_safe(email)[:8]}"),
        "status": str(payload.get("status") or "submitted"),
    }
    _append(store, "submissions", row, (store.get("policy") or {}).get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "submission": row, "summary": _summary_for_email(email)}


@router.post("/acknowledge")
def acknowledge(payload: dict = Body(default={}), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    row = {
        "at": _now_iso(),
        "regulator": str(payload.get("regulator") or "SEC"),
        "submission_reference": str(payload.get("submission_reference") or f"SUB-{_safe(email)[:8]}"),
        "status": str(payload.get("status") or "received"),
    }
    _append(store, "acknowledgements", row, (store.get("policy") or {}).get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "acknowledgement": row, "summary": _summary_for_email(email)}


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
    stage_filing({"filing_type": "Form PF", "jurisdiction": "US", "release_window": "quarter-end", "status": "staged"}, {"email": email})
    submit({"filing_type": "Form PF", "jurisdiction": "US", "submission_reference": f"SUB-{_safe(email)[:8]}", "status": "submitted"}, {"email": email})
    acknowledge({"regulator": "SEC", "submission_reference": f"SUB-{_safe(email)[:8]}", "status": "received"}, {"email": email})
    _evaluate(email, {
        "submission_integrity_score": 0.993,
        "evidence_linkage_score": 0.989,
        "regulator_ack_readiness_score": 0.988,
        "pending_submissions": 1,
        "rejected_submissions": 0,
        "release_window_open": True,
    })
    return {"ok": True, "summary": _summary_for_email(email)}
