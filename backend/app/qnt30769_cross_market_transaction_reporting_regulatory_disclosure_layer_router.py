from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(prefix="/api/cross-market-transaction-reporting-regulatory-disclosure-layer", tags=["cross-market-transaction-reporting-regulatory-disclosure-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "cross_market_transaction_reporting_regulatory_disclosure_layer"
DEFAULT_POLICY = {
    "retain_cycles": 180,
    "minimum_score": 96.0,
    "require_filing_clear": True,
    "require_governance_clear": True,
    "require_provenance_clear": True,
    "require_trade_conduct_clear": True,
    "minimum_reporting_completeness": 0.98,
    "minimum_jurisdiction_mapping_quality": 0.97,
    "minimum_submission_timeliness": 0.97,
    "minimum_disclosure_traceability": 0.98,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _filing():
    from backend.app import qnt30755_regulatory_filing_submission_orchestration_layer_router as module
    return module


def _governance():
    from backend.app import qnt30751_multi_jurisdiction_governance_layer_router as module
    return module


def _provenance():
    from backend.app import qnt30765_regulatory_data_lineage_evidence_provenance_attestation_fabric_router as module
    return module


def _trade_conduct():
    from backend.app import qnt30767_regulatory_surveillance_market_abuse_detection_trade_conduct_enforcement_layer_router as module
    return module


def _best_execution():
    from backend.app import qnt30768_best_execution_surveillance_order_handling_fairness_market_conduct_assurance_layer_router as module
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
            "reporting_cycles": [],
            "report_stagings": [],
            "submission_batches": [],
            "disclosure_events": [],
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
        "cross_market_transaction_reporting_regulatory_disclosure_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "reporting_cycle_count": len(s.get("reporting_cycles") or []),
            "report_staging_count": len(s.get("report_stagings") or []),
            "submission_batch_count": len(s.get("submission_batches") or []),
            "disclosure_event_count": len(s.get("disclosure_events") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "reporting_cycles": s.get("reporting_cycles") or [],
        "report_stagings": s.get("report_stagings") or [],
        "submission_batches": s.get("submission_batches") or [],
        "disclosure_events": s.get("disclosure_events") or [],
    }


def _cross_system_context(email: str) -> dict:
    return {
        "captured_at": _now_iso(),
        "filing": (_filing()._summary_for_email(email).get("regulatory_filing_submission_orchestration_layer_status") or {}),
        "governance": (_governance()._summary_for_email(email).get("multi_jurisdiction_governance_layer_status") or {}),
        "provenance": (_provenance()._summary_for_email(email).get("regulatory_data_lineage_evidence_provenance_attestation_fabric_status") or {}),
        "trade_conduct": (_trade_conduct()._summary_for_email(email).get("regulatory_surveillance_market_abuse_detection_trade_conduct_enforcement_layer_status") or {}),
        "best_execution": (_best_execution()._summary_for_email(email).get("best_execution_surveillance_order_handling_fairness_market_conduct_assurance_layer_status") or {}),
    }


def _band(score: float) -> str:
    if score >= 98.0:
        return "GLOBAL_TRANSACTION_REPORTING_READY"
    if score >= 96.0:
        return "REPORTING_AND_DISCLOSURE_CLEAR"
    if score >= 92.0:
        return "REPORTING_WATCH"
    return "DISCLOSURE_REMEDIATION_REQUIRED"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _cross_system_context(email)

    reporting_completeness = float(payload.get("reporting_completeness", 0.0) or 0.0)
    jurisdiction_mapping_quality = float(payload.get("jurisdiction_mapping_quality", 0.0) or 0.0)
    submission_timeliness = float(payload.get("submission_timeliness", 0.0) or 0.0)
    disclosure_traceability = float(payload.get("disclosure_traceability", 0.0) or 0.0)
    open_submission_exceptions = int(payload.get("open_submission_exceptions", 0) or 0)
    open_disclosure_breaks = int(payload.get("open_disclosure_breaks", 0) or 0)

    score = 100.0
    reasons = []
    alerts = []

    if reporting_completeness < float(policy.get("minimum_reporting_completeness", 0.98)):
        score -= round((float(policy.get("minimum_reporting_completeness", 0.98)) - reporting_completeness) * 100.0, 2)
        reasons.append("reporting completeness is below global reporting threshold")
        alerts.append("REPORTING_COMPLETENESS_WEAK")
    if jurisdiction_mapping_quality < float(policy.get("minimum_jurisdiction_mapping_quality", 0.97)):
        score -= round((float(policy.get("minimum_jurisdiction_mapping_quality", 0.97)) - jurisdiction_mapping_quality) * 95.0, 2)
        reasons.append("jurisdiction mapping quality is below filing policy")
        alerts.append("JURISDICTION_MAPPING_WEAK")
    if submission_timeliness < float(policy.get("minimum_submission_timeliness", 0.97)):
        score -= round((float(policy.get("minimum_submission_timeliness", 0.97)) - submission_timeliness) * 95.0, 2)
        reasons.append("submission timeliness is below reporting command threshold")
        alerts.append("SUBMISSION_TIMELINESS_WEAK")
    if disclosure_traceability < float(policy.get("minimum_disclosure_traceability", 0.98)):
        score -= round((float(policy.get("minimum_disclosure_traceability", 0.98)) - disclosure_traceability) * 100.0, 2)
        reasons.append("disclosure traceability is below evidence continuity requirement")
        alerts.append("DISCLOSURE_TRACEABILITY_WEAK")
    if open_submission_exceptions > 0:
        score -= min(open_submission_exceptions * 5.0, 20.0)
        reasons.append("submission exceptions remain unresolved")
        alerts.append("OPEN_SUBMISSION_EXCEPTIONS")
    if open_disclosure_breaks > 0:
        score -= min(open_disclosure_breaks * 5.0, 20.0)
        reasons.append("disclosure breaks remain unresolved")
        alerts.append("OPEN_DISCLOSURE_BREAKS")

    filing_posture = str(ctx.get("filing", {}).get("posture", "UNINITIALIZED"))
    governance_posture = str(ctx.get("governance", {}).get("posture", "UNINITIALIZED"))
    provenance_posture = str(ctx.get("provenance", {}).get("posture", "UNINITIALIZED"))
    trade_conduct_posture = str(ctx.get("trade_conduct", {}).get("posture", "UNINITIALIZED"))
    best_execution_posture = str(ctx.get("best_execution", {}).get("posture", "UNINITIALIZED"))

    if policy.get("require_filing_clear", True) and filing_posture not in {"FILING_COMMAND_CLEAR", "FILING_WATCH", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("filing posture is not reporting-clear"); alerts.append("FILING_NOT_CLEAR")
    if policy.get("require_governance_clear", True) and governance_posture not in {"GLOBAL_GOVERNANCE_READY", "JURISDICTION_WATCH", "UNINITIALIZED"}:
        score -= 7.0; reasons.append("governance posture is not reporting-clear"); alerts.append("GOVERNANCE_NOT_CLEAR")
    if policy.get("require_provenance_clear", True) and provenance_posture not in {"EVIDENCE_PROVENANCE_CLEAR", "HEIGHTENED_DATA_GOVERNANCE_WATCH", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("provenance posture is not reporting-clear"); alerts.append("PROVENANCE_NOT_CLEAR")
    if policy.get("require_trade_conduct_clear", True) and trade_conduct_posture not in {"TRADE_CONDUCT_ENFORCEMENT_CLEAR", "HEIGHTENED_SURVEILLANCE_WATCH", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("trade conduct posture is not disclosure-clear"); alerts.append("TRADE_CONDUCT_NOT_CLEAR")
    if best_execution_posture not in {"MARKET_CONDUCT_ASSURANCE_CLEAR", "EXECUTION_QUALITY_WATCH", "UNINITIALIZED"}:
        score -= 7.0; reasons.append("best execution posture is not reporting-clear"); alerts.append("BEST_EXECUTION_NOT_CLEAR")

    score = max(round(score, 2), 0.0)
    band = _band(score)
    posture = "REPORTING_AND_DISCLOSURE_CLEAR" if score >= float(policy.get("minimum_score", 96.0)) else ("REPORTING_WATCH" if score >= 92.0 else "DISCLOSURE_REMEDIATION_REQUIRED")
    operator_review_required = posture != "REPORTING_AND_DISCLOSURE_CLEAR" or open_submission_exceptions > 0 or open_disclosure_breaks > 0
    row = {
        "mission": "QNT30769",
        "evaluated_at": _now_iso(),
        "score": score,
        "band": band,
        "posture": posture,
        "operator_review_required": operator_review_required,
        "reporting_completeness": reporting_completeness,
        "jurisdiction_mapping_quality": jurisdiction_mapping_quality,
        "submission_timeliness": submission_timeliness,
        "disclosure_traceability": disclosure_traceability,
        "open_submission_exceptions": open_submission_exceptions,
        "open_disclosure_breaks": open_disclosure_breaks,
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


@router.post("/register-reporting-cycle")
def register_reporting_cycle(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "registered_at": _now_iso(),
        "cycle_code": payload.get("cycle_code", "RTR_2026_Q4_GLOBAL_TRANSACTION_REPORTING"),
        "framework_scope": payload.get("framework_scope", "MIFID_CAT_EMIR"),
        "status": payload.get("status", "OPEN"),
    }
    _append(store, "reporting_cycles", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "reporting_cycle": row, "summary": _summary_for_email(email)}


@router.post("/stage-report")
def stage_report(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "staged_at": _now_iso(),
        "report_code": payload.get("report_code", "RPT_2026_Q4_MULTI_JURISDICTION_DISCLOSURE"),
        "jurisdiction_pack": payload.get("jurisdiction_pack", "EU_US_UK"),
        "status": payload.get("status", "STAGED"),
    }
    _append(store, "report_stagings", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "report_staging": row, "summary": _summary_for_email(email)}


@router.post("/submit-batch")
def submit_batch(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "submitted_at": _now_iso(),
        "batch_code": payload.get("batch_code", "SUB_2026_Q4_CROSS_MARKET_BATCH_001"),
        "submission_target": payload.get("submission_target", "GLOBAL_REGULATORY_GATEWAY"),
        "status": payload.get("status", "SUBMITTED"),
    }
    _append(store, "submission_batches", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "submission_batch": row, "summary": _summary_for_email(email)}


@router.post("/record-disclosure-event")
def record_disclosure_event(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "recorded_at": _now_iso(),
        "event_code": payload.get("event_code", "DISC_2026_Q4_TRANSACTION_DISCLOSURE_CONFIRMATION"),
        "disclosure_channel": payload.get("disclosure_channel", "REGULATORY_AND_INVESTOR_DISCLOSURE"),
        "status": payload.get("status", "RECORDED"),
    }
    _append(store, "disclosure_events", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "disclosure_event": row, "summary": _summary_for_email(email)}


@router.get("/policy")
def policy(user=Depends(_require_user)):
    return {"ok": True, "policy": _load(user["email"]).get("policy") or dict(DEFAULT_POLICY)}


@router.post("/bootstrap-demo")
def bootstrap_demo(user=Depends(_require_user)):
    email = user["email"]
    register_reporting_cycle({}, user)
    stage_report({}, user)
    submit_batch({}, user)
    record_disclosure_event({}, user)
    run = _evaluate(email, {
        "reporting_completeness": 0.99,
        "jurisdiction_mapping_quality": 0.98,
        "submission_timeliness": 0.98,
        "disclosure_traceability": 0.99,
        "open_submission_exceptions": 0,
        "open_disclosure_breaks": 0,
    })
    return {"ok": True, "run": run, "summary": _summary_for_email(email)}
