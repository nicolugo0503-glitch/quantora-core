from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(prefix="/api/recovery-resolution-scenario-simulation-command-layer", tags=["recovery-resolution-scenario-simulation-command-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "recovery_resolution_scenario_simulation_command_layer"
DEFAULT_POLICY = {
    "retain_cycles": 180,
    "minimum_score": 96.0,
    "require_resolution_control_clear": True,
    "require_capital_adequacy_clear": True,
    "require_liquidity_command_clear": True,
    "require_breach_command_clear": True,
    "minimum_scenario_coverage": 0.95,
    "minimum_transfer_readiness": 0.90,
    "minimum_recapitalization_readiness": 0.90,
    "minimum_operational_continuity_score": 0.92,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _resolution_control():
    from backend.app import qnt30761_regulatory_resolution_planning_wind_down_control_layer_router as module
    return module


def _capital_adequacy():
    from backend.app import qnt30759_regulatory_capital_adequacy_surveillance_early_warning_layer_router as module
    return module


def _liquidity_command():
    from backend.app import qnt30760_regulatory_liquidity_stress_command_recovery_layer_router as module
    return module


def _breach_command():
    from backend.app import qnt30757_regulatory_breach_escalation_remediation_command_layer_router as module
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
            "scenarios": [],
            "simulation_runs": [],
            "remediation_orders": [],
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
        "recovery_resolution_scenario_simulation_command_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "scenario_count": len(s.get("scenarios") or []),
            "simulation_run_count": len(s.get("simulation_runs") or []),
            "remediation_order_count": len(s.get("remediation_orders") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "scenarios": s.get("scenarios") or [],
        "simulation_runs": s.get("simulation_runs") or [],
        "remediation_orders": s.get("remediation_orders") or [],
    }


def _cross_system_context(email: str) -> dict:
    return {
        "captured_at": _now_iso(),
        "resolution_control": (_resolution_control()._summary_for_email(email).get("regulatory_resolution_planning_wind_down_control_layer_status") or {}),
        "capital_adequacy": (_capital_adequacy()._summary_for_email(email).get("regulatory_capital_adequacy_surveillance_early_warning_layer_status") or {}),
        "liquidity_command": (_liquidity_command()._summary_for_email(email).get("regulatory_liquidity_stress_command_recovery_layer_status") or {}),
        "breach_command": (_breach_command()._summary_for_email(email).get("regulatory_breach_escalation_remediation_command_layer_status") or {}),
    }


def _band(score: float) -> str:
    if score >= 98.0:
        return "SIMULATION_COMMAND_READY"
    if score >= 96.0:
        return "CONTROLLED_SIMULATION_READY"
    if score >= 92.0:
        return "HEIGHTENED_SCENARIO_WATCH"
    return "SCENARIO_REMEDIATION_ACTIVE"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _cross_system_context(email)

    scenario_coverage = float(payload.get("scenario_coverage", 0.0) or 0.0)
    transfer_readiness = float(payload.get("transfer_readiness", 0.0) or 0.0)
    recapitalization_readiness = float(payload.get("recapitalization_readiness", 0.0) or 0.0)
    operational_continuity_score = float(payload.get("operational_continuity_score", 0.0) or 0.0)
    unresolved_failure_points = int(payload.get("unresolved_failure_points", 0) or 0)
    severe_outcome_count = int(payload.get("severe_outcome_count", 0) or 0)

    score = 100.0
    reasons = []
    alerts = []

    if scenario_coverage < float(policy.get("minimum_scenario_coverage", 0.95)):
        score -= round((float(policy.get("minimum_scenario_coverage", 0.95)) - scenario_coverage) * 100.0, 2)
        reasons.append("scenario coverage is below policy")
        alerts.append("SCENARIO_COVERAGE_WEAK")
    if transfer_readiness < float(policy.get("minimum_transfer_readiness", 0.90)):
        score -= round((float(policy.get("minimum_transfer_readiness", 0.90)) - transfer_readiness) * 85.0, 2)
        reasons.append("transfer readiness is below policy")
        alerts.append("TRANSFER_READINESS_WEAK")
    if recapitalization_readiness < float(policy.get("minimum_recapitalization_readiness", 0.90)):
        score -= round((float(policy.get("minimum_recapitalization_readiness", 0.90)) - recapitalization_readiness) * 85.0, 2)
        reasons.append("recapitalization readiness is below policy")
        alerts.append("RECAPITALIZATION_READINESS_WEAK")
    if operational_continuity_score < float(policy.get("minimum_operational_continuity_score", 0.92)):
        score -= round((float(policy.get("minimum_operational_continuity_score", 0.92)) - operational_continuity_score) * 80.0, 2)
        reasons.append("operational continuity score is below institutional standard")
        alerts.append("OPERATIONAL_CONTINUITY_WEAK")
    if unresolved_failure_points > 0:
        score -= min(unresolved_failure_points * 6.0, 24.0)
        reasons.append("unresolved failure points remain in scenario pathways")
        alerts.append("UNRESOLVED_FAILURE_POINTS")
    if severe_outcome_count > 0:
        score -= min(severe_outcome_count * 5.0, 20.0)
        reasons.append("severe scenario outcomes remain unresolved")
        alerts.append("SEVERE_SCENARIO_OUTCOMES")

    resolution_posture = str(ctx.get("resolution_control", {}).get("posture", "UNINITIALIZED"))
    capital_posture = str(ctx.get("capital_adequacy", {}).get("posture", "UNINITIALIZED"))
    liquidity_posture = str(ctx.get("liquidity_command", {}).get("posture", "UNINITIALIZED"))
    breach_posture = str(ctx.get("breach_command", {}).get("posture", "UNINITIALIZED"))

    if policy.get("require_resolution_control_clear", True) and resolution_posture not in {"RESOLUTION_READY", "HEIGHTENED_RESOLUTION_WATCH", "UNINITIALIZED"}:
        score -= 10.0; reasons.append("resolution planning posture is not simulation-clear"); alerts.append("RESOLUTION_CONTROL_NOT_CLEAR")
    if policy.get("require_capital_adequacy_clear", True) and capital_posture not in {"CAPITAL_ADEQUACY_CLEAR", "EARLY_WARNING", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("capital adequacy posture is not simulation-clear"); alerts.append("CAPITAL_ADEQUACY_NOT_CLEAR")
    if policy.get("require_liquidity_command_clear", True) and liquidity_posture not in {"LIQUIDITY_CLEAR", "CONTROLLED_STRESS", "UNINITIALIZED"}:
        score -= 10.0; reasons.append("liquidity command posture is not simulation-clear"); alerts.append("LIQUIDITY_COMMAND_NOT_CLEAR")
    if policy.get("require_breach_command_clear", True) and breach_posture not in {"BREACH_COMMAND_CLEAR", "WATCH", "UNINITIALIZED"}:
        score -= 7.0; reasons.append("breach command posture is not simulation-clear"); alerts.append("BREACH_COMMAND_NOT_CLEAR")

    score = max(round(score, 2), 0.0)
    band = _band(score)
    posture = "SIMULATION_COMMAND_READY" if score >= float(policy.get("minimum_score", 96.0)) else ("HEIGHTENED_SCENARIO_WATCH" if score >= 92.0 else "SCENARIO_REMEDIATION_ACTIVE")
    operator_review_required = posture != "SIMULATION_COMMAND_READY" or unresolved_failure_points > 0 or severe_outcome_count > 0
    row = {
        "mission": "QNT30762",
        "evaluated_at": _now_iso(),
        "score": score,
        "band": band,
        "posture": posture,
        "operator_review_required": operator_review_required,
        "scenario_coverage": scenario_coverage,
        "transfer_readiness": transfer_readiness,
        "recapitalization_readiness": recapitalization_readiness,
        "operational_continuity_score": operational_continuity_score,
        "unresolved_failure_points": unresolved_failure_points,
        "severe_outcome_count": severe_outcome_count,
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


@router.post("/register-scenario")
def register_scenario(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "registered_at": _now_iso(),
        "scenario_code": payload.get("scenario_code", "RECOVERY_AND_RESOLUTION_DUAL_STRESS"),
        "scenario_type": payload.get("scenario_type", "JOINT_CAPITAL_LIQUIDITY_STRESS"),
        "jurisdiction": payload.get("jurisdiction", "GLOBAL"),
        "status": payload.get("status", "ACTIVE"),
    }
    _append(store, "scenarios", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "scenario": row, "summary": _summary_for_email(email)}


@router.post("/run-simulation")
def run_simulation(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "ran_at": _now_iso(),
        "simulation_code": payload.get("simulation_code", "WEEKEND_RESOLUTION_TABLETOP"),
        "scenario_code": payload.get("scenario_code", "RECOVERY_AND_RESOLUTION_DUAL_STRESS"),
        "outcome_band": payload.get("outcome_band", "CONTROLLED_TRANSFER"),
        "status": payload.get("status", "COMPLETED"),
    }
    _append(store, "simulation_runs", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "simulation_run": row, "summary": _summary_for_email(email)}


@router.post("/issue-remediation-order")
def issue_remediation_order(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "issued_at": _now_iso(),
        "order_code": payload.get("order_code", "SIMULATION_GAP_REMEDIATION_01"),
        "owner": payload.get("owner", "resolution-office"),
        "priority": payload.get("priority", "HIGH"),
        "status": payload.get("status", "OPEN"),
    }
    _append(store, "remediation_orders", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "remediation_order": row, "summary": _summary_for_email(email)}


@router.get("/policy")
def policy(user=Depends(_require_user)):
    return {"ok": True, "policy": _load(user["email"]).get("policy") or dict(DEFAULT_POLICY)}


@router.post("/bootstrap-demo")
def bootstrap_demo(user=Depends(_require_user)):
    email = user["email"]
    register_scenario({
        "scenario_code": "GLOBAL_RECOVERY_RESOLUTION_DUAL_STRESS",
        "scenario_type": "CAPITAL_LIQUIDITY_AND_OPERATIONAL_STRESS",
        "jurisdiction": "GLOBAL",
        "status": "ACTIVE",
    }, user)
    run_simulation({
        "simulation_code": "RESOLUTION_WEEKEND_TABLETOP",
        "scenario_code": "GLOBAL_RECOVERY_RESOLUTION_DUAL_STRESS",
        "outcome_band": "CONTROLLED_TRANSFER",
        "status": "COMPLETED",
    }, user)
    issue_remediation_order({
        "order_code": "SIMULATION_CONTINUITY_HARDENING",
        "owner": "resolution-office",
        "priority": "HIGH",
        "status": "TRACKING",
    }, user)
    run = _evaluate(email, {
        "scenario_coverage": 0.97,
        "transfer_readiness": 0.94,
        "recapitalization_readiness": 0.93,
        "operational_continuity_score": 0.95,
        "unresolved_failure_points": 0,
        "severe_outcome_count": 0,
    })
    return {"ok": True, "run": run, "summary": _summary_for_email(email)}
