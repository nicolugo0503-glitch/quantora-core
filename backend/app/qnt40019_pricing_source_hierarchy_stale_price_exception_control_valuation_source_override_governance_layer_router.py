from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(
    prefix="/api/pricing-source-hierarchy-stale-price-exception-control-valuation-source-override-governance-layer",
    tags=["pricing-source-hierarchy-stale-price-exception-control-valuation-source-override-governance-layer"],
)

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "pricing_source_hierarchy_stale_price_exception_control_valuation_source_override_governance_layer"
DEFAULT_POLICY = {
    "retain_cycles": 365,
    "minimum_score": 96.0,
    "minimum_source_hierarchy_readiness": 0.97,
    "minimum_stale_price_exception_readiness": 0.97,
    "minimum_source_override_governance_readiness": 0.96,
    "maximum_stale_price_age_hours": 24.0,
    "maximum_open_source_exceptions": 0,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _require_user():
    return _mu()._require_session()


def _valuation_governance():
    from backend.app import qnt40017_independent_price_verification_valuation_committee_challenge_nav_fair_value_override_governance_layer_router as module
    return module


def _shadow_nav():
    from backend.app import qnt40018_administrator_shadow_nav_independent_nav_recalculation_nav_break_escalation_layer_router as module
    return module


def _nav():
    from backend.app import qnt30597_nav_strike_router as module
    return module


def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]


def _path(email: str) -> Path:
    ENGINE_DIR.mkdir(parents=True, exist_ok=True)
    return ENGINE_DIR / f"{_safe(email)}.json"


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
            "pricing_source_hierarchies": [],
            "stale_price_exceptions": [],
            "valuation_source_overrides": [],
            "latest_run": None,
            "last_context": {},
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))


def _save(email: str, data: dict):
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")


def _context(email: str) -> dict:
    valuation = _valuation_governance()._summary_for_email(email)
    shadow = _shadow_nav()._summary_for_email(email)
    nav = _nav().nav_strike_summary()
    latest_nav = nav.get("latest_valuation") or {}
    latest_val_run = valuation.get("latest_run") or {}
    latest_shadow_run = shadow.get("latest_run") or {}
    return {
        "captured_at": _now_iso(),
        "valuation_governance_summary": {
            "posture": ((valuation.get("independent_price_verification_valuation_committee_challenge_nav_fair_value_override_governance_layer_status") or {}).get("posture")),
            "score": latest_val_run.get("score"),
            "independent_price_verification_count": len(valuation.get("independent_price_verifications") or []),
            "fair_value_override_count": len(valuation.get("fair_value_overrides") or []),
        },
        "shadow_nav_summary": {
            "posture": ((shadow.get("administrator_shadow_nav_independent_nav_recalculation_nav_break_escalation_layer_status") or {}).get("posture")),
            "score": latest_shadow_run.get("score"),
            "administrator_shadow_nav_count": len(shadow.get("administrator_shadow_navs") or []),
            "nav_break_escalation_count": len(shadow.get("nav_break_escalations") or []),
        },
        "nav_summary": {
            "valuation_count": nav.get("valuation_count", 0),
            "official_count": nav.get("official_count", 0),
            "latest_valuation_id": latest_nav.get("valuation_id"),
            "latest_valuation_status": latest_nav.get("status"),
            "latest_official_nav": latest_nav.get("official_nav"),
            "latest_valuation_date": latest_nav.get("valuation_date"),
        },
    }


def _summary_for_email(email: str) -> dict:
    s = _load(email)
    latest = s.get("latest_run") or {}
    return {
        "pricing_source_hierarchy_stale_price_exception_control_valuation_source_override_governance_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "pricing_source_hierarchy_count": len(s.get("pricing_source_hierarchies") or []),
            "stale_price_exception_count": len(s.get("stale_price_exceptions") or []),
            "valuation_source_override_count": len(s.get("valuation_source_overrides") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "pricing_source_hierarchies": s.get("pricing_source_hierarchies") or [],
        "stale_price_exceptions": s.get("stale_price_exceptions") or [],
        "valuation_source_overrides": s.get("valuation_source_overrides") or [],
    }


def _band(score: float) -> str:
    if score >= 98.0:
        return "SOURCE_GOVERNANCE_STRONG"
    if score >= 96.0:
        return "SOURCE_GOVERNANCE_CLEAR"
    if score >= 92.0:
        return "SOURCE_GOVERNANCE_WATCH"
    return "SOURCE_GOVERNANCE_REMEDIATION_REQUIRED"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _context(email)

    source_hierarchy_readiness = float(payload.get("source_hierarchy_readiness", 0.0) or 0.0)
    stale_price_exception_readiness = float(payload.get("stale_price_exception_readiness", 0.0) or 0.0)
    source_override_governance_readiness = float(payload.get("source_override_governance_readiness", 0.0) or 0.0)
    stale_price_age_hours = float(payload.get("stale_price_age_hours", 0.0) or 0.0)
    open_source_exceptions = int(payload.get("open_source_exceptions", 0) or 0)

    score = 100.0
    reasons = []
    alerts = []

    def penalize(metric: float, minimum: float, weight: float, reason: str, code: str):
        nonlocal score
        if metric < minimum:
            score -= round((minimum - metric) * weight, 2)
            reasons.append(reason)
            alerts.append(code)

    penalize(source_hierarchy_readiness, float(policy.get("minimum_source_hierarchy_readiness", 0.97)), 120.0, "pricing source hierarchy readiness is below policy", "SOURCE_HIERARCHY_READINESS_WEAK")
    penalize(stale_price_exception_readiness, float(policy.get("minimum_stale_price_exception_readiness", 0.97)), 120.0, "stale price exception readiness is below policy", "STALE_PRICE_EXCEPTION_READINESS_WEAK")
    penalize(source_override_governance_readiness, float(policy.get("minimum_source_override_governance_readiness", 0.96)), 120.0, "valuation source override governance readiness is below policy", "SOURCE_OVERRIDE_GOVERNANCE_WEAK")

    max_age = float(policy.get("maximum_stale_price_age_hours", 24.0))
    if stale_price_age_hours > max_age:
        score -= 7.0 + (stale_price_age_hours - max_age) * 0.4
        reasons.append("stale price age exceeds policy")
        alerts.append("STALE_PRICE_AGE_EXCEEDS_POLICY")
    max_exceptions = int(policy.get("maximum_open_source_exceptions", 0))
    if open_source_exceptions > max_exceptions:
        score -= 8.0 + (open_source_exceptions - max_exceptions) * 2.0
        reasons.append("open source exceptions exceed policy")
        alerts.append("OPEN_SOURCE_EXCEPTIONS")

    valuation = ctx.get("valuation_governance_summary") or {}
    shadow = ctx.get("shadow_nav_summary") or {}
    nav = ctx.get("nav_summary") or {}

    if valuation.get("posture") not in {"FAIR_VALUE_GOVERNED", "VALUATION_CLEAR"}:
        score -= 8.0
        reasons.append("valuation governance posture must be clear before pricing source overrides are approved")
        alerts.append("VALUATION_GOVERNANCE_NOT_CLEAR")
    if valuation.get("independent_price_verification_count", 0) < 1:
        score -= 6.0
        reasons.append("independent price verification evidence is required before pricing source hierarchy governance")
        alerts.append("INDEPENDENT_PRICE_VERIFICATION_MISSING")
    if shadow.get("posture") not in {"NAV_BREAK_CONTROLLED", "NAV_CONTROL_CLEAR", "NAV_CONTROL_WATCH"}:
        score -= 6.0
        reasons.append("shadow nav control posture must be established before source overrides are governed")
        alerts.append("SHADOW_NAV_CONTROL_NOT_ESTABLISHED")
    if shadow.get("administrator_shadow_nav_count", 0) < 1:
        score -= 5.0
        reasons.append("administrator shadow nav evidence is required before stale price escalation")
        alerts.append("ADMINISTRATOR_SHADOW_NAV_MISSING")
    if nav.get("valuation_count", 0) < 1:
        score -= 6.0
        reasons.append("official nav valuation evidence is required")
        alerts.append("NAV_VALUATION_EVIDENCE_MISSING")
    if nav.get("latest_valuation_status") != "official":
        score -= 6.0
        reasons.append("latest nav valuation must be official before source hierarchy governance")
        alerts.append("LATEST_NAV_NOT_OFFICIAL")

    score = round(max(score, 0.0), 2)
    posture = _band(score)
    operator_review_required = bool(score < float(policy.get("minimum_score", 96.0)) or len(alerts) > 0)
    run = {
        "run_id": f"qnt40019_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "score": score,
        "band": posture,
        "posture": posture,
        "operator_review_required": operator_review_required,
        "reasons": reasons,
        "alerts": alerts,
        "source_hierarchy_readiness": source_hierarchy_readiness,
        "stale_price_exception_readiness": stale_price_exception_readiness,
        "source_override_governance_readiness": source_override_governance_readiness,
        "stale_price_age_hours": stale_price_age_hours,
        "open_source_exceptions": open_source_exceptions,
        "context": ctx,
    }
    _append(store, "runs", run, int(policy.get("retain_cycles", 365)))
    store["latest_run"] = run
    store["alerts"] = alerts
    store["last_context"] = ctx
    _save(email, store)
    return {"ok": True, **run}


@router.get('/summary')
def summary(user=Depends(_require_user)):
    return _summary_for_email(user["email"])


@router.post('/evaluate')
def evaluate(payload: dict = Body(...), user=Depends(_require_user)):
    return _evaluate(user["email"], payload or {})


@router.post('/record-pricing-source-hierarchy')
def record_pricing_source_hierarchy(payload: dict = Body(...), user=Depends(_require_user)):
    store = _load(user['email'])
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    event = {
        "recorded_at": _now_iso(),
        "hierarchy_name": payload.get('hierarchy_name', 'official-nav-primary-hierarchy'),
        "primary_source": payload.get('primary_source', 'independent_pricing_service'),
        "secondary_source": payload.get('secondary_source', 'administrator_shadow_nav'),
        "fallback_source": payload.get('fallback_source', 'valuation_committee_override'),
        "coverage_ratio": float(payload.get('coverage_ratio', 1.0) or 1.0),
        "approved_by": payload.get('approved_by', user.get('display_name') or user['email']),
    }
    _append(store, 'pricing_source_hierarchies', event, int(policy.get('retain_cycles', 365)))
    _save(user['email'], store)
    return {"ok": True, "event": event}


@router.post('/record-stale-price-exception')
def record_stale_price_exception(payload: dict = Body(...), user=Depends(_require_user)):
    store = _load(user['email'])
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    event = {
        "recorded_at": _now_iso(),
        "asset_id": payload.get('asset_id', 'POSITION-001'),
        "source_name": payload.get('source_name', 'independent_pricing_service'),
        "stale_hours": float(payload.get('stale_hours', 30.0) or 30.0),
        "exception_reason": payload.get('exception_reason', 'price_feed_not_refreshed_within_policy_window'),
        "escalation_status": payload.get('escalation_status', 'open'),
    }
    _append(store, 'stale_price_exceptions', event, int(policy.get('retain_cycles', 365)))
    _save(user['email'], store)
    return {"ok": True, "event": event}


@router.post('/issue-valuation-source-override')
def issue_valuation_source_override(payload: dict = Body(...), user=Depends(_require_user)):
    store = _load(user['email'])
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    event = {
        "recorded_at": _now_iso(),
        "asset_id": payload.get('asset_id', 'POSITION-001'),
        "from_source": payload.get('from_source', 'independent_pricing_service'),
        "to_source": payload.get('to_source', 'valuation_committee_override'),
        "override_reason": payload.get('override_reason', 'stale_price_exception_and_shadow_nav_variance_reviewed'),
        "approved_by": payload.get('approved_by', user.get('display_name') or user['email']),
        "governance_ticket": payload.get('governance_ticket', 'VAL-SRC-OVERRIDE-001'),
    }
    _append(store, 'valuation_source_overrides', event, int(policy.get('retain_cycles', 365)))
    _save(user['email'], store)
    return {"ok": True, "event": event}


@router.get('/policy')
def policy(user=Depends(_require_user)):
    store = _load(user['email'])
    return {"ok": True, "policy": {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}}


@router.post('/bootstrap-demo')
def bootstrap_demo(user=Depends(_require_user)):
    email = user['email']
    record_pricing_source_hierarchy({
        'hierarchy_name': 'official_nav_hierarchy',
        'primary_source': 'independent_pricing_service',
        'secondary_source': 'administrator_shadow_nav',
        'fallback_source': 'valuation_committee_override',
        'coverage_ratio': 0.99,
    }, user)
    record_stale_price_exception({
        'asset_id': 'POSITION-ALPHA',
        'source_name': 'independent_pricing_service',
        'stale_hours': 18.0,
        'exception_reason': 'overnight_vendor_hold_and_manual_review_required',
        'escalation_status': 'reviewed',
    }, user)
    issue_valuation_source_override({
        'asset_id': 'POSITION-ALPHA',
        'from_source': 'independent_pricing_service',
        'to_source': 'valuation_committee_override',
        'override_reason': 'approved after stale price review and shadow nav comparison',
        'governance_ticket': 'VAL-SRC-OVERRIDE-DEMO',
    }, user)
    latest_stale = (( _load(email).get('stale_price_exceptions') or [{}] )[0]) or {}
    result = _evaluate(email, {
        'source_hierarchy_readiness': 0.991,
        'stale_price_exception_readiness': 0.989,
        'source_override_governance_readiness': 0.987,
        'stale_price_age_hours': float(latest_stale.get('stale_hours', 18.0) or 18.0),
        'open_source_exceptions': 0 if latest_stale.get('escalation_status') in {'reviewed', 'closed'} else 1,
    })
    return {"ok": True, "result": result, "summary": _summary_for_email(email)}
