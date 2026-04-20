from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json

router = APIRouter(prefix="/api/governance-archive-exception-review-retrieval-breach-escalation-supervisory-preservation-override-layer", tags=["governance-archive-exception-review-retrieval-breach-escalation-supervisory-preservation-override-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ENGINE_DIR = PROJECT_DIR / "backend" / "artifacts" / "governance_archive_exception_review_retrieval_breach_escalation_supervisory_preservation_override_layer"
DEFAULT_POLICY = {
    "retain_cycles": 365,
    "minimum_score": 96.0,
    "minimum_archive_exception_review_readiness": 0.97,
    "minimum_retrieval_breach_escalation_readiness": 0.97,
    "minimum_supervisory_preservation_override_readiness": 0.97,
    "maximum_open_retrieval_breaches": 0,
}

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _require_user():
    return _mu()._require_session()

def _dep_a():
    from backend.app import qnt40029_governance_record_retention_schedule_board_retrieval_index_permanent_archive_supervision_layer_router as module
    return module

def _safe(v: str) -> str:
    return hashlib.sha256((v or '').strip().lower().encode()).hexdigest()[:24]

def _path(email: str) -> Path:
    ENGINE_DIR.mkdir(parents=True, exist_ok=True)
    return ENGINE_DIR / f"{_safe(email)}.json"

def _now_iso():
    return datetime.now(timezone.utc).isoformat()

def _append(store, key, row, retain):
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
            "archive_exception_reviews": [],
            "retrieval_breach_escalations": [],
            "supervisory_preservation_overrides": [],
            "latest_run": None,
            "last_context": {},
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))

def _save(email, data):
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")

def _context(email: str) -> dict:
    a = _dep_a()._summary_for_email(email)
    la = a.get("latest_run") or {}
    return {
        "captured_at": _now_iso(),
        "dep_a_summary": {
            "posture": ((a.get("annual_governance_binder_assembly_board_certification_release_permanent_record_seal_layer_status") or {}).get("posture")),
            "score": la.get("score"),
        },
    }

def _summary_for_email(email: str) -> dict:
    s = _load(email)
    latest = s.get("latest_run") or {}
    return {
        "governance_archive_exception_review_retrieval_breach_escalation_supervisory_preservation_override_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "archive_exception_review_count": len(s.get("archive_exception_reviews") or []),
            "retrieval_breach_escalation_count": len(s.get("retrieval_breach_escalations") or []),
            "supervisory_preservation_override_count": len(s.get("supervisory_preservation_overrides") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "archive_exception_reviews": s.get("archive_exception_reviews") or [],
        "retrieval_breach_escalations": s.get("retrieval_breach_escalations") or [],
        "supervisory_preservation_overrides": s.get("supervisory_preservation_overrides") or [],
    }

def _band(score: float) -> str:
    if score >= 98.0:
        return "SUPERVISORY_PRESERVATION_OVERRIDE_STRONG"
    if score >= 96.0:
        return "SUPERVISORY_PRESERVATION_OVERRIDE_CLEAR"
    if score >= 92.0:
        return "SUPERVISORY_PRESERVATION_OVERRIDE_WATCH"
    return "SUPERVISORY_PRESERVATION_OVERRIDE_REMEDIATION_REQUIRED"

def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _context(email)
    archive_exception_review_readiness = float(payload.get("archive_exception_review_readiness", 0.0) or 0.0)
    retrieval_breach_escalation_readiness = float(payload.get("retrieval_breach_escalation_readiness", 0.0) or 0.0)
    supervisory_preservation_override_readiness = float(payload.get("supervisory_preservation_override_readiness", 0.0) or 0.0)
    open_retrieval_breaches = int(payload.get("open_retrieval_breaches", 0) or 0)
    score = 100.0
    reasons = []
    alerts = []
    def penalize(metric, minimum, weight, reason, code):
        nonlocal score
        if metric < minimum:
            score -= round((minimum - metric) * weight, 2)
            reasons.append(reason)
            alerts.append(code)
    penalize(archive_exception_review_readiness, float(policy.get("minimum_archive_exception_review_readiness", 0.97)), 120.0, "archive exception review readiness is below policy", "ARCHIVE_EXCEPTION_REVIEW_READINESS_WEAK")
    penalize(retrieval_breach_escalation_readiness, float(policy.get("minimum_retrieval_breach_escalation_readiness", 0.97)), 120.0, "retrieval breach escalation readiness is below policy", "RETRIEVAL_BREACH_READINESS_WEAK")
    penalize(supervisory_preservation_override_readiness, float(policy.get("minimum_supervisory_preservation_override_readiness", 0.97)), 120.0, "supervisory preservation override readiness is below policy", "SUPERVISORY_PRESERVATION_OVERRIDE_READINESS_WEAK")
    if open_retrieval_breaches > int(policy.get("maximum_open_retrieval_breaches", 0)):
        score -= 8.0 + (open_retrieval_breaches - int(policy.get("maximum_open_retrieval_breaches", 0))) * 2.0
        reasons.append("open permanent-archive exceptions exceed policy")
        alerts.append("OPEN_RETRIEVAL_BREACHES_EXCEED_POLICY")
    if ctx.get("dep_a_summary", {}).get("posture") not in {"PERMANENT_RECORD_SEAL_STRONG", "PERMANENT_RECORD_SEAL_CLEAR", "PERMANENT_RECORD_SEAL_WATCH"}:
        score -= 8.0
        reasons.append("permanent record seal posture must be established before supervisory preservation override")
        alerts.append("PERMANENT_ARCHIVE_SUPERVISION_POSTURE_NOT_ESTABLISHED")
    score = max(0.0, round(score, 2))
    posture = _band(score)
    operator_review_required = bool(score < float(policy.get("minimum_score", 96.0)) or open_retrieval_breaches > 0)
    run = {
        "run_id": f"qnt40030_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "archive_exception_review_readiness": archive_exception_review_readiness,
        "retrieval_breach_escalation_readiness": retrieval_breach_escalation_readiness,
        "supervisory_preservation_override_readiness": supervisory_preservation_override_readiness,
        "open_retrieval_breaches": open_retrieval_breaches,
        "score": score,
        "band": posture,
        "posture": posture,
        "reasons": reasons,
        "alerts": alerts,
        "operator_review_required": operator_review_required,
    }
    _append(store, "runs", run, int(policy.get("retain_cycles", 365)))
    store["latest_run"] = run
    store["alerts"] = [{"captured_at": _now_iso(), "code": code} for code in alerts]
    store["last_context"] = ctx
    _save(email, store)
    return run

def _create_row(kind, payload):
    return {"id": f"{kind}_{int(datetime.now(timezone.utc).timestamp())}", "captured_at": _now_iso(), **payload}

@router.get('/summary')
def summary(user=Depends(_require_user)):
    return _summary_for_email(user['email'])

@router.post('/evaluate')
def evaluate(payload: dict = Body(...), user=Depends(_require_user)):
    return {'ok': True, 'run': _evaluate(user['email'], payload), 'summary': _summary_for_email(user['email'])}

@router.post('/record-retention-schedule')
def record_archive_exception_review(payload: dict = Body(...), user=Depends(_require_user)):
    email = user['email']
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    row = _create_row('archive_exception_review', payload)
    _append(store, 'archive_exception_reviews', row, int(policy.get('retain_cycles', 365)))
    _save(email, store)
    return {'ok': True, 'archive_exception_review': row, 'summary': _summary_for_email(email)}

@router.post('/record-board-retrieval-index')
def record_board_retrieval_breach_escalation(payload: dict = Body(...), user=Depends(_require_user)):
    email = user['email']
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    row = _create_row('retrieval_breach_escalation', payload)
    _append(store, 'retrieval_breach_escalations', row, int(policy.get('retain_cycles', 365)))
    _save(email, store)
    return {'ok': True, 'retrieval_breach_escalation': row, 'summary': _summary_for_email(email)}

@router.post('/record-permanent-archive-supervision')
def record_permanent_supervisory_preservation_override(payload: dict = Body(...), user=Depends(_require_user)):
    email = user['email']
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    row = _create_row('supervisory_preservation_override', payload)
    _append(store, 'supervisory_preservation_overrides', row, int(policy.get('retain_cycles', 365)))
    _save(email, store)
    return {'ok': True, 'supervisory_preservation_override': row, 'summary': _summary_for_email(email)}

@router.get('/policy')
def policy(user=Depends(_require_user)):
    return {'ok': True, 'policy': _load(user['email']).get('policy') or dict(DEFAULT_POLICY)}

@router.post('/policy')
def set_policy(payload: dict = Body(...), user=Depends(_require_user)):
    email = user['email']
    store = _load(email)
    store['policy'] = {**dict(DEFAULT_POLICY), **(store.get('policy') or {}), **payload}
    _save(email, store)
    return {'ok': True, 'policy': store['policy']}

@router.post('/bootstrap-demo')
def bootstrap_demo(user=Depends(_require_user)):
    email = user['email']
    _dep_a().bootstrap_demo(user)
    record_archive_exception_review({'schedule_name': 'annual governance archive exception review FY2025', 'archive_exception_review_readiness': 0.99}, user)
    record_board_retrieval_breach_escalation({'index_name': 'board retrieval breach escalation FY2025', 'retrieval_breach_escalation_readiness': 0.99}, user)
    record_permanent_supervisory_preservation_override({'supervision_name': 'supervisory preservation override FY2025', 'supervisory_preservation_override_readiness': 0.99}, user)
    run = _evaluate(email, {'archive_exception_review_readiness': 0.99, 'retrieval_breach_escalation_readiness': 0.99, 'supervisory_preservation_override_readiness': 0.99, 'open_retrieval_breaches': 0})
    return {'ok': True, 'run': run, 'summary': _summary_for_email(email)}
