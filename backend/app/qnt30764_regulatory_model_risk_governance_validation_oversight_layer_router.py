from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(prefix="/api/regulatory-model-risk-governance-validation-oversight-layer", tags=["regulatory-model-risk-governance-validation-oversight-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "regulatory_model_risk_governance_validation_oversight_layer"
DEFAULT_POLICY = {
    "retain_cycles": 180,
    "minimum_score": 96.0,
    "require_stress_testing_clear": True,
    "require_capital_adequacy_clear": True,
    "require_liquidity_command_clear": True,
    "minimum_model_inventory_coverage": 0.95,
    "minimum_validation_completion_score": 0.93,
    "minimum_model_governance_score": 0.94,
    "minimum_challenge_closure_score": 0.92,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _stress_testing():
    from backend.app import qnt30763_regulatory_stress_testing_submission_supervisory_challenge_layer_router as module
    return module


def _capital_adequacy():
    from backend.app import qnt30759_regulatory_capital_adequacy_surveillance_early_warning_layer_router as module
    return module


def _liquidity_command():
    from backend.app import qnt30760_regulatory_liquidity_stress_command_recovery_layer_router as module
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
            "model_families": [],
            "validation_reviews": [],
            "governance_actions": [],
            "challenge_closures": [],
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
        "regulatory_model_risk_governance_validation_oversight_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "model_family_count": len(s.get("model_families") or []),
            "validation_review_count": len(s.get("validation_reviews") or []),
            "governance_action_count": len(s.get("governance_actions") or []),
            "challenge_closure_count": len(s.get("challenge_closures") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "model_families": s.get("model_families") or [],
        "validation_reviews": s.get("validation_reviews") or [],
        "governance_actions": s.get("governance_actions") or [],
        "challenge_closures": s.get("challenge_closures") or [],
    }


def _cross_system_context(email: str) -> dict:
    return {
        "captured_at": _now_iso(),
        "stress_testing": (_stress_testing()._summary_for_email(email).get("regulatory_stress_testing_submission_supervisory_challenge_layer_status") or {}),
        "capital_adequacy": (_capital_adequacy()._summary_for_email(email).get("regulatory_capital_adequacy_surveillance_early_warning_layer_status") or {}),
        "liquidity_command": (_liquidity_command()._summary_for_email(email).get("regulatory_liquidity_stress_command_recovery_layer_status") or {}),
    }


def _band(score: float) -> str:
    if score >= 98.0:
        return "VALIDATION_OVERSIGHT_READY"
    if score >= 96.0:
        return "MODEL_RISK_GOVERNANCE_CLEAR"
    if score >= 92.0:
        return "HEIGHTENED_MODEL_RISK_WATCH"
    return "MODEL_REMEDIATION_REQUIRED"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _cross_system_context(email)

    model_inventory_coverage = float(payload.get("model_inventory_coverage", 0.0) or 0.0)
    validation_completion_score = float(payload.get("validation_completion_score", 0.0) or 0.0)
    model_governance_score = float(payload.get("model_governance_score", 0.0) or 0.0)
    challenge_closure_score = float(payload.get("challenge_closure_score", 0.0) or 0.0)
    overdue_validations = int(payload.get("overdue_validations", 0) or 0)
    high_severity_model_findings = int(payload.get("high_severity_model_findings", 0) or 0)

    score = 100.0
    reasons = []
    alerts = []

    if model_inventory_coverage < float(policy.get("minimum_model_inventory_coverage", 0.95)):
        score -= round((float(policy.get("minimum_model_inventory_coverage", 0.95)) - model_inventory_coverage) * 100.0, 2)
        reasons.append("model inventory coverage is below policy")
        alerts.append("MODEL_INVENTORY_COVERAGE_WEAK")
    if validation_completion_score < float(policy.get("minimum_validation_completion_score", 0.93)):
        score -= round((float(policy.get("minimum_validation_completion_score", 0.93)) - validation_completion_score) * 95.0, 2)
        reasons.append("validation completion score is below institutional standard")
        alerts.append("VALIDATION_COMPLETION_WEAK")
    if model_governance_score < float(policy.get("minimum_model_governance_score", 0.94)):
        score -= round((float(policy.get("minimum_model_governance_score", 0.94)) - model_governance_score) * 95.0, 2)
        reasons.append("model governance score is below policy")
        alerts.append("MODEL_GOVERNANCE_WEAK")
    if challenge_closure_score < float(policy.get("minimum_challenge_closure_score", 0.92)):
        score -= round((float(policy.get("minimum_challenge_closure_score", 0.92)) - challenge_closure_score) * 90.0, 2)
        reasons.append("challenge closure evidence is below institutional threshold")
        alerts.append("CHALLENGE_CLOSURE_WEAK")
    if overdue_validations > 0:
        score -= min(overdue_validations * 5.0, 20.0)
        reasons.append("overdue model validations remain unresolved")
        alerts.append("OVERDUE_VALIDATIONS")
    if high_severity_model_findings > 0:
        score -= min(high_severity_model_findings * 7.0, 28.0)
        reasons.append("high severity model findings remain open")
        alerts.append("HIGH_SEVERITY_MODEL_FINDINGS")

    stress_posture = str(ctx.get("stress_testing", {}).get("posture", "UNINITIALIZED"))
    capital_posture = str(ctx.get("capital_adequacy", {}).get("posture", "UNINITIALIZED"))
    liquidity_posture = str(ctx.get("liquidity_command", {}).get("posture", "UNINITIALIZED"))

    if policy.get("require_stress_testing_clear", True) and stress_posture not in {"SUPERVISORY_CHALLENGE_READY", "HEIGHTENED_SUPERVISORY_WATCH", "UNINITIALIZED"}:
        score -= 10.0; reasons.append("stress testing posture is not model-risk clear"); alerts.append("STRESS_TESTING_NOT_CLEAR")
    if policy.get("require_capital_adequacy_clear", True) and capital_posture not in {"CAPITAL_ADEQUACY_CLEAR", "EARLY_WARNING", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("capital adequacy posture is not validation-clear"); alerts.append("CAPITAL_ADEQUACY_NOT_CLEAR")
    if policy.get("require_liquidity_command_clear", True) and liquidity_posture not in {"LIQUIDITY_CLEAR", "CONTROLLED_STRESS", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("liquidity posture is not validation-clear"); alerts.append("LIQUIDITY_COMMAND_NOT_CLEAR")

    score = max(round(score, 2), 0.0)
    band = _band(score)
    posture = "MODEL_RISK_GOVERNANCE_CLEAR" if score >= float(policy.get("minimum_score", 96.0)) else ("HEIGHTENED_MODEL_RISK_WATCH" if score >= 92.0 else "MODEL_REMEDIATION_REQUIRED")
    operator_review_required = posture != "MODEL_RISK_GOVERNANCE_CLEAR" or overdue_validations > 0 or high_severity_model_findings > 0
    row = {
        "mission": "QNT30764",
        "evaluated_at": _now_iso(),
        "score": score,
        "band": band,
        "posture": posture,
        "operator_review_required": operator_review_required,
        "model_inventory_coverage": model_inventory_coverage,
        "validation_completion_score": validation_completion_score,
        "model_governance_score": model_governance_score,
        "challenge_closure_score": challenge_closure_score,
        "overdue_validations": overdue_validations,
        "high_severity_model_findings": high_severity_model_findings,
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


@router.post("/register-model-family")
def register_model_family(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "registered_at": _now_iso(),
        "model_family": payload.get("model_family", "CREDIT_LOSS_FORECASTING"),
        "tier": payload.get("tier", "TIER_1"),
        "owner": payload.get("owner", "model-risk-office"),
        "status": payload.get("status", "ACTIVE"),
    }
    _append(store, "model_families", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "model_family": row, "summary": _summary_for_email(email)}


@router.post("/record-validation-review")
def record_validation_review(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "recorded_at": _now_iso(),
        "review_code": payload.get("review_code", "VAL_2026_Q4_MARKET_RISK"),
        "validation_scope": payload.get("validation_scope", "FULL_SCOPE"),
        "owner": payload.get("owner", "independent-validation"),
        "status": payload.get("status", "OPEN"),
    }
    _append(store, "validation_reviews", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "validation_review": row, "summary": _summary_for_email(email)}


@router.post("/issue-governance-action")
def issue_governance_action(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "issued_at": _now_iso(),
        "action_code": payload.get("action_code", "MODEL_LIMITATION_ESCALATION"),
        "committee": payload.get("committee", "MODEL_RISK_COMMITTEE"),
        "severity": payload.get("severity", "HIGH"),
        "status": payload.get("status", "OPEN"),
    }
    _append(store, "governance_actions", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "governance_action": row, "summary": _summary_for_email(email)}


@router.post("/close-challenge-evidence")
def close_challenge_evidence(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "closed_at": _now_iso(),
        "challenge_code": payload.get("challenge_code", "MODEL_LIMITATION_ESCALATION"),
        "closure_evidence": payload.get("closure_evidence", "VALIDATION_MEMO_ACCEPTED"),
        "status": payload.get("status", "CLOSED"),
    }
    _append(store, "challenge_closures", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "challenge_closure": row, "summary": _summary_for_email(email)}


@router.get("/policy")
def policy(user=Depends(_require_user)):
    return {"ok": True, "policy": _load(user["email"]).get("policy") or dict(DEFAULT_POLICY)}


@router.post("/bootstrap-demo")
def bootstrap_demo(user=Depends(_require_user)):
    email = user["email"]
    register_model_family({
        "model_family": "ENTERPRISE_STRESS_AND_CAPITAL_MODELS",
        "tier": "TIER_1",
        "owner": "model-risk-office",
        "status": "ACTIVE",
    }, user)
    record_validation_review({
        "review_code": "VAL_2026_GLOBAL_CAPITAL_STACK",
        "validation_scope": "FULL_SCOPE",
        "owner": "independent-validation",
        "status": "OPEN",
    }, user)
    issue_governance_action({
        "action_code": "MODEL_LIMITATION_ESCALATION",
        "committee": "MODEL_RISK_COMMITTEE",
        "severity": "HIGH",
        "status": "OPEN",
    }, user)
    close_challenge_evidence({
        "challenge_code": "MODEL_LIMITATION_ESCALATION",
        "closure_evidence": "VALIDATION_MEMO_AND_CHALLENGE_RESPONSE_ACCEPTED",
        "status": "CLOSED",
    }, user)
    run = _evaluate(email, {
        "model_inventory_coverage": 0.98,
        "validation_completion_score": 0.95,
        "model_governance_score": 0.96,
        "challenge_closure_score": 0.95,
        "overdue_validations": 0,
        "high_severity_model_findings": 0,
    })
    return {"ok": True, "run": run, "summary": _summary_for_email(email)}
