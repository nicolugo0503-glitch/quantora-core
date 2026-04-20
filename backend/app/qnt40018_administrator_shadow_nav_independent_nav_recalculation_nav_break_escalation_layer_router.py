from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(
    prefix="/api/administrator-shadow-nav-independent-nav-recalculation-nav-break-escalation-layer",
    tags=["administrator-shadow-nav-independent-nav-recalculation-nav-break-escalation-layer"],
)

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "administrator_shadow_nav_independent_nav_recalculation_nav_break_escalation_layer"
DEFAULT_POLICY = {
    "retain_cycles": 365,
    "minimum_score": 96.0,
    "minimum_shadow_nav_readiness": 0.97,
    "minimum_independent_recalculation_readiness": 0.97,
    "minimum_nav_break_escalation_readiness": 0.96,
    "maximum_nav_gap_bps": 5.0,
    "maximum_open_nav_breaks": 0,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _require_user():
    return _mu()._require_session()


def _valuation_governance():
    from backend.app import qnt40017_independent_price_verification_valuation_committee_challenge_nav_fair_value_override_governance_layer_router as module
    return module


def _official_books():
    from backend.app import qnt40016_fund_administrator_nav_package_approval_controller_sign_off_official_books_release_layer_router as module
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
            "administrator_shadow_navs": [],
            "independent_nav_recalculations": [],
            "nav_break_escalations": [],
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
    official = _official_books()._summary_for_email(email)
    nav = _nav().nav_strike_summary()
    latest_nav = nav.get("latest_valuation") or {}
    latest_run = (valuation.get("latest_run") or {})
    latest_official = (official.get("latest_run") or {})
    return {
        "captured_at": _now_iso(),
        "valuation_governance_summary": {
            "posture": ((valuation.get("independent_price_verification_valuation_committee_challenge_nav_fair_value_override_governance_layer_status") or {}).get("posture")),
            "score": latest_run.get("score"),
            "fair_value_override_count": len(valuation.get("fair_value_overrides") or []),
            "independent_price_verification_count": len(valuation.get("independent_price_verifications") or []),
        },
        "official_books_summary": {
            "posture": ((official.get("fund_administrator_nav_package_approval_controller_sign_off_official_books_release_layer_status") or {}).get("posture")),
            "score": latest_official.get("score"),
            "official_books_release_count": len(official.get("official_books_releases") or []),
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
        "administrator_shadow_nav_independent_nav_recalculation_nav_break_escalation_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "administrator_shadow_nav_count": len(s.get("administrator_shadow_navs") or []),
            "independent_nav_recalculation_count": len(s.get("independent_nav_recalculations") or []),
            "nav_break_escalation_count": len(s.get("nav_break_escalations") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "administrator_shadow_navs": s.get("administrator_shadow_navs") or [],
        "independent_nav_recalculations": s.get("independent_nav_recalculations") or [],
        "nav_break_escalations": s.get("nav_break_escalations") or [],
    }


def _band(score: float) -> str:
    if score >= 98.0:
        return "NAV_BREAK_CONTROLLED"
    if score >= 96.0:
        return "NAV_CONTROL_CLEAR"
    if score >= 92.0:
        return "NAV_CONTROL_WATCH"
    return "NAV_BREAK_REMEDIATION_REQUIRED"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _context(email)

    shadow_nav_readiness = float(payload.get("shadow_nav_readiness", 0.0) or 0.0)
    independent_recalculation_readiness = float(payload.get("independent_recalculation_readiness", 0.0) or 0.0)
    nav_break_escalation_readiness = float(payload.get("nav_break_escalation_readiness", 0.0) or 0.0)
    nav_gap_bps = float(payload.get("nav_gap_bps", 0.0) or 0.0)
    open_nav_breaks = int(payload.get("open_nav_breaks", 0) or 0)

    score = 100.0
    reasons = []
    alerts = []

    def penalize(metric: float, minimum: float, weight: float, reason: str, code: str):
        nonlocal score
        if metric < minimum:
            score -= round((minimum - metric) * weight, 2)
            reasons.append(reason)
            alerts.append(code)

    penalize(shadow_nav_readiness, float(policy.get("minimum_shadow_nav_readiness", 0.97)), 120.0, "administrator shadow nav readiness is below policy", "SHADOW_NAV_READINESS_WEAK")
    penalize(independent_recalculation_readiness, float(policy.get("minimum_independent_recalculation_readiness", 0.97)), 120.0, "independent nav recalculation readiness is below policy", "INDEPENDENT_RECALC_READINESS_WEAK")
    penalize(nav_break_escalation_readiness, float(policy.get("minimum_nav_break_escalation_readiness", 0.96)), 120.0, "nav break escalation readiness is below policy", "NAV_BREAK_ESCALATION_READINESS_WEAK")

    max_gap = float(policy.get("maximum_nav_gap_bps", 5.0))
    if nav_gap_bps > max_gap:
        score -= 7.0 + (nav_gap_bps - max_gap) * 1.5
        reasons.append("shadow nav and official nav gap exceeds policy")
        alerts.append("NAV_GAP_EXCEEDS_POLICY")
    max_breaks = int(policy.get("maximum_open_nav_breaks", 0))
    if open_nav_breaks > max_breaks:
        score -= 8.0 + (open_nav_breaks - max_breaks) * 2.0
        reasons.append("open nav breaks exceed policy")
        alerts.append("OPEN_NAV_BREAKS")

    valuation = ctx.get("valuation_governance_summary") or {}
    official = ctx.get("official_books_summary") or {}
    nav = ctx.get("nav_summary") or {}

    if valuation.get("posture") not in {"FAIR_VALUE_GOVERNED", "VALUATION_CLEAR"}:
        score -= 8.0
        reasons.append("valuation governance posture must be clear before shadow nav break escalation")
        alerts.append("VALUATION_GOVERNANCE_NOT_CLEAR")
    if valuation.get("independent_price_verification_count", 0) < 1:
        score -= 6.0
        reasons.append("independent price verification evidence is required before nav break escalation")
        alerts.append("INDEPENDENT_PRICE_VERIFICATION_MISSING")
    if official.get("posture") not in {"OFFICIAL_RELEASE_CLEAR", "OFFICIAL_BOOKS_RELEASED"}:
        score -= 6.0
        reasons.append("official books release posture must be clear before administrator shadow nav control")
        alerts.append("OFFICIAL_BOOKS_NOT_CLEAR")
    if official.get("official_books_release_count", 0) < 1:
        score -= 5.0
        reasons.append("official books release evidence is required for shadow nav control")
        alerts.append("OFFICIAL_BOOKS_RELEASE_EVIDENCE_MISSING")
    if nav.get("valuation_count", 0) < 1:
        score -= 6.0
        reasons.append("official nav valuation evidence is required")
        alerts.append("NAV_VALUATION_EVIDENCE_MISSING")
    if nav.get("latest_valuation_status") != "official":
        score -= 6.0
        reasons.append("latest nav valuation must be official before shadow nav comparison")
        alerts.append("LATEST_NAV_NOT_OFFICIAL")

    score = round(max(score, 0.0), 2)
    posture = _band(score)
    operator_review_required = bool(score < float(policy.get("minimum_score", 96.0)) or len(alerts) > 0)
    run = {
        "run_id": f"qnt40018_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "score": score,
        "band": posture,
        "posture": posture,
        "operator_review_required": operator_review_required,
        "reasons": reasons,
        "alerts": alerts,
        "shadow_nav_readiness": shadow_nav_readiness,
        "independent_recalculation_readiness": independent_recalculation_readiness,
        "nav_break_escalation_readiness": nav_break_escalation_readiness,
        "nav_gap_bps": nav_gap_bps,
        "open_nav_breaks": open_nav_breaks,
    }
    _append(store, "runs", run, int(policy.get("retain_cycles", 365)))
    store["latest_run"] = run
    store["alerts"] = alerts
    store["last_context"] = ctx
    _save(email, store)
    return run


@router.get('/summary')
def summary(user=Depends(_require_user)):
    return _summary_for_email((user.get('email') or '').strip().lower())


@router.post('/evaluate')
def evaluate(payload: dict = Body(...), user=Depends(_require_user)):
    email = (user.get('email') or '').strip().lower()
    return {"ok": True, "run": _evaluate(email, payload), "summary": _summary_for_email(email)}


@router.post('/record-administrator-shadow-nav')
def record_administrator_shadow_nav(payload: dict = Body(...), user=Depends(_require_user)):
    email = (user.get('email') or '').strip().lower()
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    nav = _nav().nav_strike_summary()
    latest = nav.get('latest_valuation') or {}
    official_nav = float(payload.get('official_nav') or latest.get('official_nav') or 0.0)
    shadow_nav = float(payload.get('shadow_nav') or official_nav)
    gap_bps = round((abs(shadow_nav - official_nav) / official_nav) * 10000.0, 4) if official_nav else 0.0
    event = {
        "shadow_nav_id": payload.get('shadow_nav_id') or f"shadnav_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "valuation_id": payload.get('valuation_id') or latest.get('valuation_id'),
        "official_nav": official_nav,
        "shadow_nav": shadow_nav,
        "nav_gap_bps": gap_bps,
        "status": payload.get('status') or ('matched' if gap_bps <= float(policy.get('maximum_nav_gap_bps', 5.0)) else 'break_detected'),
        "administrator": payload.get('administrator') or 'Independent Fund Administrator',
        "notes": payload.get('notes') or 'administrator shadow nav captured against official nav',
    }
    _append(store, 'administrator_shadow_navs', event, int(policy.get('retain_cycles', 365)))
    _save(email, store)
    return {"ok": True, "event": event, "summary": _summary_for_email(email)}


@router.post('/record-independent-nav-recalculation')
def record_independent_nav_recalculation(payload: dict = Body(...), user=Depends(_require_user)):
    email = (user.get('email') or '').strip().lower()
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    nav = _nav().nav_strike_summary()
    latest = nav.get('latest_valuation') or {}
    event = {
        "recalculation_id": payload.get('recalculation_id') or f"inr_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "valuation_id": payload.get('valuation_id') or latest.get('valuation_id'),
        "recalculated_nav": float(payload.get('recalculated_nav') or latest.get('official_nav') or 0.0),
        "status": payload.get('status') or 'completed',
        "reviewer": payload.get('reviewer') or user.get('display_name') or 'Quantora Controller',
        "notes": payload.get('notes') or 'independent nav recalculation completed for administrator challenge support',
    }
    _append(store, 'independent_nav_recalculations', event, int(policy.get('retain_cycles', 365)))
    _save(email, store)
    return {"ok": True, "event": event, "summary": _summary_for_email(email)}


@router.post('/escalate-nav-break')
def escalate_nav_break(payload: dict = Body(...), user=Depends(_require_user)):
    email = (user.get('email') or '').strip().lower()
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    latest_shadow = ((store.get('administrator_shadow_navs') or [None])[0]) or {}
    event = {
        "nav_break_id": payload.get('nav_break_id') or f"nbk_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "valuation_id": payload.get('valuation_id') or latest_shadow.get('valuation_id'),
        "severity": payload.get('severity') or ('critical' if float(latest_shadow.get('nav_gap_bps', 0.0) or 0.0) > float(policy.get('maximum_nav_gap_bps', 5.0)) else 'watch'),
        "status": payload.get('status') or 'escalated',
        "escalation_target": payload.get('escalation_target') or 'Quantora Valuation Committee and Controller',
        "notes": payload.get('notes') or 'nav break escalated for administrator-shadow-nav mismatch review',
    }
    _append(store, 'nav_break_escalations', event, int(policy.get('retain_cycles', 365)))
    _save(email, store)
    return {"ok": True, "event": event, "summary": _summary_for_email(email)}


@router.get('/policy')
def policy(user=Depends(_require_user)):
    email = (user.get('email') or '').strip().lower()
    store = _load(email)
    return {"ok": True, "policy": {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}}


@router.post('/bootstrap-demo')
def bootstrap_demo(user=Depends(_require_user)):
    email = (user.get('email') or '').strip().lower()
    session = dict(user)
    session.setdefault('logged_in', True)
    session.setdefault('is_admin', True)
    session.setdefault('display_name', 'Quantora Fund Administrator Oversight')
    from backend.app import main as app_main
    app_main.save_session(session)

    _valuation_governance().bootstrap_demo(user)
    nav = _nav().nav_strike_summary()
    latest = nav.get('latest_valuation') or {}
    official_nav = float(latest.get('official_nav') or 1000000.0)
    shadow_nav = round(official_nav * 0.9997, 2)
    record_administrator_shadow_nav({'official_nav': official_nav, 'shadow_nav': shadow_nav}, user)
    record_independent_nav_recalculation({'recalculated_nav': official_nav}, user)
    escalate_nav_break({'status': 'escalated', 'severity': 'watch'}, user)

    gap_bps = round((abs(shadow_nav - official_nav) / official_nav) * 10000.0, 4) if official_nav else 0.0
    run = _evaluate(email, {
        'shadow_nav_readiness': 0.99,
        'independent_recalculation_readiness': 0.99,
        'nav_break_escalation_readiness': 0.98,
        'nav_gap_bps': gap_bps,
        'open_nav_breaks': 0,
    })
    return {"ok": True, "run": run, "summary": _summary_for_email(email)}
