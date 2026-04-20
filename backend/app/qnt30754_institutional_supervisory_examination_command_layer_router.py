from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(prefix="/api/institutional-supervisory-examination-command-layer", tags=["institutional-supervisory-examination-command-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "institutional_supervisory_examination_command_layer"
DEFAULT_POLICY = {
    "retain_cycles": 180,
    "minimum_score": 96.0,
    "require_regulator_ready": True,
    "require_compliance_automated": True,
    "require_multi_jurisdiction_clear": True,
    "require_global_deployment_controlled": True,
    "minimum_exam_pack_completeness_score": 0.985,
    "minimum_evidence_response_speed_score": 0.98,
    "minimum_supervisory_traceability_score": 0.98,
    "max_open_exam_requests": 2,
    "max_critical_exam_findings": 0,
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


def _capital_expansion():
    from backend.app import qnt30752_institutional_capital_expansion_engine_router as capital_expansion
    return capital_expansion


def _global_deployment():
    from backend.app import qnt30753_global_strategy_deployment_layer_router as global_deployment
    return global_deployment


def _audit_ready():
    from backend.app import qnt30747_institutional_audit_readiness_certification_layer_router as audit_ready
    return audit_ready


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
            "exam_cycles": [],
            "evidence_requests": [],
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
        "institutional_supervisory_examination_command_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "exam_cycle_count": len(s.get("exam_cycles") or []),
            "evidence_request_count": len(s.get("evidence_requests") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "exam_cycles": s.get("exam_cycles") or [],
        "evidence_requests": s.get("evidence_requests") or [],
    }


def _cross_system_context(email: str) -> dict:
    return {
        "captured_at": _now_iso(),
        "regulator_readiness": (_regulator_readiness()._summary_for_email(email).get("institutional_regulator_readiness_interface_status") or {}),
        "compliance_automation": (_compliance()._summary_for_email(email).get("regulatory_compliance_automation_layer_status") or {}),
        "multi_jurisdiction": (_multi_jurisdiction()._summary_for_email(email).get("multi_jurisdiction_governance_layer_status") or {}),
        "capital_expansion": (_capital_expansion()._summary_for_email(email).get("institutional_capital_expansion_engine_status") or {}),
        "global_deployment": (_global_deployment()._summary_for_email(email).get("global_strategy_deployment_layer_status") or {}),
        "audit_readiness": (_audit_ready()._summary_for_email(email).get("institutional_audit_readiness_certification_layer_status") or {}),
    }


def _band(score: float) -> str:
    if score >= 98.0:
        return "EXAM_READY"
    if score >= 96.0:
        return "CONTROLLED_RESPONSE"
    if score >= 92.0:
        return "SUPERVISORY_WATCH"
    return "BLOCKED"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _cross_system_context(email)
    exam_pack_completeness_score = float(payload.get("exam_pack_completeness_score", 0.0) or 0.0)
    evidence_response_speed_score = float(payload.get("evidence_response_speed_score", 0.0) or 0.0)
    supervisory_traceability_score = float(payload.get("supervisory_traceability_score", 0.0) or 0.0)
    open_exam_requests = int(payload.get("open_exam_requests", 0) or 0)
    critical_exam_findings = int(payload.get("critical_exam_findings", 0) or 0)
    regulator_war_room_enabled = bool(payload.get("regulator_war_room_enabled", False))

    score = 100.0
    reasons = []
    alerts = []
    for val, threshold, mult, reason, code in [
        (exam_pack_completeness_score, float(policy.get("minimum_exam_pack_completeness_score", 0.985)), 130.0, "exam pack completeness is below policy", "EXAM_PACK_WEAK"),
        (evidence_response_speed_score, float(policy.get("minimum_evidence_response_speed_score", 0.98)), 110.0, "evidence response speed is below policy", "RESPONSE_SPEED_WEAK"),
        (supervisory_traceability_score, float(policy.get("minimum_supervisory_traceability_score", 0.98)), 110.0, "supervisory traceability is below policy", "TRACEABILITY_WEAK"),
    ]:
        if val < threshold:
            score -= round((threshold - val) * mult, 2)
            reasons.append(reason)
            alerts.append(code)
    if open_exam_requests > int(policy.get("max_open_exam_requests", 2)):
        score -= min((open_exam_requests - int(policy.get("max_open_exam_requests", 2))) * 5.0, 20.0)
        reasons.append("open supervisory requests exceed policy")
        alerts.append("OPEN_SUPERVISORY_REQUESTS_HIGH")
    if critical_exam_findings > int(policy.get("max_critical_exam_findings", 0)):
        score -= min(critical_exam_findings * 20.0, 40.0)
        reasons.append("critical examination findings remain unresolved")
        alerts.append("CRITICAL_EXAM_FINDINGS_OPEN")
    if not regulator_war_room_enabled:
        score -= 5.0
        reasons.append("regulator war room is not enabled")
        alerts.append("WAR_ROOM_DISABLED")

    regulator_posture = str(ctx.get("regulator_readiness", {}).get("posture", "UNINITIALIZED"))
    compliance_posture = str(ctx.get("compliance_automation", {}).get("posture", "UNINITIALIZED"))
    governance_posture = str(ctx.get("multi_jurisdiction", {}).get("posture", "UNINITIALIZED"))
    capital_posture = str(ctx.get("capital_expansion", {}).get("posture", "UNINITIALIZED"))
    deployment_posture = str(ctx.get("global_deployment", {}).get("posture", "UNINITIALIZED"))
    audit_posture = str(ctx.get("audit_readiness", {}).get("posture", "UNINITIALIZED"))

    if policy.get("require_regulator_ready", True) and regulator_posture not in {"REGULATOR_READY", "UNINITIALIZED"}:
        score -= 10.0; reasons.append("regulator readiness posture is not clear"); alerts.append("REGULATOR_READINESS_NOT_CLEAR")
    if policy.get("require_compliance_automated", True) and compliance_posture not in {"AUTOMATED_CLEAR", "CONTROLLED_AUTOMATION", "UNINITIALIZED"}:
        score -= 10.0; reasons.append("compliance automation posture is not clear"); alerts.append("COMPLIANCE_AUTOMATION_NOT_CLEAR")
    if policy.get("require_multi_jurisdiction_clear", True) and governance_posture not in {"GLOBAL_GOVERNANCE_CLEAR", "CONTROLLED_EXPANSION", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("multi-jurisdiction governance posture is not clear"); alerts.append("MULTI_JURISDICTION_NOT_CLEAR")
    if policy.get("require_global_deployment_controlled", True) and deployment_posture not in {"GLOBAL_DEPLOYMENT_CLEAR", "CONTROLLED_DEPLOYMENT", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("global deployment posture is not supervisory clear"); alerts.append("GLOBAL_DEPLOYMENT_NOT_CLEAR")
    if capital_posture not in {"ALLOCATOR_SCALE_READY", "CONTROLLED_EXPANSION", "UNINITIALIZED"}:
        score -= 6.0; reasons.append("capital expansion posture is not supervisory clear"); alerts.append("CAPITAL_EXPANSION_NOT_CLEAR")
    if audit_posture not in {"AUDIT_READY", "MINOR_GAPS", "UNINITIALIZED"}:
        score -= 6.0; reasons.append("audit readiness posture is not supervisory clear"); alerts.append("AUDIT_NOT_CLEAR")

    score = max(round(score, 2), 0.0)
    band = _band(score)
    posture = "EXAM_READY" if score >= float(policy.get("minimum_score", 96.0)) else ("WATCH" if score >= 92.0 else "BLOCKED")
    operator_review_required = posture != "EXAM_READY" or critical_exam_findings > 0
    row = {
        "mission": "QNT30754",
        "evaluated_at": _now_iso(),
        "score": score,
        "band": band,
        "posture": posture,
        "operator_review_required": operator_review_required,
        "exam_pack_completeness_score": exam_pack_completeness_score,
        "evidence_response_speed_score": evidence_response_speed_score,
        "supervisory_traceability_score": supervisory_traceability_score,
        "open_exam_requests": open_exam_requests,
        "critical_exam_findings": critical_exam_findings,
        "regulator_war_room_enabled": regulator_war_room_enabled,
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


@router.post("/open-exam")
def open_exam(payload: dict = Body(default={}), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    row = {
        "at": _now_iso(),
        "exam_name": str(payload.get("exam_name") or "SEC routine examination"),
        "jurisdiction": str(payload.get("jurisdiction") or "US"),
        "status": str(payload.get("status") or "open"),
    }
    _append(store, "exam_cycles", row, (store.get("policy") or {}).get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "exam_cycle": row, "summary": _summary_for_email(email)}


@router.post("/request-evidence")
def request_evidence(payload: dict = Body(default={}), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    row = {
        "at": _now_iso(),
        "request_name": str(payload.get("request_name") or "trade blotter and evidence pack"),
        "owner": str(payload.get("owner") or "compliance-ops"),
        "status": str(payload.get("status") or "queued"),
    }
    _append(store, "evidence_requests", row, (store.get("policy") or {}).get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "evidence_request": row, "summary": _summary_for_email(email)}


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
    open_exam({"exam_name": "SEC routine examination", "jurisdiction": "US", "status": "open"}, {"email": email})
    request_evidence({"request_name": "order lifecycle evidence pack", "owner": "audit-ops", "status": "queued"}, {"email": email})
    _evaluate(email, {
        "exam_pack_completeness_score": 0.992,
        "evidence_response_speed_score": 0.988,
        "supervisory_traceability_score": 0.989,
        "open_exam_requests": 1,
        "critical_exam_findings": 0,
        "regulator_war_room_enabled": True,
    })
    return {"ok": True, "summary": _summary_for_email(email)}
