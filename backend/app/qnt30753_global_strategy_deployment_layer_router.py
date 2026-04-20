from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(prefix="/api/global-strategy-deployment-layer", tags=["global-strategy-deployment-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "global_strategy_deployment_layer"
DEFAULT_POLICY = {
    "retain_cycles": 180,
    "minimum_score": 96.0,
    "require_global_governance_clear": True,
    "require_capital_expansion_ready": True,
    "require_treasury_confirmed": True,
    "minimum_market_readiness_score": 0.985,
    "minimum_liquidity_assurance_score": 0.985,
    "minimum_execution_alignment_score": 0.98,
    "max_deployment_blocks": 0,
    "max_market_structure_gaps": 1,
}

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu
def _multi_jurisdiction():
    from backend.app import qnt30751_multi_jurisdiction_governance_layer_router as multi_jurisdiction
    return multi_jurisdiction
def _capital_expansion():
    from backend.app import qnt30752_institutional_capital_expansion_engine_router as capital_expansion
    return capital_expansion
def _treasury():
    from backend.app import qnt30745_institutional_treasury_confirmation_layer_router as treasury
    return treasury
def _audit_ready():
    from backend.app import qnt30747_institutional_audit_readiness_certification_layer_router as audit_ready
    return audit_ready
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
            "market_activations": [],
            "strategy_books": [],
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
        "global_strategy_deployment_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "market_activation_count": len(s.get("market_activations") or []),
            "strategy_book_count": len(s.get("strategy_books") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "market_activations": s.get("market_activations") or [],
        "strategy_books": s.get("strategy_books") or [],
    }

def _cross_system_context(email: str) -> dict:
    return {
        "captured_at": _now_iso(),
        "multi_jurisdiction": (_multi_jurisdiction()._summary_for_email(email).get("multi_jurisdiction_governance_layer_status") or {}),
        "capital_expansion": (_capital_expansion()._summary_for_email(email).get("institutional_capital_expansion_engine_status") or {}),
        "treasury": (_treasury()._summary_for_email(email).get("institutional_treasury_confirmation_layer_status") or {}),
        "audit_readiness": (_audit_ready()._summary_for_email(email).get("institutional_audit_readiness_certification_layer_status") or {}),
        "reporting": (_reporting()._summary_for_email(email).get("reporting_disclosure_automation_layer_status") or {}),
    }

def _band(score: float) -> str:
    if score >= 98.0:
        return "GLOBAL_DEPLOYMENT_CLEAR"
    if score >= 96.0:
        return "CONTROLLED_DEPLOYMENT"
    if score >= 92.0:
        return "MARKET_REVIEW"
    return "BLOCKED"

def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _cross_system_context(email)
    market_readiness_score = float(payload.get("market_readiness_score", 0.0) or 0.0)
    liquidity_assurance_score = float(payload.get("liquidity_assurance_score", 0.0) or 0.0)
    execution_alignment_score = float(payload.get("execution_alignment_score", 0.0) or 0.0)
    deployment_blocks = int(payload.get("deployment_blocks", 0) or 0)
    market_structure_gaps = int(payload.get("market_structure_gaps", 0) or 0)
    follow_the_sun_enabled = bool(payload.get("follow_the_sun_enabled", False))

    score = 100.0
    reasons = []
    alerts = []
    for val, threshold, mult, reason, code in [
        (market_readiness_score, float(policy.get("minimum_market_readiness_score", 0.985)), 130.0, "market readiness is below policy", "MARKET_READINESS_WEAK"),
        (liquidity_assurance_score, float(policy.get("minimum_liquidity_assurance_score", 0.985)), 120.0, "liquidity assurance is below policy", "LIQUIDITY_ASSURANCE_WEAK"),
        (execution_alignment_score, float(policy.get("minimum_execution_alignment_score", 0.98)), 110.0, "execution alignment is below policy", "EXECUTION_ALIGNMENT_WEAK"),
    ]:
        if val < threshold:
            score -= round((threshold - val) * mult, 2)
            reasons.append(reason)
            alerts.append(code)
    if deployment_blocks > int(policy.get("max_deployment_blocks", 0)):
        score -= min(deployment_blocks * 15.0, 30.0)
        reasons.append("deployment blocks remain open")
        alerts.append("DEPLOYMENT_BLOCK_OPEN")
    if market_structure_gaps > int(policy.get("max_market_structure_gaps", 1)):
        score -= min((market_structure_gaps - int(policy.get("max_market_structure_gaps", 1))) * 5.0, 20.0)
        reasons.append("market structure gaps exceed policy")
        alerts.append("MARKET_STRUCTURE_GAPS_HIGH")
    if not follow_the_sun_enabled:
        score -= 5.0
        reasons.append("follow-the-sun routing is not enabled")
        alerts.append("FOLLOW_THE_SUN_DISABLED")

    governance_posture = str(ctx.get("multi_jurisdiction", {}).get("posture", "UNINITIALIZED"))
    capital_posture = str(ctx.get("capital_expansion", {}).get("posture", "UNINITIALIZED"))
    treasury_posture = str(ctx.get("treasury", {}).get("posture", "UNINITIALIZED"))
    audit_posture = str(ctx.get("audit_readiness", {}).get("posture", "UNINITIALIZED"))
    reporting_posture = str(ctx.get("reporting", {}).get("posture", "UNINITIALIZED"))
    if policy.get("require_global_governance_clear", True) and governance_posture not in {"GLOBAL_GOVERNANCE_CLEAR", "CONTROLLED_EXPANSION", "UNINITIALIZED"}:
        score -= 10.0; reasons.append("global governance posture is not deployment clear"); alerts.append("GLOBAL_GOVERNANCE_NOT_CLEAR")
    if policy.get("require_capital_expansion_ready", True) and capital_posture not in {"ALLOCATOR_SCALE_READY", "CONTROLLED_EXPANSION", "UNINITIALIZED"}:
        score -= 10.0; reasons.append("capital expansion posture is not deployment clear"); alerts.append("CAPITAL_EXPANSION_NOT_CLEAR")
    if policy.get("require_treasury_confirmed", True) and treasury_posture not in {"CONFIRMED", "TREASURY_CONFIRMED", "TREASURY_CONTROLLED", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("treasury posture is not deployment clear"); alerts.append("TREASURY_NOT_CLEAR")
    if audit_posture not in {"AUDIT_READY", "MINOR_GAPS", "UNINITIALIZED"}:
        score -= 6.0; reasons.append("audit readiness posture is not deployment clear"); alerts.append("AUDIT_NOT_CLEAR")
    if reporting_posture not in {"AUTOMATED_CLEAR", "CONTROLLED", "APPROVED", "UNINITIALIZED"}:
        score -= 6.0; reasons.append("reporting posture is not deployment clear"); alerts.append("REPORTING_NOT_CLEAR")

    score = max(round(score, 2), 0.0)
    band = _band(score)
    posture = "GLOBAL_DEPLOYMENT_CLEAR" if score >= float(policy.get("minimum_score", 96.0)) else ("WATCH" if score >= 92.0 else "BLOCKED")
    operator_review_required = posture != "GLOBAL_DEPLOYMENT_CLEAR" or deployment_blocks > 0
    row = {
        "mission": "QNT30753",
        "evaluated_at": _now_iso(),
        "score": score,
        "band": band,
        "posture": posture,
        "operator_review_required": operator_review_required,
        "market_readiness_score": market_readiness_score,
        "liquidity_assurance_score": liquidity_assurance_score,
        "execution_alignment_score": execution_alignment_score,
        "deployment_blocks": deployment_blocks,
        "market_structure_gaps": market_structure_gaps,
        "follow_the_sun_enabled": follow_the_sun_enabled,
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

@router.post("/activate-market")
def activate_market(payload: dict = Body(default={}), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    row = {
        "at": _now_iso(),
        "market": str(payload.get("market") or "US Equities"),
        "venue": str(payload.get("venue") or "primary-routing"),
        "status": str(payload.get("status") or "active"),
    }
    _append(store, "market_activations", row, (store.get("policy") or {}).get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "market_activation": row, "summary": _summary_for_email(email)}

@router.post("/register-book")
def register_book(payload: dict = Body(default={}), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    row = {
        "at": _now_iso(),
        "strategy": str(payload.get("strategy") or "global-macro"),
        "region": str(payload.get("region") or "Global"),
        "status": str(payload.get("status") or "ready"),
    }
    _append(store, "strategy_books", row, (store.get("policy") or {}).get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "strategy_book": row, "summary": _summary_for_email(email)}

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
    activate_market({"market": "US Equities", "venue": "primary-routing", "status": "active"}, {"email": email})
    register_book({"strategy": "global-macro", "region": "Global", "status": "ready"}, {"email": email})
    _evaluate(email, {
        "market_readiness_score": 0.992,
        "liquidity_assurance_score": 0.989,
        "execution_alignment_score": 0.988,
        "deployment_blocks": 0,
        "market_structure_gaps": 1,
        "follow_the_sun_enabled": True,
    })
    return {"ok": True, "summary": _summary_for_email(email)}
