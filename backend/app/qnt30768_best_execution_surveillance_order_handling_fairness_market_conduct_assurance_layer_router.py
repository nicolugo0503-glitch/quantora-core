from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(prefix="/api/best-execution-surveillance-order-handling-fairness-market-conduct-assurance-layer", tags=["best-execution-surveillance-order-handling-fairness-market-conduct-assurance-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "best_execution_surveillance_order_handling_fairness_market_conduct_assurance_layer"
DEFAULT_POLICY = {
    "retain_cycles": 180,
    "minimum_score": 96.0,
    "require_trade_conduct_clear": True,
    "require_governance_clear": True,
    "require_provenance_clear": True,
    "minimum_best_execution_score": 0.96,
    "minimum_order_fairness_score": 0.96,
    "minimum_venue_routing_integrity": 0.97,
    "minimum_disclosure_traceability": 0.97,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _trade_conduct():
    from backend.app import qnt30767_regulatory_surveillance_market_abuse_detection_trade_conduct_enforcement_layer_router as module
    return module


def _governance():
    from backend.app import qnt30751_multi_jurisdiction_governance_layer_router as module
    return module


def _provenance():
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
            "executions": [],
            "best_execution_reviews": [],
            "routing_validations": [],
            "execution_anomalies": [],
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
        "best_execution_surveillance_order_handling_fairness_market_conduct_assurance_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "execution_count": len(s.get("executions") or []),
            "best_execution_review_count": len(s.get("best_execution_reviews") or []),
            "routing_validation_count": len(s.get("routing_validations") or []),
            "execution_anomaly_count": len(s.get("execution_anomalies") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "executions": s.get("executions") or [],
        "best_execution_reviews": s.get("best_execution_reviews") or [],
        "routing_validations": s.get("routing_validations") or [],
        "execution_anomalies": s.get("execution_anomalies") or [],
    }


def _cross_system_context(email: str) -> dict:
    return {
        "captured_at": _now_iso(),
        "trade_conduct": (_trade_conduct()._summary_for_email(email).get("regulatory_surveillance_market_abuse_detection_trade_conduct_enforcement_layer_status") or {}),
        "governance": (_governance()._summary_for_email(email).get("multi_jurisdiction_governance_layer_status") or {}),
        "provenance": (_provenance()._summary_for_email(email).get("regulatory_data_lineage_evidence_provenance_attestation_fabric_status") or {}),
    }


def _band(score: float) -> str:
    if score >= 98.0:
        return "BEST_EXECUTION_COMMAND_READY"
    if score >= 96.0:
        return "MARKET_CONDUCT_ASSURANCE_CLEAR"
    if score >= 92.0:
        return "EXECUTION_QUALITY_WATCH"
    return "EXECUTION_CONDUCT_REMEDIATION_REQUIRED"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _cross_system_context(email)

    best_execution_score = float(payload.get("best_execution_score", 0.0) or 0.0)
    order_fairness_score = float(payload.get("order_fairness_score", 0.0) or 0.0)
    venue_routing_integrity = float(payload.get("venue_routing_integrity", 0.0) or 0.0)
    disclosure_traceability = float(payload.get("disclosure_traceability", 0.0) or 0.0)
    unresolved_execution_anomalies = int(payload.get("unresolved_execution_anomalies", 0) or 0)
    unresolved_routing_exceptions = int(payload.get("unresolved_routing_exceptions", 0) or 0)

    score = 100.0
    reasons = []
    alerts = []

    if best_execution_score < float(policy.get("minimum_best_execution_score", 0.96)):
        score -= round((float(policy.get("minimum_best_execution_score", 0.96)) - best_execution_score) * 100.0, 2)
        reasons.append("best execution score is below institutional tolerance")
        alerts.append("BEST_EXECUTION_SCORE_WEAK")
    if order_fairness_score < float(policy.get("minimum_order_fairness_score", 0.96)):
        score -= round((float(policy.get("minimum_order_fairness_score", 0.96)) - order_fairness_score) * 100.0, 2)
        reasons.append("order handling fairness is below regulator-grade threshold")
        alerts.append("ORDER_FAIRNESS_WEAK")
    if venue_routing_integrity < float(policy.get("minimum_venue_routing_integrity", 0.97)):
        score -= round((float(policy.get("minimum_venue_routing_integrity", 0.97)) - venue_routing_integrity) * 100.0, 2)
        reasons.append("venue routing integrity is below execution governance requirement")
        alerts.append("VENUE_ROUTING_INTEGRITY_WEAK")
    if disclosure_traceability < float(policy.get("minimum_disclosure_traceability", 0.97)):
        score -= round((float(policy.get("minimum_disclosure_traceability", 0.97)) - disclosure_traceability) * 100.0, 2)
        reasons.append("disclosure traceability is below evidence continuity standard")
        alerts.append("DISCLOSURE_TRACEABILITY_WEAK")
    if unresolved_execution_anomalies > 0:
        score -= min(unresolved_execution_anomalies * 5.0, 20.0)
        reasons.append("execution anomalies remain unresolved")
        alerts.append("OPEN_EXECUTION_ANOMALIES")
    if unresolved_routing_exceptions > 0:
        score -= min(unresolved_routing_exceptions * 4.0, 16.0)
        reasons.append("routing exceptions remain unresolved")
        alerts.append("OPEN_ROUTING_EXCEPTIONS")

    trade_conduct_posture = str(ctx.get("trade_conduct", {}).get("posture", "UNINITIALIZED"))
    governance_posture = str(ctx.get("governance", {}).get("posture", "UNINITIALIZED"))
    provenance_posture = str(ctx.get("provenance", {}).get("posture", "UNINITIALIZED"))

    if policy.get("require_trade_conduct_clear", True) and trade_conduct_posture not in {"TRADE_CONDUCT_ENFORCEMENT_CLEAR", "HEIGHTENED_SURVEILLANCE_WATCH", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("trade conduct posture is not execution-clear"); alerts.append("TRADE_CONDUCT_NOT_CLEAR")
    if policy.get("require_governance_clear", True) and governance_posture not in {"GLOBAL_GOVERNANCE_READY", "JURISDICTION_WATCH", "UNINITIALIZED"}:
        score -= 7.0; reasons.append("jurisdiction governance posture is not execution-clear"); alerts.append("GOVERNANCE_NOT_CLEAR")
    if policy.get("require_provenance_clear", True) and provenance_posture not in {"EVIDENCE_PROVENANCE_CLEAR", "HEIGHTENED_DATA_GOVERNANCE_WATCH", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("evidence provenance posture is not execution-clear"); alerts.append("PROVENANCE_NOT_CLEAR")

    score = max(round(score, 2), 0.0)
    band = _band(score)
    posture = "MARKET_CONDUCT_ASSURANCE_CLEAR" if score >= float(policy.get("minimum_score", 96.0)) else ("EXECUTION_QUALITY_WATCH" if score >= 92.0 else "EXECUTION_CONDUCT_REMEDIATION_REQUIRED")
    operator_review_required = posture != "MARKET_CONDUCT_ASSURANCE_CLEAR" or unresolved_execution_anomalies > 0 or unresolved_routing_exceptions > 0
    row = {
        "mission": "QNT30768",
        "evaluated_at": _now_iso(),
        "score": score,
        "band": band,
        "posture": posture,
        "operator_review_required": operator_review_required,
        "best_execution_score": best_execution_score,
        "order_fairness_score": order_fairness_score,
        "venue_routing_integrity": venue_routing_integrity,
        "disclosure_traceability": disclosure_traceability,
        "unresolved_execution_anomalies": unresolved_execution_anomalies,
        "unresolved_routing_exceptions": unresolved_routing_exceptions,
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


@router.post("/record-execution")
def record_execution(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "recorded_at": _now_iso(),
        "order_id": payload.get("order_id", "ORD_2026_Q4_GLOBAL_EXEC_001"),
        "venue": payload.get("venue", "PRIMARY_MULTI_ASSET_ROUTER"),
        "instrument": payload.get("instrument", "BTC-USD"),
        "status": payload.get("status", "EXECUTED"),
    }
    _append(store, "executions", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "execution": row, "summary": _summary_for_email(email)}


@router.post("/evaluate-best-execution")
def evaluate_best_execution(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "reviewed_at": _now_iso(),
        "review_code": payload.get("review_code", "BER_2026_Q4_GLOBAL_EXECUTION_REVIEW"),
        "benchmark": payload.get("benchmark", "NBBO_OR_EQUIVALENT_BEST_MARKET"),
        "status": payload.get("status", "PASSED"),
    }
    _append(store, "best_execution_reviews", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "best_execution_review": row, "summary": _summary_for_email(email)}


@router.post("/validate-order-routing")
def validate_order_routing(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "validated_at": _now_iso(),
        "route_code": payload.get("route_code", "ROUTE_2026_Q4_MULTI_VENUE_FAIRNESS"),
        "fairness_basis": payload.get("fairness_basis", "PRICE_TIME_LIQUIDITY_ACCESS_AND_LATENCY"),
        "status": payload.get("status", "VALIDATED"),
    }
    _append(store, "routing_validations", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "routing_validation": row, "summary": _summary_for_email(email)}


@router.post("/flag-execution-anomaly")
def flag_execution_anomaly(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "flagged_at": _now_iso(),
        "anomaly_code": payload.get("anomaly_code", "EXA_2026_Q4_SLIPPAGE_CLUSTER"),
        "severity": payload.get("severity", "HIGH"),
        "status": payload.get("status", "OPEN"),
    }
    _append(store, "execution_anomalies", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "execution_anomaly": row, "summary": _summary_for_email(email)}


@router.get("/policy")
def policy(user=Depends(_require_user)):
    return {"ok": True, "policy": _load(user["email"]).get("policy") or dict(DEFAULT_POLICY)}


@router.post("/bootstrap-demo")
def bootstrap_demo(user=Depends(_require_user)):
    email = user["email"]
    record_execution({}, user)
    evaluate_best_execution({}, user)
    validate_order_routing({}, user)
    flag_execution_anomaly({"status": "CLOSED", "severity": "MEDIUM"}, user)
    run = _evaluate(email, {
        "best_execution_score": 0.98,
        "order_fairness_score": 0.97,
        "venue_routing_integrity": 0.98,
        "disclosure_traceability": 0.98,
        "unresolved_execution_anomalies": 0,
        "unresolved_routing_exceptions": 0,
    })
    return {"ok": True, "run": run, "summary": _summary_for_email(email)}
