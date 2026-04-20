from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(prefix="/api/regulatory-resolution-planning-wind-down-control-layer", tags=["regulatory-resolution-planning-wind-down-control-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "regulatory_resolution_planning_wind_down_control_layer"
DEFAULT_POLICY = {
    "retain_cycles": 180,
    "minimum_score": 96.0,
    "require_multi_jurisdiction_clear": True,
    "require_capital_adequacy_clear": True,
    "require_liquidity_command_clear": True,
    "require_breach_command_clear": True,
    "require_enforcement_command_clear": True,
    "minimum_resolution_plan_coverage": 0.95,
    "minimum_critical_function_mapping_coverage": 0.95,
    "minimum_wind_down_runway_days": 45,
    "minimum_funding_exit_readiness": 0.90,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _multi_jurisdiction():
    from backend.app import qnt30751_multi_jurisdiction_governance_layer_router as module
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


def _enforcement_command():
    from backend.app import qnt30758_regulatory_enforcement_response_consent_order_command_layer_router as module
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
            "resolution_plans": [],
            "critical_function_maps": [],
            "wind_down_reviews": [],
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
        "regulatory_resolution_planning_wind_down_control_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "resolution_plan_count": len(s.get("resolution_plans") or []),
            "critical_function_map_count": len(s.get("critical_function_maps") or []),
            "wind_down_review_count": len(s.get("wind_down_reviews") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "resolution_plans": s.get("resolution_plans") or [],
        "critical_function_maps": s.get("critical_function_maps") or [],
        "wind_down_reviews": s.get("wind_down_reviews") or [],
    }


def _cross_system_context(email: str) -> dict:
    return {
        "captured_at": _now_iso(),
        "multi_jurisdiction": (_multi_jurisdiction()._summary_for_email(email).get("multi_jurisdiction_governance_layer_status") or {}),
        "capital_adequacy": (_capital_adequacy()._summary_for_email(email).get("regulatory_capital_adequacy_surveillance_early_warning_layer_status") or {}),
        "liquidity_command": (_liquidity_command()._summary_for_email(email).get("regulatory_liquidity_stress_command_recovery_layer_status") or {}),
        "breach_command": (_breach_command()._summary_for_email(email).get("regulatory_breach_escalation_remediation_command_layer_status") or {}),
        "enforcement_command": (_enforcement_command()._summary_for_email(email).get("regulatory_enforcement_response_consent_order_command_layer_status") or {}),
    }


def _band(score: float) -> str:
    if score >= 98.0:
        return "RESOLUTION_READY"
    if score >= 96.0:
        return "CONTROLLED_WIND_DOWN_READY"
    if score >= 92.0:
        return "HEIGHTENED_RESOLUTION_WATCH"
    return "RESOLUTION_REMEDIATION_ACTIVE"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _cross_system_context(email)

    resolution_plan_coverage = float(payload.get("resolution_plan_coverage", 0.0) or 0.0)
    critical_function_mapping_coverage = float(payload.get("critical_function_mapping_coverage", 0.0) or 0.0)
    wind_down_runway_days = int(payload.get("wind_down_runway_days", 0) or 0)
    funding_exit_readiness = float(payload.get("funding_exit_readiness", 0.0) or 0.0)
    recovery_playbook_completeness = float(payload.get("recovery_playbook_completeness", 0.0) or 0.0)
    unresolved_resolution_blockers = int(payload.get("unresolved_resolution_blockers", 0) or 0)

    score = 100.0
    reasons = []
    alerts = []

    if resolution_plan_coverage < float(policy.get("minimum_resolution_plan_coverage", 0.95)):
        score -= round((float(policy.get("minimum_resolution_plan_coverage", 0.95)) - resolution_plan_coverage) * 100.0, 2)
        reasons.append("resolution plan coverage is below policy")
        alerts.append("RESOLUTION_PLAN_COVERAGE_WEAK")
    if critical_function_mapping_coverage < float(policy.get("minimum_critical_function_mapping_coverage", 0.95)):
        score -= round((float(policy.get("minimum_critical_function_mapping_coverage", 0.95)) - critical_function_mapping_coverage) * 90.0, 2)
        reasons.append("critical function mapping coverage is below policy")
        alerts.append("CRITICAL_FUNCTION_MAP_INCOMPLETE")
    if wind_down_runway_days < int(policy.get("minimum_wind_down_runway_days", 45)):
        score -= min((int(policy.get("minimum_wind_down_runway_days", 45)) - wind_down_runway_days) * 1.2, 24.0)
        reasons.append("wind-down runway is below policy")
        alerts.append("WIND_DOWN_RUNWAY_SHORT")
    if funding_exit_readiness < float(policy.get("minimum_funding_exit_readiness", 0.90)):
        score -= round((float(policy.get("minimum_funding_exit_readiness", 0.90)) - funding_exit_readiness) * 80.0, 2)
        reasons.append("funding exit readiness is below policy")
        alerts.append("FUNDING_EXIT_NOT_READY")
    if recovery_playbook_completeness < 0.90:
        score -= round((0.90 - recovery_playbook_completeness) * 70.0, 2)
        reasons.append("recovery and wind-down playbook completeness is below institutional standard")
        alerts.append("RECOVERY_PLAYBOOK_INCOMPLETE")
    if unresolved_resolution_blockers > 0:
        score -= min(unresolved_resolution_blockers * 7.0, 21.0)
        reasons.append("unresolved resolution blockers remain open")
        alerts.append("UNRESOLVED_RESOLUTION_BLOCKERS")

    governance_posture = str(ctx.get("multi_jurisdiction", {}).get("posture", "UNINITIALIZED"))
    capital_posture = str(ctx.get("capital_adequacy", {}).get("posture", "UNINITIALIZED"))
    liquidity_posture = str(ctx.get("liquidity_command", {}).get("posture", "UNINITIALIZED"))
    breach_posture = str(ctx.get("breach_command", {}).get("posture", "UNINITIALIZED"))
    enforcement_posture = str(ctx.get("enforcement_command", {}).get("posture", "UNINITIALIZED"))

    if policy.get("require_multi_jurisdiction_clear", True) and governance_posture not in {"GLOBAL_GOVERNANCE_CLEAR", "CONTROLLED_EXPANSION", "UNINITIALIZED"}:
        score -= 7.0; reasons.append("multi-jurisdiction governance posture is not resolution-clear"); alerts.append("MULTI_JURISDICTION_NOT_CLEAR")
    if policy.get("require_capital_adequacy_clear", True) and capital_posture not in {"CAPITAL_ADEQUACY_CLEAR", "EARLY_WARNING", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("capital adequacy posture is not resolution-clear"); alerts.append("CAPITAL_ADEQUACY_NOT_CLEAR")
    if policy.get("require_liquidity_command_clear", True) and liquidity_posture not in {"LIQUIDITY_CLEAR", "CONTROLLED_STRESS", "UNINITIALIZED"}:
        score -= 10.0; reasons.append("liquidity command posture is not resolution-clear"); alerts.append("LIQUIDITY_COMMAND_NOT_CLEAR")
    if policy.get("require_breach_command_clear", True) and breach_posture not in {"BREACH_COMMAND_CLEAR", "WATCH", "UNINITIALIZED"}:
        score -= 7.0; reasons.append("breach command posture is not resolution-clear"); alerts.append("BREACH_COMMAND_NOT_CLEAR")
    if policy.get("require_enforcement_command_clear", True) and enforcement_posture not in {"ENFORCEMENT_COMMAND_CLEAR", "CONTROLLED_RESPONSE", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("enforcement command posture is not resolution-clear"); alerts.append("ENFORCEMENT_COMMAND_NOT_CLEAR")

    score = max(round(score, 2), 0.0)
    band = _band(score)
    posture = "RESOLUTION_READY" if score >= float(policy.get("minimum_score", 96.0)) else ("HEIGHTENED_RESOLUTION_WATCH" if score >= 92.0 else "RESOLUTION_REMEDIATION_ACTIVE")
    operator_review_required = posture != "RESOLUTION_READY" or unresolved_resolution_blockers > 0
    row = {
        "mission": "QNT30761",
        "evaluated_at": _now_iso(),
        "score": score,
        "band": band,
        "posture": posture,
        "operator_review_required": operator_review_required,
        "resolution_plan_coverage": resolution_plan_coverage,
        "critical_function_mapping_coverage": critical_function_mapping_coverage,
        "wind_down_runway_days": wind_down_runway_days,
        "funding_exit_readiness": funding_exit_readiness,
        "recovery_playbook_completeness": recovery_playbook_completeness,
        "unresolved_resolution_blockers": unresolved_resolution_blockers,
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


@router.post("/register-resolution-plan")
def register_resolution_plan(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "registered_at": _now_iso(),
        "jurisdiction": payload.get("jurisdiction", "US"),
        "entity_scope": payload.get("entity_scope", "quantora-master"),
        "plan_version": payload.get("plan_version", "RWDP-1.0"),
        "status": payload.get("status", "CURRENT"),
    }
    _append(store, "resolution_plans", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "resolution_plan": row, "summary": _summary_for_email(email)}


@router.post("/map-critical-function")
def map_critical_function(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "mapped_at": _now_iso(),
        "function_code": payload.get("function_code", "EXECUTION_AND_CLEARING"),
        "dependency_owner": payload.get("dependency_owner", "operations-and-treasury"),
        "resolution_path": payload.get("resolution_path", "TRANSFER_OR_WIND_DOWN"),
        "status": payload.get("status", "MAPPED"),
    }
    _append(store, "critical_function_maps", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "critical_function_map": row, "summary": _summary_for_email(email)}


@router.post("/launch-wind-down-readiness-review")
def launch_wind_down_readiness_review(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "launched_at": _now_iso(),
        "review_code": payload.get("review_code", "ORDERLY_WIND_DOWN_QUARTERLY"),
        "owner": payload.get("owner", "resolution-office"),
        "target_state": payload.get("target_state", "RESOLUTION_READY"),
        "status": payload.get("status", "IN_PROGRESS"),
    }
    _append(store, "wind_down_reviews", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "wind_down_review": row, "summary": _summary_for_email(email)}


@router.get("/policy")
def policy(user=Depends(_require_user)):
    return {"ok": True, "policy": _load(user["email"]).get("policy") or dict(DEFAULT_POLICY)}


@router.post("/bootstrap-demo")
def bootstrap_demo(user=Depends(_require_user)):
    email = user["email"]
    register_resolution_plan({
        "jurisdiction": "US",
        "entity_scope": "quantora-master",
        "plan_version": "RWDP-1.0",
        "status": "CURRENT",
    }, user)
    map_critical_function({
        "function_code": "TREASURY_AND_EXECUTION",
        "dependency_owner": "operations-and-treasury",
        "resolution_path": "TRANSFER_OR_ORDERLY_WIND_DOWN",
        "status": "MAPPED",
    }, user)
    launch_wind_down_readiness_review({
        "review_code": "ORDERLY_WIND_DOWN_TABLETOP",
        "owner": "resolution-office",
        "target_state": "RESOLUTION_READY",
        "status": "TRACKING",
    }, user)
    run = _evaluate(email, {
        "resolution_plan_coverage": 0.98,
        "critical_function_mapping_coverage": 0.97,
        "wind_down_runway_days": 52,
        "funding_exit_readiness": 0.93,
        "recovery_playbook_completeness": 0.95,
        "unresolved_resolution_blockers": 0,
    })
    return {"ok": True, "run": run, "summary": _summary_for_email(email)}
