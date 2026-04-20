from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(prefix="/api/regulatory-capital-adequacy-surveillance-early-warning-layer", tags=["regulatory-capital-adequacy-surveillance-early-warning-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "regulatory_capital_adequacy_surveillance_early_warning_layer"
DEFAULT_POLICY = {
    "retain_cycles": 180,
    "minimum_score": 96.0,
    "require_multi_jurisdiction_clear": True,
    "require_capital_expansion_ready": True,
    "require_global_strategy_governed": True,
    "require_deadline_control_clear": True,
    "require_breach_command_clear": True,
    "require_enforcement_command_clear": True,
    "minimum_capital_ratio": 1.2,
    "minimum_liquidity_coverage_ratio": 1.15,
    "minimum_stress_buffer_ratio": 0.18,
    "max_warning_triggers": 0,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _multi_jurisdiction():
    from backend.app import qnt30751_multi_jurisdiction_governance_layer_router as module
    return module


def _capital_expansion():
    from backend.app import qnt30752_institutional_capital_expansion_engine_router as module
    return module


def _global_strategy():
    from backend.app import qnt30753_global_strategy_deployment_layer_router as module
    return module


def _deadline_control():
    from backend.app import qnt30756_regulatory_obligation_calendar_deadline_control_layer_router as module
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
            "snapshots": [],
            "warning_triggers": [],
            "capital_actions": [],
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
        "regulatory_capital_adequacy_surveillance_early_warning_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "snapshot_count": len(s.get("snapshots") or []),
            "warning_trigger_count": len(s.get("warning_triggers") or []),
            "capital_action_count": len(s.get("capital_actions") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "snapshots": s.get("snapshots") or [],
        "warning_triggers": s.get("warning_triggers") or [],
        "capital_actions": s.get("capital_actions") or [],
    }


def _cross_system_context(email: str) -> dict:
    return {
        "captured_at": _now_iso(),
        "multi_jurisdiction": (_multi_jurisdiction()._summary_for_email(email).get("multi_jurisdiction_governance_layer_status") or {}),
        "capital_expansion": (_capital_expansion()._summary_for_email(email).get("institutional_capital_expansion_engine_status") or {}),
        "global_strategy": (_global_strategy()._summary_for_email(email).get("global_strategy_deployment_layer_status") or {}),
        "deadline_control": (_deadline_control()._summary_for_email(email).get("regulatory_obligation_calendar_deadline_control_layer_status") or {}),
        "breach_command": (_breach_command()._summary_for_email(email).get("regulatory_breach_escalation_remediation_command_layer_status") or {}),
        "enforcement_command": (_enforcement_command()._summary_for_email(email).get("regulatory_enforcement_response_consent_order_command_layer_status") or {}),
    }


def _band(score: float) -> str:
    if score >= 98.0:
        return "CAPITAL_ADEQUACY_CLEAR"
    if score >= 96.0:
        return "CONTROLLED_CAPITAL_BUFFER"
    if score >= 92.0:
        return "EARLY_WARNING"
    return "CAPITAL_PRESSURE_ACTIVE"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _cross_system_context(email)
    capital_ratio = float(payload.get("capital_ratio", 0.0) or 0.0)
    liquidity_coverage_ratio = float(payload.get("liquidity_coverage_ratio", 0.0) or 0.0)
    stress_buffer_ratio = float(payload.get("stress_buffer_ratio", 0.0) or 0.0)
    warning_triggers = int(payload.get("warning_triggers", 0) or 0)
    unresolved_supervisory_actions = int(payload.get("unresolved_supervisory_actions", 0) or 0)
    capital_restriction_active = bool(payload.get("capital_restriction_active", False))

    score = 100.0
    reasons = []
    alerts = []
    checks = [
        (capital_ratio, float(policy.get("minimum_capital_ratio", 1.2)), 60.0, "capital ratio is below policy", "CAPITAL_RATIO_WEAK"),
        (liquidity_coverage_ratio, float(policy.get("minimum_liquidity_coverage_ratio", 1.15)), 70.0, "liquidity coverage ratio is below policy", "LIQUIDITY_COVERAGE_WEAK"),
        (stress_buffer_ratio, float(policy.get("minimum_stress_buffer_ratio", 0.18)), 120.0, "stress buffer ratio is below policy", "STRESS_BUFFER_WEAK"),
    ]
    for val, threshold, mult, reason, code in checks:
        if val < threshold:
            score -= round((threshold - val) * mult, 2)
            reasons.append(reason)
            alerts.append(code)
    if warning_triggers > int(policy.get("max_warning_triggers", 0)):
        score -= min(warning_triggers * 8.0, 24.0)
        reasons.append("warning triggers exceed policy")
        alerts.append("WARNING_TRIGGER_LIMIT_BREACH")
    if unresolved_supervisory_actions > 0:
        score -= min(unresolved_supervisory_actions * 7.0, 21.0)
        reasons.append("unresolved supervisory actions remain open")
        alerts.append("UNRESOLVED_SUPERVISORY_ACTIONS")
    if capital_restriction_active:
        score -= 14.0
        reasons.append("capital restriction is active")
        alerts.append("CAPITAL_RESTRICTION_ACTIVE")

    governance_posture = str(ctx.get("multi_jurisdiction", {}).get("posture", "UNINITIALIZED"))
    capital_expansion_posture = str(ctx.get("capital_expansion", {}).get("posture", "UNINITIALIZED"))
    strategy_posture = str(ctx.get("global_strategy", {}).get("posture", "UNINITIALIZED"))
    deadline_posture = str(ctx.get("deadline_control", {}).get("posture", "UNINITIALIZED"))
    breach_posture = str(ctx.get("breach_command", {}).get("posture", "UNINITIALIZED"))
    enforcement_posture = str(ctx.get("enforcement_command", {}).get("posture", "UNINITIALIZED"))

    if policy.get("require_multi_jurisdiction_clear", True) and governance_posture not in {"GLOBAL_GOVERNANCE_CLEAR", "CONTROLLED_EXPANSION", "UNINITIALIZED"}:
        score -= 7.0; reasons.append("multi-jurisdiction governance posture is not capital-clear"); alerts.append("MULTI_JURISDICTION_NOT_CLEAR")
    if policy.get("require_capital_expansion_ready", True) and capital_expansion_posture not in {"CAPITAL_EXPANSION_CLEAR", "CONTROLLED_SCALE", "UNINITIALIZED"}:
        score -= 7.0; reasons.append("capital expansion posture is not capital-clear"); alerts.append("CAPITAL_EXPANSION_NOT_CLEAR")
    if policy.get("require_global_strategy_governed", True) and strategy_posture not in {"GLOBAL_DEPLOYMENT_CLEAR", "CONTROLLED_EXPANSION", "UNINITIALIZED"}:
        score -= 7.0; reasons.append("global strategy deployment posture is not capital-clear"); alerts.append("GLOBAL_STRATEGY_NOT_CLEAR")
    if policy.get("require_deadline_control_clear", True) and deadline_posture not in {"DEADLINE_DISCIPLINE_CLEAR", "WATCH", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("deadline control posture is not capital-clear"); alerts.append("DEADLINE_CONTROL_NOT_CLEAR")
    if policy.get("require_breach_command_clear", True) and breach_posture not in {"BREACH_COMMAND_CLEAR", "WATCH", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("breach command posture is not capital-clear"); alerts.append("BREACH_COMMAND_NOT_CLEAR")
    if policy.get("require_enforcement_command_clear", True) and enforcement_posture not in {"ENFORCEMENT_COMMAND_CLEAR", "CONTROLLED_RESPONSE", "UNINITIALIZED"}:
        score -= 9.0; reasons.append("enforcement command posture is not capital-clear"); alerts.append("ENFORCEMENT_COMMAND_NOT_CLEAR")

    score = max(round(score, 2), 0.0)
    band = _band(score)
    posture = "CAPITAL_ADEQUACY_CLEAR" if score >= float(policy.get("minimum_score", 96.0)) else ("EARLY_WARNING" if score >= 92.0 else "CAPITAL_PRESSURE_ACTIVE")
    operator_review_required = posture != "CAPITAL_ADEQUACY_CLEAR" or warning_triggers > 0 or unresolved_supervisory_actions > 0 or capital_restriction_active
    row = {
        "mission": "QNT30759",
        "evaluated_at": _now_iso(),
        "score": score,
        "band": band,
        "posture": posture,
        "operator_review_required": operator_review_required,
        "capital_ratio": capital_ratio,
        "liquidity_coverage_ratio": liquidity_coverage_ratio,
        "stress_buffer_ratio": stress_buffer_ratio,
        "warning_triggers": warning_triggers,
        "unresolved_supervisory_actions": unresolved_supervisory_actions,
        "capital_restriction_active": capital_restriction_active,
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


@router.post("/record-snapshot")
def record_snapshot(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "recorded_at": _now_iso(),
        "jurisdiction": payload.get("jurisdiction", "US"),
        "entity_scope": payload.get("entity_scope", "quantora-master"),
        "capital_ratio": float(payload.get("capital_ratio", 1.26) or 0.0),
        "liquidity_coverage_ratio": float(payload.get("liquidity_coverage_ratio", 1.19) or 0.0),
        "stress_buffer_ratio": float(payload.get("stress_buffer_ratio", 0.22) or 0.0),
    }
    _append(store, "snapshots", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "snapshot": row, "summary": _summary_for_email(email)}


@router.post("/trigger-warning")
def trigger_warning(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "triggered_at": _now_iso(),
        "warning_code": payload.get("warning_code", "CAPITAL_BUFFER_COMPRESSION"),
        "severity": payload.get("severity", "HIGH"),
        "owner": payload.get("owner", "capital-committee"),
        "status": payload.get("status", "OPEN"),
    }
    _append(store, "warning_triggers", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "warning_trigger": row, "summary": _summary_for_email(email)}


@router.post("/launch-capital-action")
def launch_capital_action(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "launched_at": _now_iso(),
        "action_code": payload.get("action_code", "BUFFER_REPLENISHMENT_PROGRAM"),
        "action_owner": payload.get("action_owner", "treasury-and-risk"),
        "target_state": payload.get("target_state", "CAPITAL_ADEQUACY_CLEAR"),
        "status": payload.get("status", "IN_PROGRESS"),
    }
    _append(store, "capital_actions", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "capital_action": row, "summary": _summary_for_email(email)}


@router.get("/policy")
def policy(user=Depends(_require_user)):
    return {"ok": True, "policy": _load(user["email"]).get("policy") or dict(DEFAULT_POLICY)}


@router.post("/bootstrap-demo")
def bootstrap_demo(user=Depends(_require_user)):
    email = user["email"]
    record_snapshot({
        "jurisdiction": "US",
        "entity_scope": "quantora-master",
        "capital_ratio": 1.27,
        "liquidity_coverage_ratio": 1.18,
        "stress_buffer_ratio": 0.23,
    }, user)
    trigger_warning({
        "warning_code": "EARLY_WARNING_MONITOR_ENABLED",
        "severity": "MEDIUM",
        "owner": "capital-committee",
        "status": "TRACKING",
    }, user)
    launch_capital_action({
        "action_code": "CONTINGENT_BUFFER_REPLENISHMENT",
        "action_owner": "treasury-and-risk",
        "target_state": "CAPITAL_ADEQUACY_CLEAR",
        "status": "READY",
    }, user)
    run = _evaluate(email, {
        "capital_ratio": 1.27,
        "liquidity_coverage_ratio": 1.18,
        "stress_buffer_ratio": 0.23,
        "warning_triggers": 0,
        "unresolved_supervisory_actions": 0,
        "capital_restriction_active": False,
    })
    return {"ok": True, "run": run, "summary": _summary_for_email(email)}
