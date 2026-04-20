from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(prefix="/api/regulatory-records-retention-legal-hold-supervisory-retrieval-command-layer", tags=["regulatory-records-retention-legal-hold-supervisory-retrieval-command-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "regulatory_records_retention_legal_hold_supervisory_retrieval_command_layer"
DEFAULT_POLICY = {
    "retain_cycles": 180,
    "minimum_score": 96.0,
    "require_filing_orchestration_clear": True,
    "require_enforcement_response_clear": True,
    "require_stress_testing_clear": True,
    "require_provenance_clear": True,
    "minimum_retention_coverage": 0.97,
    "minimum_hold_integrity_score": 0.96,
    "minimum_supervisory_retrieval_readiness": 0.95,
    "minimum_record_index_integrity": 0.96,
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


def _provenance_fabric():
    from backend.app import qnt30765_regulatory_data_lineage_evidence_provenance_attestation_fabric_router as module
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
            "record_classes": [],
            "legal_holds": [],
            "supervisory_retrieval_packets": [],
            "hold_releases": [],
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
        "regulatory_records_retention_legal_hold_supervisory_retrieval_command_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "record_class_count": len(s.get("record_classes") or []),
            "legal_hold_count": len(s.get("legal_holds") or []),
            "supervisory_retrieval_packet_count": len(s.get("supervisory_retrieval_packets") or []),
            "hold_release_count": len(s.get("hold_releases") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "record_classes": s.get("record_classes") or [],
        "legal_holds": s.get("legal_holds") or [],
        "supervisory_retrieval_packets": s.get("supervisory_retrieval_packets") or [],
        "hold_releases": s.get("hold_releases") or [],
    }


def _cross_system_context(email: str) -> dict:
    return {
        "captured_at": _now_iso(),
        "filing_orchestration": (_filing_orchestration()._summary_for_email(email).get("regulatory_filing_submission_orchestration_layer_status") or {}),
        "enforcement_response": (_enforcement_response()._summary_for_email(email).get("regulatory_enforcement_response_consent_order_command_layer_status") or {}),
        "stress_testing": (_stress_testing()._summary_for_email(email).get("regulatory_stress_testing_submission_supervisory_challenge_layer_status") or {}),
        "provenance_fabric": (_provenance_fabric()._summary_for_email(email).get("regulatory_data_lineage_evidence_provenance_attestation_fabric_status") or {}),
    }


def _band(score: float) -> str:
    if score >= 98.0:
        return "SUPERVISORY_RETRIEVAL_COMMAND_READY"
    if score >= 96.0:
        return "RECORDS_AND_HOLD_CONTROL_CLEAR"
    if score >= 92.0:
        return "HEIGHTENED_RECORDS_WATCH"
    return "RECORDS_REMEDIATION_REQUIRED"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _cross_system_context(email)

    retention_coverage = float(payload.get("retention_coverage", 0.0) or 0.0)
    hold_integrity_score = float(payload.get("hold_integrity_score", 0.0) or 0.0)
    supervisory_retrieval_readiness = float(payload.get("supervisory_retrieval_readiness", 0.0) or 0.0)
    record_index_integrity = float(payload.get("record_index_integrity", 0.0) or 0.0)
    open_legal_hold_exceptions = int(payload.get("open_legal_hold_exceptions", 0) or 0)
    overdue_supervisory_requests = int(payload.get("overdue_supervisory_requests", 0) or 0)

    score = 100.0
    reasons = []
    alerts = []

    if retention_coverage < float(policy.get("minimum_retention_coverage", 0.97)):
        score -= round((float(policy.get("minimum_retention_coverage", 0.97)) - retention_coverage) * 100.0, 2)
        reasons.append("records retention coverage is below institutional policy")
        alerts.append("RETENTION_COVERAGE_WEAK")
    if hold_integrity_score < float(policy.get("minimum_hold_integrity_score", 0.96)):
        score -= round((float(policy.get("minimum_hold_integrity_score", 0.96)) - hold_integrity_score) * 100.0, 2)
        reasons.append("legal hold integrity is below required preservation threshold")
        alerts.append("LEGAL_HOLD_INTEGRITY_WEAK")
    if supervisory_retrieval_readiness < float(policy.get("minimum_supervisory_retrieval_readiness", 0.95)):
        score -= round((float(policy.get("minimum_supervisory_retrieval_readiness", 0.95)) - supervisory_retrieval_readiness) * 95.0, 2)
        reasons.append("supervisory retrieval readiness is below command standard")
        alerts.append("SUPERVISORY_RETRIEVAL_READINESS_WEAK")
    if record_index_integrity < float(policy.get("minimum_record_index_integrity", 0.96)):
        score -= round((float(policy.get("minimum_record_index_integrity", 0.96)) - record_index_integrity) * 95.0, 2)
        reasons.append("record index integrity is below institutional control level")
        alerts.append("RECORD_INDEX_INTEGRITY_WEAK")
    if open_legal_hold_exceptions > 0:
        score -= min(open_legal_hold_exceptions * 6.0, 24.0)
        reasons.append("open legal hold exceptions remain unresolved")
        alerts.append("OPEN_LEGAL_HOLD_EXCEPTIONS")
    if overdue_supervisory_requests > 0:
        score -= min(overdue_supervisory_requests * 5.0, 20.0)
        reasons.append("overdue supervisory retrieval requests remain open")
        alerts.append("OVERDUE_SUPERVISORY_REQUESTS")

    filing_posture = str(ctx.get("filing_orchestration", {}).get("posture", "UNINITIALIZED"))
    enforcement_posture = str(ctx.get("enforcement_response", {}).get("posture", "UNINITIALIZED"))
    stress_posture = str(ctx.get("stress_testing", {}).get("posture", "UNINITIALIZED"))
    provenance_posture = str(ctx.get("provenance_fabric", {}).get("posture", "UNINITIALIZED"))

    if policy.get("require_filing_orchestration_clear", True) and filing_posture not in {"FILING_READY", "HEIGHTENED_FILING_WATCH", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("filing orchestration posture is not retention-clear"); alerts.append("FILING_ORCHESTRATION_NOT_CLEAR")
    if policy.get("require_enforcement_response_clear", True) and enforcement_posture not in {"ENFORCEMENT_RESPONSE_READY", "HEIGHTENED_ENFORCEMENT_WATCH", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("enforcement response posture is not records-clear"); alerts.append("ENFORCEMENT_RESPONSE_NOT_CLEAR")
    if policy.get("require_stress_testing_clear", True) and stress_posture not in {"SUPERVISORY_CHALLENGE_READY", "HEIGHTENED_SUPERVISORY_WATCH", "UNINITIALIZED"}:
        score -= 7.0; reasons.append("stress testing posture is not retrieval-clear"); alerts.append("STRESS_TESTING_NOT_CLEAR")
    if policy.get("require_provenance_clear", True) and provenance_posture not in {"EVIDENCE_PROVENANCE_CLEAR", "HEIGHTENED_DATA_GOVERNANCE_WATCH", "UNINITIALIZED"}:
        score -= 9.0; reasons.append("evidence provenance posture is not records-clear"); alerts.append("PROVENANCE_FABRIC_NOT_CLEAR")

    score = max(round(score, 2), 0.0)
    band = _band(score)
    posture = "RECORDS_AND_HOLD_CONTROL_CLEAR" if score >= float(policy.get("minimum_score", 96.0)) else ("HEIGHTENED_RECORDS_WATCH" if score >= 92.0 else "RECORDS_REMEDIATION_REQUIRED")
    operator_review_required = posture != "RECORDS_AND_HOLD_CONTROL_CLEAR" or open_legal_hold_exceptions > 0 or overdue_supervisory_requests > 0
    row = {
        "mission": "QNT30766",
        "evaluated_at": _now_iso(),
        "score": score,
        "band": band,
        "posture": posture,
        "operator_review_required": operator_review_required,
        "retention_coverage": retention_coverage,
        "hold_integrity_score": hold_integrity_score,
        "supervisory_retrieval_readiness": supervisory_retrieval_readiness,
        "record_index_integrity": record_index_integrity,
        "open_legal_hold_exceptions": open_legal_hold_exceptions,
        "overdue_supervisory_requests": overdue_supervisory_requests,
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


@router.post("/register-record-class")
def register_record_class(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "registered_at": _now_iso(),
        "record_class": payload.get("record_class", "REGULATORY_SUPERVISORY_EVIDENCE_PACKET"),
        "retention_period": payload.get("retention_period", "7Y"),
        "custodian": payload.get("custodian", "records-governance-office"),
        "status": payload.get("status", "ACTIVE"),
    }
    _append(store, "record_classes", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "record_class": row, "summary": _summary_for_email(email)}


@router.post("/place-legal-hold")
def place_legal_hold(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "placed_at": _now_iso(),
        "hold_code": payload.get("hold_code", "LH_2026_Q4_SUPERVISORY_REVIEW"),
        "scope": payload.get("scope", "REGULATORY_RECORDS_AND_COMMUNICATIONS"),
        "owner": payload.get("owner", "general-counsel-office"),
        "status": payload.get("status", "ACTIVE"),
    }
    _append(store, "legal_holds", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "legal_hold": row, "summary": _summary_for_email(email)}


@router.post("/retrieve-supervisory-packet")
def retrieve_supervisory_packet(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "retrieved_at": _now_iso(),
        "request_code": payload.get("request_code", "SUP_REQ_2026_Q4_RECORDS_PACKET"),
        "requesting_authority": payload.get("requesting_authority", "primary-supervisor"),
        "packet_scope": payload.get("packet_scope", "ENFORCEMENT_FILINGS_STRESS_TEST_EVIDENCE"),
        "status": payload.get("status", "DELIVERED"),
    }
    _append(store, "supervisory_retrieval_packets", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "supervisory_retrieval_packet": row, "summary": _summary_for_email(email)}


@router.post("/release-hold")
def release_hold(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "released_at": _now_iso(),
        "hold_code": payload.get("hold_code", "LH_2026_Q4_SUPERVISORY_REVIEW"),
        "release_basis": payload.get("release_basis", "REGULATORY_CLEARANCE_AND_COUNSEL_APPROVAL"),
        "status": payload.get("status", "RELEASED"),
    }
    _append(store, "hold_releases", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "hold_release": row, "summary": _summary_for_email(email)}


@router.get("/policy")
def policy(user=Depends(_require_user)):
    return {"ok": True, "policy": _load(user["email"]).get("policy") or dict(DEFAULT_POLICY)}


@router.post("/bootstrap-demo")
def bootstrap_demo(user=Depends(_require_user)):
    email = user["email"]
    register_record_class({
        "record_class": "GLOBAL_SUPERVISORY_AND_ENFORCEMENT_RECORD_PACKET",
        "retention_period": "7Y",
        "custodian": "records-governance-office",
        "status": "ACTIVE",
    }, user)
    place_legal_hold({
        "hold_code": "LH_2026_Q4_GLOBAL_SUPERVISORY_REVIEW",
        "scope": "REGULATORY_RECORDS_EVIDENCE_AND_COMMUNICATIONS",
        "owner": "general-counsel-office",
        "status": "ACTIVE",
    }, user)
    retrieve_supervisory_packet({
        "request_code": "SUP_REQ_2026_Q4_GLOBAL_RECORDS_PACKET",
        "requesting_authority": "primary-supervisor",
        "packet_scope": "FILINGS_ENFORCEMENT_STRESS_TEST_AND_LINEAGE_EVIDENCE",
        "status": "DELIVERED",
    }, user)
    release_hold({
        "hold_code": "LH_2026_Q4_GLOBAL_SUPERVISORY_REVIEW",
        "release_basis": "COUNSEL_APPROVAL_AND_SUPERVISORY_CLEARANCE",
        "status": "RELEASED",
    }, user)
    run = _evaluate(email, {
        "retention_coverage": 0.98,
        "hold_integrity_score": 0.97,
        "supervisory_retrieval_readiness": 0.96,
        "record_index_integrity": 0.97,
        "open_legal_hold_exceptions": 0,
        "overdue_supervisory_requests": 0,
    })
    return {"ok": True, "run": run, "summary": _summary_for_email(email)}
