from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(prefix="/api/institutional-capital-expansion-engine", tags=["institutional-capital-expansion-engine"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "institutional_capital_expansion_engine"
DEFAULT_POLICY = {
    "retain_cycles": 180,
    "minimum_score": 96.0,
    "require_compliance_automation": True,
    "require_global_governance_clear": True,
    "require_investor_confirmed": True,
    "minimum_allocator_readiness_score": 0.985,
    "minimum_onboarding_capacity_score": 0.985,
    "minimum_distribution_confidence_score": 0.98,
    "max_kyc_backlog": 2,
    "max_capital_intake_blocks": 0,
}

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu
def _compliance_automation():
    from backend.app import qnt30750_regulatory_compliance_automation_layer_router as compliance_automation
    return compliance_automation
def _multi_jurisdiction():
    from backend.app import qnt30751_multi_jurisdiction_governance_layer_router as multi_jurisdiction
    return multi_jurisdiction
def _investor():
    from backend.app import qnt30746_institutional_investor_capital_confirmation_layer_router as investor
    return investor
def _delivery():
    from backend.app import qnt30704_investor_delivery_pack_system_router as delivery
    return delivery
def _reporting():
    from backend.app import qnt30715_reporting_disclosure_automation_layer_router as reporting
    return reporting


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
            "capital_lanes": [],
            "allocator_campaigns": [],
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
        "institutional_capital_expansion_engine_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "capital_lane_count": len(s.get("capital_lanes") or []),
            "allocator_campaign_count": len(s.get("allocator_campaigns") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "capital_lanes": s.get("capital_lanes") or [],
        "allocator_campaigns": s.get("allocator_campaigns") or [],
    }

def _cross_system_context(email: str) -> dict:
    return {
        "captured_at": _now_iso(),
        "compliance_automation": (_compliance_automation()._summary_for_email(email).get("regulatory_compliance_automation_layer_status") or {}),
        "multi_jurisdiction": (_multi_jurisdiction()._summary_for_email(email).get("multi_jurisdiction_governance_layer_status") or {}),
        "investor": (_investor()._summary_for_email(email).get("institutional_investor_capital_confirmation_layer_status") or {}),
        "delivery": (_delivery()._summary_for_email(email).get("status") or {}),
        "reporting": (_reporting()._summary_for_email(email).get("reporting_disclosure_automation_layer_status") or {}),
    }

def _band(score: float) -> str:
    if score >= 98.0:
        return "ALLOCATOR_SCALE_READY"
    if score >= 96.0:
        return "CONTROLLED_EXPANSION"
    if score >= 92.0:
        return "CAPACITY_REVIEW"
    return "BLOCKED"

def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _cross_system_context(email)
    allocator_readiness_score = float(payload.get("allocator_readiness_score", 0.0) or 0.0)
    onboarding_capacity_score = float(payload.get("onboarding_capacity_score", 0.0) or 0.0)
    distribution_confidence_score = float(payload.get("distribution_confidence_score", 0.0) or 0.0)
    kyc_backlog = int(payload.get("kyc_backlog", 0) or 0)
    capital_intake_blocks = int(payload.get("capital_intake_blocks", 0) or 0)
    investor_channel_live = bool(payload.get("investor_channel_live", False))

    score = 100.0
    reasons = []
    alerts = []
    for val, threshold, mult, reason, code in [
        (allocator_readiness_score, float(policy.get("minimum_allocator_readiness_score", 0.985)), 130.0, "allocator readiness is below policy", "ALLOCATOR_READINESS_WEAK"),
        (onboarding_capacity_score, float(policy.get("minimum_onboarding_capacity_score", 0.985)), 120.0, "onboarding capacity is below policy", "ONBOARDING_CAPACITY_WEAK"),
        (distribution_confidence_score, float(policy.get("minimum_distribution_confidence_score", 0.98)), 110.0, "distribution confidence is below policy", "DISTRIBUTION_CONFIDENCE_WEAK"),
    ]:
        if val < threshold:
            score -= round((threshold - val) * mult, 2)
            reasons.append(reason)
            alerts.append(code)
    if kyc_backlog > int(policy.get("max_kyc_backlog", 2)):
        score -= min((kyc_backlog - int(policy.get("max_kyc_backlog", 2))) * 5.0, 20.0)
        reasons.append("KYC backlog exceeds policy")
        alerts.append("KYC_BACKLOG_HIGH")
    if capital_intake_blocks > int(policy.get("max_capital_intake_blocks", 0)):
        score -= min(capital_intake_blocks * 15.0, 30.0)
        reasons.append("capital intake blocks remain open")
        alerts.append("CAPITAL_INTAKE_BLOCK_OPEN")
    if not investor_channel_live:
        score -= 5.0
        reasons.append("allocator channel is not live")
        alerts.append("ALLOCATOR_CHANNEL_OFFLINE")

    compliance_posture = str(ctx.get("compliance_automation", {}).get("posture", "UNINITIALIZED"))
    governance_posture = str(ctx.get("multi_jurisdiction", {}).get("posture", "UNINITIALIZED"))
    investor_posture = str(ctx.get("investor", {}).get("posture", "UNINITIALIZED"))
    reporting_posture = str(ctx.get("reporting", {}).get("posture", "UNINITIALIZED"))
    if policy.get("require_compliance_automation", True) and compliance_posture not in {"AUTOMATED_CLEAR", "CONTROLLED_AUTOMATION", "UNINITIALIZED"}:
        score -= 10.0; reasons.append("compliance automation posture is not allocator clear"); alerts.append("COMPLIANCE_AUTOMATION_NOT_CLEAR")
    if policy.get("require_global_governance_clear", True) and governance_posture not in {"GLOBAL_GOVERNANCE_CLEAR", "CONTROLLED_EXPANSION", "UNINITIALIZED"}:
        score -= 10.0; reasons.append("global governance posture is not allocator clear"); alerts.append("GLOBAL_GOVERNANCE_NOT_CLEAR")
    if policy.get("require_investor_confirmed", True) and investor_posture not in {"CONFIRMED", "FULLY_CONFIRMED", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("investor capital posture is not clear"); alerts.append("INVESTOR_NOT_CLEAR")
    if reporting_posture not in {"AUTOMATED_CLEAR", "CONTROLLED", "APPROVED", "UNINITIALIZED"}:
        score -= 6.0; reasons.append("reporting posture is not allocator clear"); alerts.append("REPORTING_NOT_CLEAR")

    score = max(round(score, 2), 0.0)
    band = _band(score)
    posture = "ALLOCATOR_SCALE_READY" if score >= float(policy.get("minimum_score", 96.0)) else ("WATCH" if score >= 92.0 else "BLOCKED")
    operator_review_required = posture != "ALLOCATOR_SCALE_READY" or capital_intake_blocks > 0
    row = {
        "mission": "QNT30752",
        "evaluated_at": _now_iso(),
        "score": score,
        "band": band,
        "posture": posture,
        "operator_review_required": operator_review_required,
        "allocator_readiness_score": allocator_readiness_score,
        "onboarding_capacity_score": onboarding_capacity_score,
        "distribution_confidence_score": distribution_confidence_score,
        "kyc_backlog": kyc_backlog,
        "capital_intake_blocks": capital_intake_blocks,
        "investor_channel_live": investor_channel_live,
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

@router.post("/open-capital-lane")
def open_capital_lane(payload: dict = Body(default={}), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    row = {
        "at": _now_iso(),
        "channel": str(payload.get("channel") or "family-office"),
        "target_region": str(payload.get("target_region") or "North America"),
        "status": str(payload.get("status") or "open"),
    }
    _append(store, "capital_lanes", row, (store.get("policy") or {}).get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "capital_lane": row, "summary": _summary_for_email(email)}

@router.post("/launch-campaign")
def launch_campaign(payload: dict = Body(default={}), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    row = {
        "at": _now_iso(),
        "campaign_name": str(payload.get("campaign_name") or "institutional-roadshow"),
        "allocator_type": str(payload.get("allocator_type") or "family-office"),
        "status": str(payload.get("status") or "launched"),
    }
    _append(store, "allocator_campaigns", row, (store.get("policy") or {}).get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "allocator_campaign": row, "summary": _summary_for_email(email)}

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
    open_capital_lane({"channel": "family-office", "target_region": "North America", "status": "open"}, {"email": email})
    launch_campaign({"campaign_name": "institutional-roadshow", "allocator_type": "family-office", "status": "launched"}, {"email": email})
    _evaluate(email, {
        "allocator_readiness_score": 0.992,
        "onboarding_capacity_score": 0.989,
        "distribution_confidence_score": 0.988,
        "kyc_backlog": 1,
        "capital_intake_blocks": 0,
        "investor_channel_live": True,
    })
    return {"ok": True, "summary": _summary_for_email(email)}
