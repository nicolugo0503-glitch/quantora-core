from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(
    prefix="/api/valuation-committee-minutes-challenge-resolution-evidence-final-nav-governance-record-layer",
    tags=["valuation-committee-minutes-challenge-resolution-evidence-final-nav-governance-record-layer"],
)

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "valuation_committee_minutes_challenge_resolution_evidence_final_nav_governance_record_layer"
DEFAULT_POLICY = {
    "retain_cycles": 365,
    "minimum_score": 96.0,
    "minimum_minutes_readiness": 0.97,
    "minimum_challenge_resolution_readiness": 0.97,
    "minimum_final_record_readiness": 0.96,
    "maximum_open_challenges": 0,
    "maximum_unlinked_evidence_gaps": 0,
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


def _source_governance():
    from backend.app import qnt40019_pricing_source_hierarchy_stale_price_exception_control_valuation_source_override_governance_layer_router as module
    return module


def _official_books():
    from backend.app import qnt40016_fund_administrator_nav_package_approval_controller_sign_off_official_books_release_layer_router as module
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
            "valuation_committee_minutes": [],
            "challenge_resolution_evidence": [],
            "final_nav_governance_records": [],
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
    source = _source_governance()._summary_for_email(email)
    books = _official_books()._summary_for_email(email)
    latest_val = valuation.get("latest_run") or {}
    latest_shadow = shadow.get("latest_run") or {}
    latest_source = source.get("latest_run") or {}
    latest_books = books.get("latest_run") or {}
    return {
        "captured_at": _now_iso(),
        "valuation_governance_summary": {
            "posture": ((valuation.get("independent_price_verification_valuation_committee_challenge_nav_fair_value_override_governance_layer_status") or {}).get("posture")),
            "score": latest_val.get("score"),
            "challenge_count": len(valuation.get("valuation_committee_challenges") or []),
            "override_count": len(valuation.get("fair_value_overrides") or []),
        },
        "shadow_nav_summary": {
            "posture": ((shadow.get("administrator_shadow_nav_independent_nav_recalculation_nav_break_escalation_layer_status") or {}).get("posture")),
            "score": latest_shadow.get("score"),
            "break_count": len(shadow.get("nav_break_escalations") or []),
        },
        "source_governance_summary": {
            "posture": ((source.get("pricing_source_hierarchy_stale_price_exception_control_valuation_source_override_governance_layer_status") or {}).get("posture")),
            "score": latest_source.get("score"),
            "source_override_count": len(source.get("valuation_source_overrides") or []),
            "open_source_alerts": len(source.get("alerts") or []),
        },
        "official_books_summary": {
            "posture": ((books.get("fund_administrator_nav_package_approval_controller_sign_off_official_books_release_layer_status") or {}).get("posture")),
            "score": latest_books.get("score"),
        },
    }


def _summary_for_email(email: str) -> dict:
    s = _load(email)
    latest = s.get("latest_run") or {}
    return {
        "valuation_committee_minutes_challenge_resolution_evidence_final_nav_governance_record_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "minutes_count": len(s.get("valuation_committee_minutes") or []),
            "challenge_resolution_evidence_count": len(s.get("challenge_resolution_evidence") or []),
            "final_nav_governance_record_count": len(s.get("final_nav_governance_records") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "valuation_committee_minutes": s.get("valuation_committee_minutes") or [],
        "challenge_resolution_evidence": s.get("challenge_resolution_evidence") or [],
        "final_nav_governance_records": s.get("final_nav_governance_records") or [],
    }


def _band(score: float) -> str:
    if score >= 98.0:
        return "FINAL_NAV_GOVERNANCE_STRONG"
    if score >= 96.0:
        return "FINAL_NAV_GOVERNANCE_CLEAR"
    if score >= 92.0:
        return "FINAL_NAV_GOVERNANCE_WATCH"
    return "FINAL_NAV_GOVERNANCE_REMEDIATION_REQUIRED"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _context(email)

    minutes_readiness = float(payload.get("minutes_readiness", 0.0) or 0.0)
    challenge_resolution_readiness = float(payload.get("challenge_resolution_readiness", 0.0) or 0.0)
    final_record_readiness = float(payload.get("final_record_readiness", 0.0) or 0.0)
    open_challenges = int(payload.get("open_challenges", 0) or 0)
    unlinked_evidence_gaps = int(payload.get("unlinked_evidence_gaps", 0) or 0)

    score = 100.0
    reasons = []
    alerts = []

    def penalize(metric: float, minimum: float, weight: float, reason: str, code: str):
        nonlocal score
        if metric < minimum:
            score -= round((minimum - metric) * weight, 2)
            reasons.append(reason)
            alerts.append(code)

    penalize(minutes_readiness, float(policy.get("minimum_minutes_readiness", 0.97)), 120.0, "valuation committee minutes readiness is below policy", "MINUTES_READINESS_WEAK")
    penalize(challenge_resolution_readiness, float(policy.get("minimum_challenge_resolution_readiness", 0.97)), 120.0, "challenge resolution evidence readiness is below policy", "CHALLENGE_RESOLUTION_READINESS_WEAK")
    penalize(final_record_readiness, float(policy.get("minimum_final_record_readiness", 0.96)), 120.0, "final nav governance record readiness is below policy", "FINAL_RECORD_READINESS_WEAK")

    max_open = int(policy.get("maximum_open_challenges", 0))
    if open_challenges > max_open:
        score -= 8.0 + (open_challenges - max_open) * 2.0
        reasons.append("open valuation challenges exceed policy")
        alerts.append("OPEN_CHALLENGES")

    max_gaps = int(policy.get("maximum_unlinked_evidence_gaps", 0))
    if unlinked_evidence_gaps > max_gaps:
        score -= 8.0 + (unlinked_evidence_gaps - max_gaps) * 2.0
        reasons.append("unlinked evidence gaps exceed policy")
        alerts.append("UNLINKED_EVIDENCE_GAPS")

    valuation = ctx.get("valuation_governance_summary") or {}
    shadow = ctx.get("shadow_nav_summary") or {}
    source = ctx.get("source_governance_summary") or {}
    books = ctx.get("official_books_summary") or {}

    if valuation.get("posture") not in {"FAIR_VALUE_GOVERNED", "VALUATION_CLEAR"}:
        score -= 8.0
        reasons.append("valuation governance posture must be clear before final nav governance record approval")
        alerts.append("VALUATION_GOVERNANCE_NOT_CLEAR")
    if valuation.get("challenge_count", 0) < 1:
        score -= 6.0
        reasons.append("valuation committee challenge evidence is required before committee minutes are finalized")
        alerts.append("VALUATION_CHALLENGE_EVIDENCE_MISSING")
    if shadow.get("posture") not in {"NAV_BREAK_CONTROLLED", "NAV_CONTROL_CLEAR", "NAV_CONTROL_WATCH"}:
        score -= 6.0
        reasons.append("shadow nav posture must be established before final nav governance is recorded")
        alerts.append("SHADOW_NAV_POSTURE_NOT_ESTABLISHED")
    if source.get("posture") not in {"SOURCE_GOVERNANCE_STRONG", "SOURCE_GOVERNANCE_CLEAR", "SOURCE_GOVERNANCE_WATCH"}:
        score -= 6.0
        reasons.append("pricing source governance posture must be established before final nav governance is recorded")
        alerts.append("SOURCE_GOVERNANCE_NOT_ESTABLISHED")
    if source.get("source_override_count", 0) < 1:
        score -= 5.0
        reasons.append("source override or override review evidence is required before final record issuance")
        alerts.append("SOURCE_OVERRIDE_EVIDENCE_MISSING")
    if books.get("posture") not in {"OFFICIAL_BOOKS_RELEASE_READY", "OFFICIAL_BOOKS_CLEAR"}:
        score -= 7.0
        reasons.append("official books release posture must be clear before final nav governance record issuance")
        alerts.append("OFFICIAL_BOOKS_POSTURE_NOT_CLEAR")

    score = round(max(score, 0.0), 2)
    posture = _band(score)
    operator_review_required = bool(score < float(policy.get("minimum_score", 96.0)) or len(alerts) > 0)
    run = {
        "run_id": f"qnt40020_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "score": score,
        "band": posture,
        "posture": posture,
        "operator_review_required": operator_review_required,
        "reasons": reasons,
        "alerts": alerts,
        "minutes_readiness": minutes_readiness,
        "challenge_resolution_readiness": challenge_resolution_readiness,
        "final_record_readiness": final_record_readiness,
        "open_challenges": open_challenges,
        "unlinked_evidence_gaps": unlinked_evidence_gaps,
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


@router.post('/record-valuation-committee-minutes')
def record_valuation_committee_minutes(payload: dict = Body(...), user=Depends(_require_user)):
    store = _load(user['email'])
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    event = {
        "recorded_at": _now_iso(),
        "meeting_id": payload.get('meeting_id', 'VAL-COMMITTEE-001'),
        "meeting_date": payload.get('meeting_date', _now_iso()[:10]),
        "chair": payload.get('chair', user.get('display_name') or user['email']),
        "minutes_hash": payload.get('minutes_hash', 'minutes_hash_demo_001'),
        "challenge_topics": payload.get('challenge_topics', ['pricing-source-hierarchy', 'fair-value-override']),
    }
    _append(store, 'valuation_committee_minutes', event, int(policy.get('retain_cycles', 365)))
    _save(user['email'], store)
    return {"ok": True, "event": event}


@router.post('/record-challenge-resolution-evidence')
def record_challenge_resolution_evidence(payload: dict = Body(...), user=Depends(_require_user)):
    store = _load(user['email'])
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    event = {
        "recorded_at": _now_iso(),
        "challenge_id": payload.get('challenge_id', 'VAL-CHALLENGE-001'),
        "resolution_status": payload.get('resolution_status', 'resolved'),
        "evidence_packet_id": payload.get('evidence_packet_id', 'VAL-EVID-001'),
        "reviewed_by": payload.get('reviewed_by', user.get('display_name') or user['email']),
        "linked_override_ticket": payload.get('linked_override_ticket', 'VAL-SRC-OVERRIDE-DEMO'),
    }
    _append(store, 'challenge_resolution_evidence', event, int(policy.get('retain_cycles', 365)))
    _save(user['email'], store)
    return {"ok": True, "event": event}


@router.post('/issue-final-nav-governance-record')
def issue_final_nav_governance_record(payload: dict = Body(...), user=Depends(_require_user)):
    store = _load(user['email'])
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    event = {
        "recorded_at": _now_iso(),
        "record_id": payload.get('record_id', 'FINAL-NAV-GOV-001'),
        "nav_cycle_id": payload.get('nav_cycle_id', 'NAV-CYCLE-001'),
        "committee_minutes_id": payload.get('committee_minutes_id', 'VAL-COMMITTEE-001'),
        "official_books_reference": payload.get('official_books_reference', 'BOOKS-REL-001'),
        "approved_by": payload.get('approved_by', user.get('display_name') or user['email']),
    }
    _append(store, 'final_nav_governance_records', event, int(policy.get('retain_cycles', 365)))
    _save(user['email'], store)
    return {"ok": True, "event": event}


@router.get('/policy')
def policy(user=Depends(_require_user)):
    store = _load(user['email'])
    return {"ok": True, "policy": {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}}


@router.post('/bootstrap-demo')
def bootstrap_demo(user=Depends(_require_user)):
    email = user['email']
    record_valuation_committee_minutes({
        'meeting_id': 'VAL-COMMITTEE-DEMO',
        'meeting_date': _now_iso()[:10],
        'minutes_hash': 'minutes_hash_demo_final_nav_001',
        'challenge_topics': ['shadow-nav-break', 'source-override-review'],
    }, user)
    record_challenge_resolution_evidence({
        'challenge_id': 'VAL-CHALLENGE-DEMO',
        'resolution_status': 'resolved',
        'evidence_packet_id': 'VAL-EVID-DEMO',
        'linked_override_ticket': 'VAL-SRC-OVERRIDE-DEMO',
    }, user)
    issue_final_nav_governance_record({
        'record_id': 'FINAL-NAV-GOV-DEMO',
        'nav_cycle_id': 'NAV-CYCLE-DEMO',
        'committee_minutes_id': 'VAL-COMMITTEE-DEMO',
        'official_books_reference': 'BOOKS-REL-DEMO',
    }, user)
    result = _evaluate(email, {
        'minutes_readiness': 0.99,
        'challenge_resolution_readiness': 0.989,
        'final_record_readiness': 0.987,
        'open_challenges': 0,
        'unlinked_evidence_gaps': 0,
    })
    return {"ok": True, "result": result, "summary": _summary_for_email(email)}
