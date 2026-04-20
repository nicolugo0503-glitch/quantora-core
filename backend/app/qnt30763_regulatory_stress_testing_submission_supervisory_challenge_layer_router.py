from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(prefix="/api/regulatory-stress-testing-submission-supervisory-challenge-layer", tags=["regulatory-stress-testing-submission-supervisory-challenge-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "regulatory_stress_testing_submission_supervisory_challenge_layer"
DEFAULT_POLICY = {
    "retain_cycles": 180,
    "minimum_score": 96.0,
    "require_capital_adequacy_clear": True,
    "require_liquidity_command_clear": True,
    "require_resolution_control_clear": True,
    "require_simulation_command_clear": True,
    "minimum_stress_test_coverage": 0.95,
    "minimum_model_traceability_score": 0.92,
    "minimum_submission_readiness_score": 0.94,
    "minimum_supervisory_challenge_response_score": 0.93,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _capital_adequacy():
    from backend.app import qnt30759_regulatory_capital_adequacy_surveillance_early_warning_layer_router as module
    return module


def _liquidity_command():
    from backend.app import qnt30760_regulatory_liquidity_stress_command_recovery_layer_router as module
    return module


def _resolution_control():
    from backend.app import qnt30761_regulatory_resolution_planning_wind_down_control_layer_router as module
    return module


def _simulation_command():
    from backend.app import qnt30762_recovery_resolution_scenario_simulation_command_layer_router as module
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
            "cycles": [],
            "staged_submissions": [],
            "supervisory_challenges": [],
            "closed_challenges": [],
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
        "regulatory_stress_testing_submission_supervisory_challenge_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "cycle_count": len(s.get("cycles") or []),
            "staged_submission_count": len(s.get("staged_submissions") or []),
            "supervisory_challenge_count": len(s.get("supervisory_challenges") or []),
            "closed_challenge_count": len(s.get("closed_challenges") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "cycles": s.get("cycles") or [],
        "staged_submissions": s.get("staged_submissions") or [],
        "supervisory_challenges": s.get("supervisory_challenges") or [],
        "closed_challenges": s.get("closed_challenges") or [],
    }


def _cross_system_context(email: str) -> dict:
    return {
        "captured_at": _now_iso(),
        "capital_adequacy": (_capital_adequacy()._summary_for_email(email).get("regulatory_capital_adequacy_surveillance_early_warning_layer_status") or {}),
        "liquidity_command": (_liquidity_command()._summary_for_email(email).get("regulatory_liquidity_stress_command_recovery_layer_status") or {}),
        "resolution_control": (_resolution_control()._summary_for_email(email).get("regulatory_resolution_planning_wind_down_control_layer_status") or {}),
        "simulation_command": (_simulation_command()._summary_for_email(email).get("recovery_resolution_scenario_simulation_command_layer_status") or {}),
    }


def _band(score: float) -> str:
    if score >= 98.0:
        return "SUPERVISORY_CHALLENGE_READY"
    if score >= 96.0:
        return "SUBMISSION_READY"
    if score >= 92.0:
        return "HEIGHTENED_SUPERVISORY_WATCH"
    return "REMEDIATION_REQUIRED"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _cross_system_context(email)

    stress_test_coverage = float(payload.get("stress_test_coverage", 0.0) or 0.0)
    model_traceability_score = float(payload.get("model_traceability_score", 0.0) or 0.0)
    submission_readiness_score = float(payload.get("submission_readiness_score", 0.0) or 0.0)
    supervisory_challenge_response_score = float(payload.get("supervisory_challenge_response_score", 0.0) or 0.0)
    unresolved_model_findings = int(payload.get("unresolved_model_findings", 0) or 0)
    late_submission_exceptions = int(payload.get("late_submission_exceptions", 0) or 0)

    score = 100.0
    reasons = []
    alerts = []

    if stress_test_coverage < float(policy.get("minimum_stress_test_coverage", 0.95)):
        score -= round((float(policy.get("minimum_stress_test_coverage", 0.95)) - stress_test_coverage) * 100.0, 2)
        reasons.append("stress testing coverage is below policy")
        alerts.append("STRESS_TEST_COVERAGE_WEAK")
    if model_traceability_score < float(policy.get("minimum_model_traceability_score", 0.92)):
        score -= round((float(policy.get("minimum_model_traceability_score", 0.92)) - model_traceability_score) * 90.0, 2)
        reasons.append("model traceability is below institutional standard")
        alerts.append("MODEL_TRACEABILITY_WEAK")
    if submission_readiness_score < float(policy.get("minimum_submission_readiness_score", 0.94)):
        score -= round((float(policy.get("minimum_submission_readiness_score", 0.94)) - submission_readiness_score) * 90.0, 2)
        reasons.append("submission readiness is below filing threshold")
        alerts.append("SUBMISSION_READINESS_WEAK")
    if supervisory_challenge_response_score < float(policy.get("minimum_supervisory_challenge_response_score", 0.93)):
        score -= round((float(policy.get("minimum_supervisory_challenge_response_score", 0.93)) - supervisory_challenge_response_score) * 90.0, 2)
        reasons.append("supervisory challenge response score is below policy")
        alerts.append("SUPERVISORY_RESPONSE_WEAK")
    if unresolved_model_findings > 0:
        score -= min(unresolved_model_findings * 6.0, 24.0)
        reasons.append("unresolved model findings remain open")
        alerts.append("UNRESOLVED_MODEL_FINDINGS")
    if late_submission_exceptions > 0:
        score -= min(late_submission_exceptions * 5.0, 20.0)
        reasons.append("late submission exceptions remain on the calendar")
        alerts.append("LATE_SUBMISSION_EXCEPTIONS")

    capital_posture = str(ctx.get("capital_adequacy", {}).get("posture", "UNINITIALIZED"))
    liquidity_posture = str(ctx.get("liquidity_command", {}).get("posture", "UNINITIALIZED"))
    resolution_posture = str(ctx.get("resolution_control", {}).get("posture", "UNINITIALIZED"))
    simulation_posture = str(ctx.get("simulation_command", {}).get("posture", "UNINITIALIZED"))

    if policy.get("require_capital_adequacy_clear", True) and capital_posture not in {"CAPITAL_ADEQUACY_CLEAR", "EARLY_WARNING", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("capital adequacy posture is not submission-clear"); alerts.append("CAPITAL_ADEQUACY_NOT_CLEAR")
    if policy.get("require_liquidity_command_clear", True) and liquidity_posture not in {"LIQUIDITY_CLEAR", "CONTROLLED_STRESS", "UNINITIALIZED"}:
        score -= 10.0; reasons.append("liquidity command posture is not submission-clear"); alerts.append("LIQUIDITY_COMMAND_NOT_CLEAR")
    if policy.get("require_resolution_control_clear", True) and resolution_posture not in {"RESOLUTION_READY", "HEIGHTENED_RESOLUTION_WATCH", "UNINITIALIZED"}:
        score -= 10.0; reasons.append("resolution posture is not submission-clear"); alerts.append("RESOLUTION_CONTROL_NOT_CLEAR")
    if policy.get("require_simulation_command_clear", True) and simulation_posture not in {"SIMULATION_COMMAND_READY", "HEIGHTENED_SCENARIO_WATCH", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("simulation posture is not submission-clear"); alerts.append("SIMULATION_COMMAND_NOT_CLEAR")

    score = max(round(score, 2), 0.0)
    band = _band(score)
    posture = "SUPERVISORY_CHALLENGE_READY" if score >= float(policy.get("minimum_score", 96.0)) else ("HEIGHTENED_SUPERVISORY_WATCH" if score >= 92.0 else "REMEDIATION_REQUIRED")
    operator_review_required = posture != "SUPERVISORY_CHALLENGE_READY" or unresolved_model_findings > 0 or late_submission_exceptions > 0
    row = {
        "mission": "QNT30763",
        "evaluated_at": _now_iso(),
        "score": score,
        "band": band,
        "posture": posture,
        "operator_review_required": operator_review_required,
        "stress_test_coverage": stress_test_coverage,
        "model_traceability_score": model_traceability_score,
        "submission_readiness_score": submission_readiness_score,
        "supervisory_challenge_response_score": supervisory_challenge_response_score,
        "unresolved_model_findings": unresolved_model_findings,
        "late_submission_exceptions": late_submission_exceptions,
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


@router.post("/register-cycle")
def register_cycle(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "registered_at": _now_iso(),
        "cycle_code": payload.get("cycle_code", "ICAAP_2026_BASELINE"),
        "jurisdiction": payload.get("jurisdiction", "GLOBAL"),
        "cycle_type": payload.get("cycle_type", "ANNUAL_REGULATORY_STRESS_TEST"),
        "status": payload.get("status", "ACTIVE"),
    }
    _append(store, "cycles", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "cycle": row, "summary": _summary_for_email(email)}


@router.post("/stage-submission")
def stage_submission(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "staged_at": _now_iso(),
        "submission_code": payload.get("submission_code", "STRESS_TEST_PACK_2026Q4"),
        "cycle_code": payload.get("cycle_code", "ICAAP_2026_BASELINE"),
        "status": payload.get("status", "STAGED"),
        "evidence_pack_status": payload.get("evidence_pack_status", "ATTACHED"),
    }
    _append(store, "staged_submissions", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "staged_submission": row, "summary": _summary_for_email(email)}


@router.post("/record-supervisory-challenge")
def record_supervisory_challenge(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "recorded_at": _now_iso(),
        "challenge_code": payload.get("challenge_code", "SUPERVISORY_MODEL_OVERRIDE_QUERY"),
        "severity": payload.get("severity", "HIGH"),
        "owner": payload.get("owner", "stress-testing-office"),
        "status": payload.get("status", "OPEN"),
    }
    _append(store, "supervisory_challenges", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "supervisory_challenge": row, "summary": _summary_for_email(email)}


@router.post("/close-challenge")
def close_challenge(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "closed_at": _now_iso(),
        "challenge_code": payload.get("challenge_code", "SUPERVISORY_MODEL_OVERRIDE_QUERY"),
        "resolution": payload.get("resolution", "TRACEABILITY_EVIDENCE_ACCEPTED"),
        "status": payload.get("status", "CLOSED"),
    }
    _append(store, "closed_challenges", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "closed_challenge": row, "summary": _summary_for_email(email)}


@router.get("/policy")
def policy(user=Depends(_require_user)):
    return {"ok": True, "policy": _load(user["email"]).get("policy") or dict(DEFAULT_POLICY)}


@router.post("/bootstrap-demo")
def bootstrap_demo(user=Depends(_require_user)):
    email = user["email"]
    register_cycle({
        "cycle_code": "GLOBAL_STRESS_TEST_2026",
        "jurisdiction": "GLOBAL",
        "cycle_type": "SUPERVISORY_STRESS_TEST",
        "status": "ACTIVE",
    }, user)
    stage_submission({
        "submission_code": "GLOBAL_STRESS_TEST_PACK_2026",
        "cycle_code": "GLOBAL_STRESS_TEST_2026",
        "status": "STAGED",
        "evidence_pack_status": "ATTACHED",
    }, user)
    record_supervisory_challenge({
        "challenge_code": "MODEL_LOSS_PROJECTION_REVIEW",
        "severity": "HIGH",
        "owner": "stress-testing-office",
        "status": "OPEN",
    }, user)
    close_challenge({
        "challenge_code": "MODEL_LOSS_PROJECTION_REVIEW",
        "resolution": "MODEL_TRACEABILITY_AND_EVIDENCE_ACCEPTED",
        "status": "CLOSED",
    }, user)
    run = _evaluate(email, {
        "stress_test_coverage": 0.98,
        "model_traceability_score": 0.95,
        "submission_readiness_score": 0.96,
        "supervisory_challenge_response_score": 0.95,
        "unresolved_model_findings": 0,
        "late_submission_exceptions": 0,
    })
    return {"ok": True, "run": run, "summary": _summary_for_email(email)}
