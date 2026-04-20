from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(
    prefix="/api/independent-price-verification-valuation-committee-challenge-nav-fair-value-override-governance-layer",
    tags=["independent-price-verification-valuation-committee-challenge-nav-fair-value-override-governance-layer"],
)

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "independent_price_verification_valuation_committee_challenge_nav_fair_value_override_governance_layer"
DEFAULT_POLICY = {
    "retain_cycles": 365,
    "minimum_score": 96.0,
    "minimum_independent_price_verification_readiness": 0.97,
    "minimum_committee_challenge_readiness": 0.96,
    "minimum_fair_value_override_governance_readiness": 0.97,
    "maximum_open_price_gaps": 0,
    "maximum_open_override_exceptions": 0,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _require_user():
    return _mu()._require_session()


def _official_books():
    from backend.app import qnt40016_fund_administrator_nav_package_approval_controller_sign_off_official_books_release_layer_router as module
    return module


def _nav():
    from backend.app import qnt30597_nav_strike_router as module
    return module


def _dealing():
    from backend.app import qnt30596_dealing_day_router as module
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
            "independent_price_verifications": [],
            "valuation_committee_challenges": [],
            "fair_value_overrides": [],
            "latest_run": None,
            "last_context": {},
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))


def _save(email: str, data: dict):
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")


def _context(email: str) -> dict:
    official = _official_books()._summary_for_email(email)
    nav = _nav().nav_strike_summary()
    dealing = _dealing().dealing_day_summary()
    latest_nav = nav.get("latest_valuation") or {}
    latest_day = (dealing.get("dealing_days") or [None])[0] or {}
    latest_run = official.get("latest_run") or {}
    return {
        "captured_at": _now_iso(),
        "official_books_summary": {
            "posture": ((official.get("fund_administrator_nav_package_approval_controller_sign_off_official_books_release_layer_status") or {}).get("posture")),
            "score": latest_run.get("score"),
            "official_books_release_count": len(official.get("official_books_releases") or []),
            "controller_sign_off_count": len(official.get("controller_sign_offs") or []),
        },
        "nav_summary": {
            "valuation_count": nav.get("valuation_count", 0),
            "official_count": nav.get("official_count", 0),
            "latest_valuation_id": latest_nav.get("valuation_id"),
            "latest_valuation_status": latest_nav.get("status"),
            "latest_official_nav": latest_nav.get("official_nav"),
            "latest_valuation_date": latest_nav.get("valuation_date"),
        },
        "dealing_summary": {
            "latest_day_id": latest_day.get("day_id"),
            "latest_cutoff_status": latest_day.get("cutoff_status"),
            "latest_status": latest_day.get("status"),
        },
    }


def _summary_for_email(email: str) -> dict:
    s = _load(email)
    latest = s.get("latest_run") or {}
    return {
        "independent_price_verification_valuation_committee_challenge_nav_fair_value_override_governance_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "independent_price_verification_count": len(s.get("independent_price_verifications") or []),
            "valuation_committee_challenge_count": len(s.get("valuation_committee_challenges") or []),
            "fair_value_override_count": len(s.get("fair_value_overrides") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "independent_price_verifications": s.get("independent_price_verifications") or [],
        "valuation_committee_challenges": s.get("valuation_committee_challenges") or [],
        "fair_value_overrides": s.get("fair_value_overrides") or [],
    }


def _band(score: float) -> str:
    if score >= 98.0:
        return "FAIR_VALUE_GOVERNED"
    if score >= 96.0:
        return "VALUATION_CLEAR"
    if score >= 92.0:
        return "VALUATION_WATCH"
    return "VALUATION_REMEDIATION_REQUIRED"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _context(email)

    independent_price_verification_readiness = float(payload.get("independent_price_verification_readiness", 0.0) or 0.0)
    committee_challenge_readiness = float(payload.get("committee_challenge_readiness", 0.0) or 0.0)
    fair_value_override_governance_readiness = float(payload.get("fair_value_override_governance_readiness", 0.0) or 0.0)
    open_price_gaps = int(payload.get("open_price_gaps", 0) or 0)
    open_override_exceptions = int(payload.get("open_override_exceptions", 0) or 0)

    score = 100.0
    reasons = []
    alerts = []

    def penalize(metric: float, minimum: float, weight: float, reason: str, code: str):
        nonlocal score
        if metric < minimum:
            score -= round((minimum - metric) * weight, 2)
            reasons.append(reason)
            alerts.append(code)

    penalize(independent_price_verification_readiness, float(policy.get("minimum_independent_price_verification_readiness", 0.97)), 120.0, "independent price verification readiness is below policy", "PRICE_VERIFICATION_READINESS_WEAK")
    penalize(committee_challenge_readiness, float(policy.get("minimum_committee_challenge_readiness", 0.96)), 120.0, "valuation committee challenge readiness is below policy", "VALUATION_CHALLENGE_READINESS_WEAK")
    penalize(fair_value_override_governance_readiness, float(policy.get("minimum_fair_value_override_governance_readiness", 0.97)), 120.0, "fair value override governance readiness is below policy", "FAIR_VALUE_OVERRIDE_GOVERNANCE_WEAK")

    max_price_gaps = int(policy.get("maximum_open_price_gaps", 0))
    if open_price_gaps > max_price_gaps:
        score -= 7.0 + (open_price_gaps - max_price_gaps) * 2.0
        reasons.append("open independent pricing gaps exceed policy")
        alerts.append("OPEN_PRICE_GAPS")
    max_override_ex = int(policy.get("maximum_open_override_exceptions", 0))
    if open_override_exceptions > max_override_ex:
        score -= 7.0 + (open_override_exceptions - max_override_ex) * 2.0
        reasons.append("open fair value override exceptions exceed policy")
        alerts.append("OPEN_OVERRIDE_EXCEPTIONS")

    official_books = ctx.get("official_books_summary") or {}
    nav_summary = ctx.get("nav_summary") or {}
    dealing_summary = ctx.get("dealing_summary") or {}

    if official_books.get("posture") not in {"OFFICIAL_RELEASE_CLEAR", "OFFICIAL_BOOKS_RELEASED"}:
        score -= 8.0
        reasons.append("official books release posture must be clear before valuation override governance")
        alerts.append("OFFICIAL_BOOKS_NOT_CLEAR")
    if official_books.get("official_books_release_count", 0) < 1:
        score -= 6.0
        reasons.append("official books release evidence is required before valuation governance")
        alerts.append("OFFICIAL_BOOKS_RELEASE_EVIDENCE_MISSING")
    if nav_summary.get("valuation_count", 0) < 1:
        score -= 6.0
        reasons.append("nav valuation evidence is required for independent pricing review")
        alerts.append("VALUATION_EVIDENCE_MISSING")
    if nav_summary.get("latest_valuation_status") != "official":
        score -= 6.0
        reasons.append("latest nav valuation must be official before fair value override governance")
        alerts.append("LATEST_VALUATION_NOT_OFFICIAL")
    if dealing_summary.get("latest_cutoff_status") not in {None, "locked", "complete", "cutoff_enforced"}:
        score -= 3.0
        reasons.append("dealing day cutoff posture is not aligned with valuation governance")
        alerts.append("DEALING_CUTOFF_MISALIGNED")

    score = round(max(score, 0.0), 2)
    posture = _band(score)
    operator_review_required = bool(score < float(policy.get("minimum_score", 96.0)) or len(alerts) > 0)
    run = {
        "run_id": f"qnt40017_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "score": score,
        "band": _band(score),
        "posture": posture,
        "operator_review_required": operator_review_required,
        "reasons": reasons,
        "alerts": alerts,
        "independent_price_verification_readiness": independent_price_verification_readiness,
        "committee_challenge_readiness": committee_challenge_readiness,
        "fair_value_override_governance_readiness": fair_value_override_governance_readiness,
        "open_price_gaps": open_price_gaps,
        "open_override_exceptions": open_override_exceptions,
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


@router.post('/record-independent-price-verification')
def record_independent_price_verification(payload: dict = Body(...), user=Depends(_require_user)):
    email = (user.get('email') or '').strip().lower()
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    nav = _nav().nav_strike_summary()
    latest = nav.get('latest_valuation') or {}
    event = {
        "verification_id": payload.get('verification_id') or f"ipv_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "valuation_id": payload.get('valuation_id') or latest.get('valuation_id'),
        "valuator": payload.get('valuator') or 'Independent Pricing Control',
        "status": payload.get('status') or 'verified',
        "price_gap_bps": float(payload.get('price_gap_bps', 0.0) or 0.0),
        "notes": payload.get('notes') or 'independent pricing sources reconciled to official valuation',
    }
    _append(store, 'independent_price_verifications', event, int(policy.get('retain_cycles', 365)))
    _save(email, store)
    return {"ok": True, "event": event, "summary": _summary_for_email(email)}


@router.post('/record-valuation-committee-challenge')
def record_valuation_committee_challenge(payload: dict = Body(...), user=Depends(_require_user)):
    email = (user.get('email') or '').strip().lower()
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    event = {
        "challenge_id": payload.get('challenge_id') or f"vcc_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "chair": payload.get('chair') or user.get('display_name') or 'Quantora Valuation Committee',
        "status": payload.get('status') or 'challenged_and_resolved',
        "issue": payload.get('issue') or 'level_3_asset_or_model_price_deviation',
        "notes": payload.get('notes') or 'valuation committee challenge logged with resolution evidence',
    }
    _append(store, 'valuation_committee_challenges', event, int(policy.get('retain_cycles', 365)))
    _save(email, store)
    return {"ok": True, "event": event, "summary": _summary_for_email(email)}


@router.post('/issue-fair-value-override')
def issue_fair_value_override(payload: dict = Body(...), user=Depends(_require_user)):
    email = (user.get('email') or '').strip().lower()
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    nav = _nav().nav_strike_summary()
    latest = nav.get('latest_valuation') or {}
    event = {
        "override_id": payload.get('override_id') or f"fvo_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "valuation_id": payload.get('valuation_id') or latest.get('valuation_id'),
        "override_reason": payload.get('override_reason') or 'fair_value_adjustment_required',
        "override_delta": float(payload.get('override_delta', 0.0) or 0.0),
        "approver": payload.get('approver') or user.get('display_name') or 'Quantora Valuation Committee',
        "status": payload.get('status') or 'approved',
        "notes": payload.get('notes') or 'fair value override approved under valuation governance policy',
    }
    _append(store, 'fair_value_overrides', event, int(policy.get('retain_cycles', 365)))
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
    session.setdefault('display_name', 'Quantora Valuation Committee Chair')
    from backend.app import main as app_main
    app_main.save_session(session)

    _official_books().bootstrap_demo(user)
    nav = _nav().nav_strike_summary()
    latest = nav.get('latest_valuation') or {}
    if latest.get('status') != 'official' and latest.get('valuation_id'):
        _nav().nav_strike_finalize({'email': email, 'valuation_id': latest.get('valuation_id'), 'notes': 'officialized for qnt40017 demo'})

    record_independent_price_verification({'status': 'verified', 'price_gap_bps': 2.1}, user)
    record_valuation_committee_challenge({'status': 'challenged_and_resolved'}, user)
    issue_fair_value_override({'status': 'approved', 'override_delta': 12500.0}, user)

    run = _evaluate(email, {
        'independent_price_verification_readiness': 0.99,
        'committee_challenge_readiness': 0.98,
        'fair_value_override_governance_readiness': 0.99,
        'open_price_gaps': 0,
        'open_override_exceptions': 0,
    })
    return {"ok": True, "run": run, "summary": _summary_for_email(email)}
