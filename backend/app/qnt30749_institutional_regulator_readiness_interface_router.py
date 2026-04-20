from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(prefix="/api/institutional-regulator-readiness-interface", tags=["institutional-regulator-readiness-interface"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "institutional_regulator_readiness_interface"
DEFAULT_POLICY = {
    "retain_cycles": 180,
    "minimum_score": 96.0,
    "require_audit_ready": True,
    "require_external_auditor_ready": True,
    "require_treasury_confirmed": True,
    "require_investor_confirmed": True,
    "minimum_framework_coverage_score": 0.985,
    "minimum_control_mapping_score": 0.985,
    "minimum_evidence_traceability_score": 0.98,
    "max_open_findings": 2,
    "max_regulatory_breaches": 0,
}

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu
def _audit_ready():
    from backend.app import qnt30747_institutional_audit_readiness_certification_layer_router as audit_ready
    return audit_ready
def _auditor_interface():
    from backend.app import qnt30748_institutional_external_auditor_interface_layer_router as auditor_interface
    return auditor_interface
def _treasury():
    from backend.app import qnt30745_institutional_treasury_confirmation_layer_router as treasury
    return treasury
def _investor():
    from backend.app import qnt30746_institutional_investor_capital_confirmation_layer_router as investor
    return investor
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
            "framework_mappings": [],
            "regulator_packets": [],
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
        "institutional_regulator_readiness_interface_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "framework_mapping_count": len(s.get("framework_mappings") or []),
            "regulator_packet_count": len(s.get("regulator_packets") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "framework_mappings": s.get("framework_mappings") or [],
        "regulator_packets": s.get("regulator_packets") or [],
    }

def _cross_system_context(email: str) -> dict:
    return {
        "captured_at": _now_iso(),
        "audit_readiness": (_audit_ready()._summary_for_email(email).get("institutional_audit_readiness_certification_layer_status") or {}),
        "external_auditor_interface": (_auditor_interface()._summary_for_email(email).get("institutional_external_auditor_interface_layer_status") or {}),
        "treasury": (_treasury()._summary_for_email(email).get("institutional_treasury_confirmation_layer_status") or {}),
        "investor": (_investor()._summary_for_email(email).get("institutional_investor_capital_confirmation_layer_status") or {}),
        "reporting": (_reporting()._summary_for_email(email).get("reporting_disclosure_automation_layer_status") or {}),
    }

def _band(score: float) -> str:
    if score >= 98.0:
        return "REGULATOR_READY"
    if score >= 96.0:
        return "CONTROLLED_SUBMISSION"
    if score >= 92.0:
        return "REMEDIATION_OPEN"
    return "BLOCKED"

def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _cross_system_context(email)
    framework_coverage_score = float(payload.get("framework_coverage_score", 0.0) or 0.0)
    control_mapping_score = float(payload.get("control_mapping_score", 0.0) or 0.0)
    evidence_traceability_score = float(payload.get("evidence_traceability_score", 0.0) or 0.0)
    open_findings = int(payload.get("open_findings", 0) or 0)
    regulatory_breaches = int(payload.get("regulatory_breaches", 0) or 0)
    filing_packet_complete = bool(payload.get("filing_packet_complete", False))

    score = 100.0
    reasons = []
    alerts = []
    for val, threshold, mult, reason, code in [
        (framework_coverage_score, float(policy.get("minimum_framework_coverage_score", 0.985)), 130.0, "regulatory framework coverage is below policy", "FRAMEWORK_COVERAGE_WEAK"),
        (control_mapping_score, float(policy.get("minimum_control_mapping_score", 0.985)), 120.0, "control mapping is below policy", "CONTROL_MAPPING_WEAK"),
        (evidence_traceability_score, float(policy.get("minimum_evidence_traceability_score", 0.98)), 110.0, "evidence traceability is below policy", "EVIDENCE_TRACEABILITY_WEAK"),
    ]:
        if val < threshold:
            score -= round((threshold - val) * mult, 2)
            reasons.append(reason)
            alerts.append(code)
    if open_findings > int(policy.get("max_open_findings", 2)):
        score -= min((open_findings - int(policy.get("max_open_findings", 2))) * 5.0, 20.0)
        reasons.append("open regulatory findings exceed policy")
        alerts.append("OPEN_FINDINGS_HIGH")
    if regulatory_breaches > int(policy.get("max_regulatory_breaches", 0)):
        score -= min(regulatory_breaches * 20.0, 40.0)
        reasons.append("regulatory breaches remain unresolved")
        alerts.append("REGULATORY_BREACH_OPEN")
    if not filing_packet_complete:
        score -= 6.0
        reasons.append("regulator filing packet is incomplete")
        alerts.append("FILING_PACKET_INCOMPLETE")

    audit_posture = str(ctx.get("audit_readiness", {}).get("posture", "UNINITIALIZED"))
    auditor_posture = str(ctx.get("external_auditor_interface", {}).get("posture", "UNINITIALIZED"))
    treasury_posture = str(ctx.get("treasury", {}).get("posture", "UNINITIALIZED"))
    investor_posture = str(ctx.get("investor", {}).get("posture", "UNINITIALIZED"))
    reporting_posture = str(ctx.get("reporting", {}).get("posture", "UNINITIALIZED"))
    if policy.get("require_audit_ready", True) and audit_posture not in {"AUDIT_READY", "UNINITIALIZED"}:
        score -= 12.0; reasons.append("audit readiness posture is not regulator clear"); alerts.append("AUDIT_NOT_REGULATOR_CLEAR")
    if policy.get("require_external_auditor_ready", True) and auditor_posture not in {"EXTERNAL_AUDITOR_READY", "UNINITIALIZED"}:
        score -= 10.0; reasons.append("external auditor interface posture is not regulator clear"); alerts.append("AUDITOR_INTERFACE_NOT_CLEAR")
    if policy.get("require_treasury_confirmed", True) and treasury_posture not in {"CONFIRMED", "TREASURY_CONFIRMED", "TREASURY_CONTROLLED", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("treasury posture is not regulator clear"); alerts.append("TREASURY_NOT_CLEAR")
    if policy.get("require_investor_confirmed", True) and investor_posture not in {"CONFIRMED", "FULLY_CONFIRMED", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("investor confirmation posture is not regulator clear"); alerts.append("INVESTOR_NOT_CLEAR")
    if reporting_posture not in {"AUTOMATED_CLEAR", "CONTROLLED", "APPROVED", "UNINITIALIZED"}:
        score -= 6.0; reasons.append("reporting posture is not regulator clear"); alerts.append("REPORTING_NOT_CLEAR")

    score = max(round(score, 2), 0.0)
    band = _band(score)
    posture = "REGULATOR_READY" if score >= float(policy.get("minimum_score", 96.0)) else ("WATCH" if score >= 92.0 else "BLOCKED")
    operator_review_required = posture != "REGULATOR_READY" or regulatory_breaches > 0
    row = {
        "mission": "QNT30749",
        "evaluated_at": _now_iso(),
        "score": score,
        "band": band,
        "posture": posture,
        "operator_review_required": operator_review_required,
        "framework_coverage_score": framework_coverage_score,
        "control_mapping_score": control_mapping_score,
        "evidence_traceability_score": evidence_traceability_score,
        "open_findings": open_findings,
        "regulatory_breaches": regulatory_breaches,
        "filing_packet_complete": filing_packet_complete,
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

@router.post("/map-framework")
def map_framework(payload: dict = Body(default={}), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    row = {
        "at": _now_iso(),
        "framework": str(payload.get("framework") or "SEC"),
        "jurisdiction": str(payload.get("jurisdiction") or "US"),
        "control_count": int(payload.get("control_count", 0) or 0),
        "status": str(payload.get("status") or "mapped"),
    }
    _append(store, "framework_mappings", row, (store.get("policy") or {}).get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "framework_mapping": row, "summary": _summary_for_email(email)}

@router.post("/publish-packet")
def publish_packet(payload: dict = Body(default={}), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    row = {
        "at": _now_iso(),
        "framework": str(payload.get("framework") or "SEC"),
        "packet_id": str(payload.get("packet_id") or f"RRI-{_safe(email)[:8]}"),
        "submission_mode": str(payload.get("submission_mode") or "ready"),
        "status": str(payload.get("status") or "published"),
    }
    _append(store, "regulator_packets", row, (store.get("policy") or {}).get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "regulator_packet": row, "summary": _summary_for_email(email)}

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
    map_framework({"framework": "SEC", "jurisdiction": "US", "control_count": 184, "status": "mapped"}, {"email": email})
    publish_packet({"framework": "SEC", "packet_id": f"RRI-{_safe(email)[:8]}", "submission_mode": "regulator-ready", "status": "published"}, {"email": email})
    _evaluate(email, {
        "framework_coverage_score": 0.992,
        "control_mapping_score": 0.991,
        "evidence_traceability_score": 0.989,
        "open_findings": 1,
        "regulatory_breaches": 0,
        "filing_packet_complete": True,
    })
    return {"ok": True, "summary": _summary_for_email(email)}
