from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(prefix="/api/regulatory-surveillance-market-abuse-detection-trade-conduct-enforcement-layer", tags=["regulatory-surveillance-market-abuse-detection-trade-conduct-enforcement-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "regulatory_surveillance_market_abuse_detection_trade_conduct_enforcement_layer"
DEFAULT_POLICY = {
    "retain_cycles": 180,
    "minimum_score": 96.0,
    "require_enforcement_response_clear": True,
    "require_records_retrieval_clear": True,
    "require_provenance_clear": True,
    "require_model_risk_clear": True,
    "minimum_surveillance_coverage": 0.97,
    "minimum_alert_precision_score": 0.95,
    "minimum_conduct_escalation_readiness": 0.96,
    "minimum_evidence_chain_integrity": 0.97,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _enforcement_response():
    from backend.app import qnt30758_regulatory_enforcement_response_consent_order_command_layer_router as module
    return module


def _records_retrieval():
    from backend.app import qnt30766_regulatory_records_retention_legal_hold_supervisory_retrieval_command_layer_router as module
    return module


def _provenance_fabric():
    from backend.app import qnt30765_regulatory_data_lineage_evidence_provenance_attestation_fabric_router as module
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
            "surveillance_signals": [],
            "trade_conduct_cases": [],
            "market_abuse_alerts": [],
            "case_closures": [],
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
        "regulatory_surveillance_market_abuse_detection_trade_conduct_enforcement_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "surveillance_signal_count": len(s.get("surveillance_signals") or []),
            "trade_conduct_case_count": len(s.get("trade_conduct_cases") or []),
            "market_abuse_alert_count": len(s.get("market_abuse_alerts") or []),
            "case_closure_count": len(s.get("case_closures") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "surveillance_signals": s.get("surveillance_signals") or [],
        "trade_conduct_cases": s.get("trade_conduct_cases") or [],
        "market_abuse_alerts": s.get("market_abuse_alerts") or [],
        "case_closures": s.get("case_closures") or [],
    }


def _cross_system_context(email: str) -> dict:
    return {
        "captured_at": _now_iso(),
        "enforcement_response": (_enforcement_response()._summary_for_email(email).get("regulatory_enforcement_response_consent_order_command_layer_status") or {}),
        "records_retrieval": (_records_retrieval()._summary_for_email(email).get("regulatory_records_retention_legal_hold_supervisory_retrieval_command_layer_status") or {}),
        "provenance_fabric": (_provenance_fabric()._summary_for_email(email).get("regulatory_data_lineage_evidence_provenance_attestation_fabric_status") or {}),
        "model_risk": (_model_risk()._summary_for_email(email).get("regulatory_model_risk_governance_validation_oversight_layer_status") or {}),
    }


def _band(score: float) -> str:
    if score >= 98.0:
        return "REGULATORY_SURVEILLANCE_COMMAND_READY"
    if score >= 96.0:
        return "TRADE_CONDUCT_ENFORCEMENT_CLEAR"
    if score >= 92.0:
        return "HEIGHTENED_SURVEILLANCE_WATCH"
    return "CONDUCT_REMEDIATION_REQUIRED"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _cross_system_context(email)

    surveillance_coverage = float(payload.get("surveillance_coverage", 0.0) or 0.0)
    alert_precision_score = float(payload.get("alert_precision_score", 0.0) or 0.0)
    conduct_escalation_readiness = float(payload.get("conduct_escalation_readiness", 0.0) or 0.0)
    evidence_chain_integrity = float(payload.get("evidence_chain_integrity", 0.0) or 0.0)
    open_priority_alerts = int(payload.get("open_priority_alerts", 0) or 0)
    open_conduct_breaches = int(payload.get("open_conduct_breaches", 0) or 0)

    score = 100.0
    reasons = []
    alerts = []

    if surveillance_coverage < float(policy.get("minimum_surveillance_coverage", 0.97)):
        score -= round((float(policy.get("minimum_surveillance_coverage", 0.97)) - surveillance_coverage) * 100.0, 2)
        reasons.append("surveillance coverage is below institutional monitoring policy")
        alerts.append("SURVEILLANCE_COVERAGE_WEAK")
    if alert_precision_score < float(policy.get("minimum_alert_precision_score", 0.95)):
        score -= round((float(policy.get("minimum_alert_precision_score", 0.95)) - alert_precision_score) * 95.0, 2)
        reasons.append("alert precision is below regulator-grade escalation tolerance")
        alerts.append("ALERT_PRECISION_WEAK")
    if conduct_escalation_readiness < float(policy.get("minimum_conduct_escalation_readiness", 0.96)):
        score -= round((float(policy.get("minimum_conduct_escalation_readiness", 0.96)) - conduct_escalation_readiness) * 95.0, 2)
        reasons.append("trade conduct escalation readiness is below command threshold")
        alerts.append("CONDUCT_ESCALATION_READINESS_WEAK")
    if evidence_chain_integrity < float(policy.get("minimum_evidence_chain_integrity", 0.97)):
        score -= round((float(policy.get("minimum_evidence_chain_integrity", 0.97)) - evidence_chain_integrity) * 100.0, 2)
        reasons.append("evidence chain integrity is below enforcement standard")
        alerts.append("EVIDENCE_CHAIN_INTEGRITY_WEAK")
    if open_priority_alerts > 0:
        score -= min(open_priority_alerts * 5.0, 20.0)
        reasons.append("priority surveillance alerts remain unresolved")
        alerts.append("OPEN_PRIORITY_ALERTS")
    if open_conduct_breaches > 0:
        score -= min(open_conduct_breaches * 6.0, 24.0)
        reasons.append("open trade conduct breaches remain unresolved")
        alerts.append("OPEN_CONDUCT_BREACHES")

    enforcement_posture = str(ctx.get("enforcement_response", {}).get("posture", "UNINITIALIZED"))
    records_posture = str(ctx.get("records_retrieval", {}).get("posture", "UNINITIALIZED"))
    provenance_posture = str(ctx.get("provenance_fabric", {}).get("posture", "UNINITIALIZED"))
    model_risk_posture = str(ctx.get("model_risk", {}).get("posture", "UNINITIALIZED"))

    if policy.get("require_enforcement_response_clear", True) and enforcement_posture not in {"ENFORCEMENT_COMMAND_CLEAR", "WATCH", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("enforcement response posture is not surveillance-clear"); alerts.append("ENFORCEMENT_RESPONSE_NOT_CLEAR")
    if policy.get("require_records_retrieval_clear", True) and records_posture not in {"RECORDS_AND_HOLD_CONTROL_CLEAR", "HEIGHTENED_RECORDS_WATCH", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("records retrieval posture is not conduct-clear"); alerts.append("RECORDS_RETRIEVAL_NOT_CLEAR")
    if policy.get("require_provenance_clear", True) and provenance_posture not in {"EVIDENCE_PROVENANCE_CLEAR", "HEIGHTENED_DATA_GOVERNANCE_WATCH", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("evidence provenance posture is not surveillance-clear"); alerts.append("PROVENANCE_FABRIC_NOT_CLEAR")
    if policy.get("require_model_risk_clear", True) and model_risk_posture not in {"MODEL_RISK_GOVERNANCE_CLEAR", "HEIGHTENED_MODEL_RISK_WATCH", "UNINITIALIZED"}:
        score -= 7.0; reasons.append("model risk posture is not monitoring-clear"); alerts.append("MODEL_RISK_NOT_CLEAR")

    score = max(round(score, 2), 0.0)
    band = _band(score)
    posture = "TRADE_CONDUCT_ENFORCEMENT_CLEAR" if score >= float(policy.get("minimum_score", 96.0)) else ("HEIGHTENED_SURVEILLANCE_WATCH" if score >= 92.0 else "CONDUCT_REMEDIATION_REQUIRED")
    operator_review_required = posture != "TRADE_CONDUCT_ENFORCEMENT_CLEAR" or open_priority_alerts > 0 or open_conduct_breaches > 0
    row = {
        "mission": "QNT30767",
        "evaluated_at": _now_iso(),
        "score": score,
        "band": band,
        "posture": posture,
        "operator_review_required": operator_review_required,
        "surveillance_coverage": surveillance_coverage,
        "alert_precision_score": alert_precision_score,
        "conduct_escalation_readiness": conduct_escalation_readiness,
        "evidence_chain_integrity": evidence_chain_integrity,
        "open_priority_alerts": open_priority_alerts,
        "open_conduct_breaches": open_conduct_breaches,
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


@router.post("/register-surveillance-signal")
def register_surveillance_signal(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "registered_at": _now_iso(),
        "signal_code": payload.get("signal_code", "SIG_2026_Q4_LAYERED_FLOW_CLUSTER"),
        "signal_type": payload.get("signal_type", "MARKET_ABUSE_SURVEILLANCE"),
        "venue_scope": payload.get("venue_scope", "MULTI_VENUE"),
        "status": payload.get("status", "OPEN"),
    }
    _append(store, "surveillance_signals", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "surveillance_signal": row, "summary": _summary_for_email(email)}


@router.post("/register-trade-conduct-case")
def register_trade_conduct_case(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "opened_at": _now_iso(),
        "case_code": payload.get("case_code", "TCC_2026_Q4_CROSS_VENUE_BEHAVIOR_REVIEW"),
        "case_owner": payload.get("case_owner", "market-conduct-office"),
        "severity": payload.get("severity", "HIGH"),
        "status": payload.get("status", "UNDER_REVIEW"),
    }
    _append(store, "trade_conduct_cases", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "trade_conduct_case": row, "summary": _summary_for_email(email)}


@router.post("/escalate-market-abuse-alert")
def escalate_market_abuse_alert(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "escalated_at": _now_iso(),
        "alert_code": payload.get("alert_code", "MA_2026_Q4_WASH_LAYERING_PATTERN"),
        "escalation_target": payload.get("escalation_target", "regulatory-surveillance-command"),
        "evidence_packet": payload.get("evidence_packet", "TRADE_AND_COMMUNICATION_CHAIN"),
        "status": payload.get("status", "ESCALATED"),
    }
    _append(store, "market_abuse_alerts", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "market_abuse_alert": row, "summary": _summary_for_email(email)}


@router.post("/close-case")
def close_case(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "closed_at": _now_iso(),
        "case_code": payload.get("case_code", "TCC_2026_Q4_CROSS_VENUE_BEHAVIOR_REVIEW"),
        "closure_basis": payload.get("closure_basis", "EVIDENCE_VALIDATED_AND_ACTION_COMPLETE"),
        "status": payload.get("status", "CLOSED"),
    }
    _append(store, "case_closures", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "case_closure": row, "summary": _summary_for_email(email)}


@router.get("/policy")
def policy(user=Depends(_require_user)):
    return {"ok": True, "policy": _load(user["email"]).get("policy") or dict(DEFAULT_POLICY)}


@router.post("/bootstrap-demo")
def bootstrap_demo(user=Depends(_require_user)):
    email = user["email"]
    register_surveillance_signal({
        "signal_code": "SIG_2026_Q4_CROSS_VENUE_PATTERN_SURGE",
        "signal_type": "MARKET_ABUSE_SURVEILLANCE",
        "venue_scope": "GLOBAL_MULTI_VENUE",
        "status": "OPEN",
    }, user)
    register_trade_conduct_case({
        "case_code": "TCC_2026_Q4_GLOBAL_CONDUCT_REVIEW",
        "case_owner": "market-conduct-office",
        "severity": "HIGH",
        "status": "UNDER_REVIEW",
    }, user)
    escalate_market_abuse_alert({
        "alert_code": "MA_2026_Q4_LAYERING_AND_SPOOFING_PATTERN",
        "escalation_target": "regulatory-surveillance-command",
        "evidence_packet": "ORDER_TRADE_COMMUNICATION_AND_LINEAGE_CHAIN",
        "status": "ESCALATED",
    }, user)
    close_case({
        "case_code": "TCC_2026_Q4_GLOBAL_CONDUCT_REVIEW",
        "closure_basis": "REMEDIATION_COMPLETE_AND_EVIDENCE_ARCHIVED",
        "status": "CLOSED",
    }, user)
    run = _evaluate(email, {
        "surveillance_coverage": 0.98,
        "alert_precision_score": 0.96,
        "conduct_escalation_readiness": 0.97,
        "evidence_chain_integrity": 0.98,
        "open_priority_alerts": 0,
        "open_conduct_breaches": 0,
    })
    return {"ok": True, "run": run, "summary": _summary_for_email(email)}
