from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(prefix="/api/multi-jurisdiction-governance-layer", tags=["multi-jurisdiction-governance-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "multi_jurisdiction_governance_layer"
DEFAULT_POLICY = {
    "retain_cycles": 180,
    "minimum_score": 96.0,
    "require_regulator_ready": True,
    "require_compliance_automation": True,
    "require_treasury_confirmed": True,
    "minimum_rulebook_coverage_score": 0.985,
    "minimum_cross_border_clearance_score": 0.985,
    "minimum_entity_governance_score": 0.98,
    "max_jurisdiction_conflicts": 1,
    "max_sanctions_exposure_flags": 0,
}

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu
def _regulator_readiness():
    from backend.app import qnt30749_institutional_regulator_readiness_interface_router as regulator_readiness
    return regulator_readiness
def _compliance_automation():
    from backend.app import qnt30750_regulatory_compliance_automation_layer_router as compliance_automation
    return compliance_automation
def _treasury():
    from backend.app import qnt30745_institutional_treasury_confirmation_layer_router as treasury
    return treasury
def _investor():
    from backend.app import qnt30746_institutional_investor_capital_confirmation_layer_router as investor
    return investor


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
            "jurisdiction_rules": [],
            "entity_clearances": [],
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
        "multi_jurisdiction_governance_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "jurisdiction_rule_count": len(s.get("jurisdiction_rules") or []),
            "entity_clearance_count": len(s.get("entity_clearances") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "jurisdiction_rules": s.get("jurisdiction_rules") or [],
        "entity_clearances": s.get("entity_clearances") or [],
    }

def _cross_system_context(email: str) -> dict:
    return {
        "captured_at": _now_iso(),
        "regulator_readiness": (_regulator_readiness()._summary_for_email(email).get("institutional_regulator_readiness_interface_status") or {}),
        "compliance_automation": (_compliance_automation()._summary_for_email(email).get("regulatory_compliance_automation_layer_status") or {}),
        "treasury": (_treasury()._summary_for_email(email).get("institutional_treasury_confirmation_layer_status") or {}),
        "investor": (_investor()._summary_for_email(email).get("institutional_investor_capital_confirmation_layer_status") or {}),
    }

def _band(score: float) -> str:
    if score >= 98.0:
        return "GLOBAL_GOVERNANCE_CLEAR"
    if score >= 96.0:
        return "CONTROLLED_EXPANSION"
    if score >= 92.0:
        return "JURISDICTION_REVIEW"
    return "BLOCKED"

def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _cross_system_context(email)
    rulebook_coverage_score = float(payload.get("rulebook_coverage_score", 0.0) or 0.0)
    cross_border_clearance_score = float(payload.get("cross_border_clearance_score", 0.0) or 0.0)
    entity_governance_score = float(payload.get("entity_governance_score", 0.0) or 0.0)
    jurisdiction_conflicts = int(payload.get("jurisdiction_conflicts", 0) or 0)
    sanctions_exposure_flags = int(payload.get("sanctions_exposure_flags", 0) or 0)
    capital_mobility_approved = bool(payload.get("capital_mobility_approved", False))

    score = 100.0
    reasons = []
    alerts = []
    for val, threshold, mult, reason, code in [
        (rulebook_coverage_score, float(policy.get("minimum_rulebook_coverage_score", 0.985)), 130.0, "jurisdiction rulebook coverage is below policy", "RULEBOOK_COVERAGE_WEAK"),
        (cross_border_clearance_score, float(policy.get("minimum_cross_border_clearance_score", 0.985)), 120.0, "cross-border clearance is below policy", "CROSS_BORDER_CLEARANCE_WEAK"),
        (entity_governance_score, float(policy.get("minimum_entity_governance_score", 0.98)), 110.0, "entity governance is below policy", "ENTITY_GOVERNANCE_WEAK"),
    ]:
        if val < threshold:
            score -= round((threshold - val) * mult, 2)
            reasons.append(reason)
            alerts.append(code)
    if jurisdiction_conflicts > int(policy.get("max_jurisdiction_conflicts", 1)):
        score -= min((jurisdiction_conflicts - int(policy.get("max_jurisdiction_conflicts", 1))) * 8.0, 24.0)
        reasons.append("jurisdiction conflicts exceed policy")
        alerts.append("JURISDICTION_CONFLICTS_HIGH")
    if sanctions_exposure_flags > int(policy.get("max_sanctions_exposure_flags", 0)):
        score -= min(sanctions_exposure_flags * 18.0, 36.0)
        reasons.append("sanctions exposure flags remain unresolved")
        alerts.append("SANCTIONS_EXPOSURE_OPEN")
    if not capital_mobility_approved:
        score -= 5.0
        reasons.append("capital mobility is not approved")
        alerts.append("CAPITAL_MOBILITY_NOT_APPROVED")

    regulator_posture = str(ctx.get("regulator_readiness", {}).get("posture", "UNINITIALIZED"))
    compliance_posture = str(ctx.get("compliance_automation", {}).get("posture", "UNINITIALIZED"))
    treasury_posture = str(ctx.get("treasury", {}).get("posture", "UNINITIALIZED"))
    investor_posture = str(ctx.get("investor", {}).get("posture", "UNINITIALIZED"))
    if policy.get("require_regulator_ready", True) and regulator_posture not in {"REGULATOR_READY", "UNINITIALIZED"}:
        score -= 10.0; reasons.append("regulator readiness posture is not clear"); alerts.append("REGULATOR_READINESS_NOT_CLEAR")
    if policy.get("require_compliance_automation", True) and compliance_posture not in {"AUTOMATED_CLEAR", "CONTROLLED_AUTOMATION", "UNINITIALIZED"}:
        score -= 10.0; reasons.append("compliance automation posture is not clear"); alerts.append("COMPLIANCE_AUTOMATION_NOT_CLEAR")
    if policy.get("require_treasury_confirmed", True) and treasury_posture not in {"CONFIRMED", "TREASURY_CONFIRMED", "TREASURY_CONTROLLED", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("treasury posture is not clear for cross-border governance"); alerts.append("TREASURY_NOT_CLEAR")
    if investor_posture not in {"CONFIRMED", "FULLY_CONFIRMED", "UNINITIALIZED"}:
        score -= 6.0; reasons.append("investor confirmation posture is not clear for cross-border governance"); alerts.append("INVESTOR_NOT_CLEAR")

    score = max(round(score, 2), 0.0)
    band = _band(score)
    posture = "GLOBAL_GOVERNANCE_CLEAR" if score >= float(policy.get("minimum_score", 96.0)) else ("WATCH" if score >= 92.0 else "BLOCKED")
    operator_review_required = posture != "GLOBAL_GOVERNANCE_CLEAR" or sanctions_exposure_flags > 0
    row = {
        "mission": "QNT30751",
        "evaluated_at": _now_iso(),
        "score": score,
        "band": band,
        "posture": posture,
        "operator_review_required": operator_review_required,
        "rulebook_coverage_score": rulebook_coverage_score,
        "cross_border_clearance_score": cross_border_clearance_score,
        "entity_governance_score": entity_governance_score,
        "jurisdiction_conflicts": jurisdiction_conflicts,
        "sanctions_exposure_flags": sanctions_exposure_flags,
        "capital_mobility_approved": capital_mobility_approved,
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

@router.post("/register-jurisdiction")
def register_jurisdiction(payload: dict = Body(default={}), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    row = {
        "at": _now_iso(),
        "jurisdiction": str(payload.get("jurisdiction") or "US"),
        "rulebook_version": str(payload.get("rulebook_version") or "v1"),
        "status": str(payload.get("status") or "active"),
    }
    _append(store, "jurisdiction_rules", row, (store.get("policy") or {}).get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "jurisdiction_rule": row, "summary": _summary_for_email(email)}

@router.post("/clear-entity")
def clear_entity(payload: dict = Body(default={}), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    row = {
        "at": _now_iso(),
        "entity_name": str(payload.get("entity_name") or "Quantora Global Fund SPC"),
        "jurisdiction": str(payload.get("jurisdiction") or "Cayman"),
        "status": str(payload.get("status") or "cleared"),
    }
    _append(store, "entity_clearances", row, (store.get("policy") or {}).get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "entity_clearance": row, "summary": _summary_for_email(email)}

@router.post("/policy")
def policy(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    store["policy"] = {**dict(DEFAULT_POLICY), **(store.get("policy") or {}), **payload}
    _save(email, store)
    return {"ok": True, "policy": store["policy"], "summary": _summary_for_email(email)}

@router.post("/bootstrap-demo")
def bootstrap_demo(user=Depends(_require_user)):
    email = user["email"]
    _load(email)
    register_jurisdiction({"jurisdiction": "US", "rulebook_version": "SEC-2026.1", "status": "active"}, {"email": email})
    clear_entity({"entity_name": "Quantora Global Master Fund", "jurisdiction": "Cayman", "status": "cleared"}, {"email": email})
    _evaluate(email, {
        "rulebook_coverage_score": 0.992,
        "cross_border_clearance_score": 0.989,
        "entity_governance_score": 0.988,
        "jurisdiction_conflicts": 1,
        "sanctions_exposure_flags": 0,
        "capital_mobility_approved": True,
    })
    return {"ok": True, "summary": _summary_for_email(email)}
