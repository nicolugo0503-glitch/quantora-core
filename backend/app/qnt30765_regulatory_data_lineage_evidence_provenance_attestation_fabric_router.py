from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(prefix="/api/regulatory-data-lineage-evidence-provenance-attestation-fabric", tags=["regulatory-data-lineage-evidence-provenance-attestation-fabric"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "regulatory_data_lineage_evidence_provenance_attestation_fabric"
DEFAULT_POLICY = {
    "retain_cycles": 180,
    "minimum_score": 96.0,
    "require_filing_orchestration_clear": True,
    "require_enforcement_response_clear": True,
    "require_stress_testing_clear": True,
    "require_model_risk_clear": True,
    "minimum_lineage_coverage": 0.96,
    "minimum_provenance_integrity_score": 0.95,
    "minimum_attestation_completion_score": 0.94,
    "minimum_evidence_continuity_score": 0.95,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _filing_orchestration():
    from backend.app import qnt30755_regulatory_filing_submission_orchestration_layer_router as module
    return module


def _enforcement_response():
    from backend.app import qnt30758_regulatory_enforcement_response_consent_order_command_layer_router as module
    return module


def _stress_testing():
    from backend.app import qnt30763_regulatory_stress_testing_submission_supervisory_challenge_layer_router as module
    return module


def _model_risk():
    from backend.app import qnt30764_regulatory_model_risk_governance_validation_oversight_layer_router as module
    return module


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
            "lineage_assets": [],
            "provenance_checks": [],
            "attestations": [],
            "evidence_gap_closures": [],
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
        "regulatory_data_lineage_evidence_provenance_attestation_fabric_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "lineage_asset_count": len(s.get("lineage_assets") or []),
            "provenance_check_count": len(s.get("provenance_checks") or []),
            "attestation_count": len(s.get("attestations") or []),
            "evidence_gap_closure_count": len(s.get("evidence_gap_closures") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "lineage_assets": s.get("lineage_assets") or [],
        "provenance_checks": s.get("provenance_checks") or [],
        "attestations": s.get("attestations") or [],
        "evidence_gap_closures": s.get("evidence_gap_closures") or [],
    }


def _cross_system_context(email: str) -> dict:
    return {
        "captured_at": _now_iso(),
        "filing_orchestration": (_filing_orchestration()._summary_for_email(email).get("regulatory_filing_submission_orchestration_layer_status") or {}),
        "enforcement_response": (_enforcement_response()._summary_for_email(email).get("regulatory_enforcement_response_consent_order_command_layer_status") or {}),
        "stress_testing": (_stress_testing()._summary_for_email(email).get("regulatory_stress_testing_submission_supervisory_challenge_layer_status") or {}),
        "model_risk": (_model_risk()._summary_for_email(email).get("regulatory_model_risk_governance_validation_oversight_layer_status") or {}),
    }


def _band(score: float) -> str:
    if score >= 98.0:
        return "ATTESTATION_FABRIC_READY"
    if score >= 96.0:
        return "EVIDENCE_PROVENANCE_CLEAR"
    if score >= 92.0:
        return "HEIGHTENED_DATA_GOVERNANCE_WATCH"
    return "EVIDENCE_REMEDIATION_REQUIRED"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _cross_system_context(email)

    lineage_coverage = float(payload.get("lineage_coverage", 0.0) or 0.0)
    provenance_integrity_score = float(payload.get("provenance_integrity_score", 0.0) or 0.0)
    attestation_completion_score = float(payload.get("attestation_completion_score", 0.0) or 0.0)
    evidence_continuity_score = float(payload.get("evidence_continuity_score", 0.0) or 0.0)
    unresolved_evidence_gaps = int(payload.get("unresolved_evidence_gaps", 0) or 0)
    stale_critical_lineage_objects = int(payload.get("stale_critical_lineage_objects", 0) or 0)

    score = 100.0
    reasons = []
    alerts = []

    if lineage_coverage < float(policy.get("minimum_lineage_coverage", 0.96)):
        score -= round((float(policy.get("minimum_lineage_coverage", 0.96)) - lineage_coverage) * 100.0, 2)
        reasons.append("critical data lineage coverage is below institutional policy")
        alerts.append("LINEAGE_COVERAGE_WEAK")
    if provenance_integrity_score < float(policy.get("minimum_provenance_integrity_score", 0.95)):
        score -= round((float(policy.get("minimum_provenance_integrity_score", 0.95)) - provenance_integrity_score) * 100.0, 2)
        reasons.append("evidence provenance integrity is below institutional threshold")
        alerts.append("PROVENANCE_INTEGRITY_WEAK")
    if attestation_completion_score < float(policy.get("minimum_attestation_completion_score", 0.94)):
        score -= round((float(policy.get("minimum_attestation_completion_score", 0.94)) - attestation_completion_score) * 95.0, 2)
        reasons.append("attestation completion is below required control level")
        alerts.append("ATTESTATION_COMPLETION_WEAK")
    if evidence_continuity_score < float(policy.get("minimum_evidence_continuity_score", 0.95)):
        score -= round((float(policy.get("minimum_evidence_continuity_score", 0.95)) - evidence_continuity_score) * 95.0, 2)
        reasons.append("evidence continuity score is below institutional standard")
        alerts.append("EVIDENCE_CONTINUITY_WEAK")
    if unresolved_evidence_gaps > 0:
        score -= min(unresolved_evidence_gaps * 6.0, 24.0)
        reasons.append("unresolved evidence gaps remain open")
        alerts.append("UNRESOLVED_EVIDENCE_GAPS")
    if stale_critical_lineage_objects > 0:
        score -= min(stale_critical_lineage_objects * 4.0, 20.0)
        reasons.append("stale critical lineage objects require refresh")
        alerts.append("STALE_CRITICAL_LINEAGE_OBJECTS")

    filing_posture = str(ctx.get("filing_orchestration", {}).get("posture", "UNINITIALIZED"))
    enforcement_posture = str(ctx.get("enforcement_response", {}).get("posture", "UNINITIALIZED"))
    stress_posture = str(ctx.get("stress_testing", {}).get("posture", "UNINITIALIZED"))
    model_risk_posture = str(ctx.get("model_risk", {}).get("posture", "UNINITIALIZED"))

    if policy.get("require_filing_orchestration_clear", True) and filing_posture not in {"FILING_READY", "HEIGHTENED_FILING_WATCH", "UNINITIALIZED"}:
        score -= 9.0; reasons.append("filing orchestration posture is not evidence-clear"); alerts.append("FILING_ORCHESTRATION_NOT_CLEAR")
    if policy.get("require_enforcement_response_clear", True) and enforcement_posture not in {"ENFORCEMENT_RESPONSE_READY", "HEIGHTENED_ENFORCEMENT_WATCH", "UNINITIALIZED"}:
        score -= 9.0; reasons.append("enforcement response posture is not evidence-clear"); alerts.append("ENFORCEMENT_RESPONSE_NOT_CLEAR")
    if policy.get("require_stress_testing_clear", True) and stress_posture not in {"SUPERVISORY_CHALLENGE_READY", "HEIGHTENED_SUPERVISORY_WATCH", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("stress testing posture is not evidence-clear"); alerts.append("STRESS_TESTING_NOT_CLEAR")
    if policy.get("require_model_risk_clear", True) and model_risk_posture not in {"MODEL_RISK_GOVERNANCE_CLEAR", "HEIGHTENED_MODEL_RISK_WATCH", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("model risk posture is not provenance-clear"); alerts.append("MODEL_RISK_NOT_CLEAR")

    score = max(round(score, 2), 0.0)
    band = _band(score)
    posture = "EVIDENCE_PROVENANCE_CLEAR" if score >= float(policy.get("minimum_score", 96.0)) else ("HEIGHTENED_DATA_GOVERNANCE_WATCH" if score >= 92.0 else "EVIDENCE_REMEDIATION_REQUIRED")
    operator_review_required = posture != "EVIDENCE_PROVENANCE_CLEAR" or unresolved_evidence_gaps > 0 or stale_critical_lineage_objects > 0
    row = {
        "mission": "QNT30765",
        "evaluated_at": _now_iso(),
        "score": score,
        "band": band,
        "posture": posture,
        "operator_review_required": operator_review_required,
        "lineage_coverage": lineage_coverage,
        "provenance_integrity_score": provenance_integrity_score,
        "attestation_completion_score": attestation_completion_score,
        "evidence_continuity_score": evidence_continuity_score,
        "unresolved_evidence_gaps": unresolved_evidence_gaps,
        "stale_critical_lineage_objects": stale_critical_lineage_objects,
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


@router.post("/register-lineage-asset")
def register_lineage_asset(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "registered_at": _now_iso(),
        "asset_code": payload.get("asset_code", "REG_CAPITAL_STRESS_SUBMISSION_DATASET"),
        "criticality": payload.get("criticality", "CRITICAL"),
        "owner": payload.get("owner", "data-governance-office"),
        "status": payload.get("status", "ACTIVE"),
    }
    _append(store, "lineage_assets", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "lineage_asset": row, "summary": _summary_for_email(email)}


@router.post("/record-provenance-check")
def record_provenance_check(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "recorded_at": _now_iso(),
        "check_code": payload.get("check_code", "PROV_2026_Q4_STRESS_AND_FILINGS"),
        "scope": payload.get("scope", "END_TO_END_TRACE"),
        "owner": payload.get("owner", "evidence-provenance-office"),
        "status": payload.get("status", "OPEN"),
    }
    _append(store, "provenance_checks", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "provenance_check": row, "summary": _summary_for_email(email)}


@router.post("/issue-attestation")
def issue_attestation(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "issued_at": _now_iso(),
        "attestation_code": payload.get("attestation_code", "ATTEST_2026_Q4_REGULATORY_EVIDENCE_FABRIC"),
        "attestor": payload.get("attestor", "chief-data-officer"),
        "scope": payload.get("scope", "REGULATORY_EVIDENCE_AND_LINEAGE"),
        "status": payload.get("status", "ISSUED"),
    }
    _append(store, "attestations", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "attestation": row, "summary": _summary_for_email(email)}


@router.post("/close-evidence-gap")
def close_evidence_gap(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "closed_at": _now_iso(),
        "gap_code": payload.get("gap_code", "EVIDENCE_GAP_TRACE_BREAK_01"),
        "closure_evidence": payload.get("closure_evidence", "LINEAGE_REFRESH_AND_ATTESTATION_ACCEPTED"),
        "status": payload.get("status", "CLOSED"),
    }
    _append(store, "evidence_gap_closures", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "evidence_gap_closure": row, "summary": _summary_for_email(email)}


@router.get("/policy")
def policy(user=Depends(_require_user)):
    return {"ok": True, "policy": _load(user["email"]).get("policy") or dict(DEFAULT_POLICY)}


@router.post("/bootstrap-demo")
def bootstrap_demo(user=Depends(_require_user)):
    email = user["email"]
    register_lineage_asset({
        "asset_code": "GLOBAL_REGULATORY_SUBMISSION_EVIDENCE_GRAPH",
        "criticality": "CRITICAL",
        "owner": "data-governance-office",
        "status": "ACTIVE",
    }, user)
    record_provenance_check({
        "check_code": "PROV_2026_Q4_GLOBAL_REGULATORY_STACK",
        "scope": "END_TO_END_TRACE",
        "owner": "evidence-provenance-office",
        "status": "OPEN",
    }, user)
    issue_attestation({
        "attestation_code": "ATTEST_2026_Q4_GLOBAL_REGULATORY_EVIDENCE_FABRIC",
        "attestor": "chief-data-officer",
        "scope": "REGULATORY_EVIDENCE_AND_LINEAGE",
        "status": "ISSUED",
    }, user)
    close_evidence_gap({
        "gap_code": "TRACE_BREAK_GLOBAL_CAPITAL_SUBMISSION_01",
        "closure_evidence": "LINEAGE_REFRESH_PROVENANCE_PACKET_AND_ATTESTATION_ACCEPTED",
        "status": "CLOSED",
    }, user)
    run = _evaluate(email, {
        "lineage_coverage": 0.98,
        "provenance_integrity_score": 0.97,
        "attestation_completion_score": 0.96,
        "evidence_continuity_score": 0.97,
        "unresolved_evidence_gaps": 0,
        "stale_critical_lineage_objects": 0,
    })
    return {"ok": True, "run": run, "summary": _summary_for_email(email)}
