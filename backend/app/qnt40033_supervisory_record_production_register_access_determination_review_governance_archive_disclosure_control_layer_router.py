from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json

router = APIRouter(prefix="/api/supervisory-record-production-register-access-determination-review-governance-archive-disclosure-control-layer", tags=["supervisory-record-production-register-access-determination-review-governance-archive-disclosure-control-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ENGINE_DIR = PROJECT_DIR / "backend" / "artifacts" / "supervisory_record_production_register_access_determination_review_governance_archive_disclosure_control_layer"
DEFAULT_POLICY = {
    "retain_cycles": 365,
    "minimum_score": 96.0,
    "minimum_production_register_readiness": 0.97,
    "minimum_access_determination_review_readiness": 0.97,
    "minimum_archive_disclosure_control_readiness": 0.97,
    "maximum_open_disclosure_exceptions": 0,
}

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _require_user():
    return _mu()._require_session()

def _dep_a():
    from backend.app import qnt40032_supervisory_preservation_order_register_archive_chain_of_custody_audit_governance_record_access_challenge_resolution_layer_router as module
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
            "production_registers": [],
            "access_determination_reviews": [],
            "archive_disclosure_controls": [],
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
            "posture": ((a.get("supervisory_preservation_order_register_archive_chain_of_custody_audit_governance_record_access_challenge_resolution_layer_status") or {}).get("posture")),
            "score": la.get("score"),
        },
    }

def _summary_for_email(email: str) -> dict:
    s = _load(email)
    latest = s.get("latest_run") or {}
    return {
        "supervisory_record_production_register_access_determination_review_governance_archive_disclosure_control_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "production_register_count": len(s.get("production_registers") or []),
            "access_determination_review_count": len(s.get("access_determination_reviews") or []),
            "archive_disclosure_control_count": len(s.get("archive_disclosure_controls") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "production_registers": s.get("production_registers") or [],
        "access_determination_reviews": s.get("access_determination_reviews") or [],
        "archive_disclosure_controls": s.get("archive_disclosure_controls") or [],
    }

def _band(score: float) -> str:
    if score >= 98.0:
        return "GOVERNANCE_ARCHIVE_DISCLOSURE_STRONG"
    if score >= 96.0:
        return "GOVERNANCE_ARCHIVE_DISCLOSURE_CLEAR"
    if score >= 92.0:
        return "GOVERNANCE_ARCHIVE_DISCLOSURE_WATCH"
    return "GOVERNANCE_ARCHIVE_DISCLOSURE_REMEDIATION_REQUIRED"

def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _context(email)
    production_register_readiness = float(payload.get("production_register_readiness", 0.0) or 0.0)
    access_determination_review_readiness = float(payload.get("access_determination_review_readiness", 0.0) or 0.0)
    archive_disclosure_control_readiness = float(payload.get("archive_disclosure_control_readiness", 0.0) or 0.0)
    open_disclosure_exceptions = int(payload.get("open_disclosure_exceptions", 0) or 0)
    score = 100.0
    reasons = []
    alerts = []
    def penalize(metric, minimum, weight, reason, code):
        nonlocal score
        if metric < minimum:
            score -= round((minimum - metric) * weight, 2)
            reasons.append(reason)
            alerts.append(code)
    penalize(production_register_readiness, float(policy.get("minimum_production_register_readiness", 0.97)), 120.0, "supervisory record production register readiness is below policy", "PRODUCTION_REGISTER_READINESS_WEAK")
    penalize(access_determination_review_readiness, float(policy.get("minimum_access_determination_review_readiness", 0.97)), 120.0, "access determination review readiness is below policy", "ACCESS_DETERMINATION_REVIEW_WEAK")
    penalize(archive_disclosure_control_readiness, float(policy.get("minimum_archive_disclosure_control_readiness", 0.97)), 120.0, "governance archive disclosure control readiness is below policy", "ARCHIVE_DISCLOSURE_CONTROL_WEAK")
    if open_disclosure_exceptions > int(policy.get("maximum_open_disclosure_exceptions", 0)):
        score -= 8.0 + (open_disclosure_exceptions - int(policy.get("maximum_open_disclosure_exceptions", 0))) * 2.0
        reasons.append("open governance archive disclosure exceptions exceed policy")
        alerts.append("OPEN_DISCLOSURE_EXCEPTIONS_EXCEED_POLICY")
    if ctx.get("dep_a_summary", {}).get("posture") not in {"GOVERNANCE_RECORD_ACCESS_CHALLENGE_STRONG", "GOVERNANCE_RECORD_ACCESS_CHALLENGE_CLEAR", "GOVERNANCE_RECORD_ACCESS_CHALLENGE_WATCH"}:
        score -= 8.0
        reasons.append("governance record access challenge posture must be established before archive disclosure control")
        alerts.append("ACCESS_CHALLENGE_POSTURE_NOT_ESTABLISHED")
    score = max(0.0, round(score, 2))
    posture = _band(score)
    operator_review_required = bool(score < float(policy.get("minimum_score", 96.0)) or open_disclosure_exceptions > 0)
    run = {
        "run_id": f"qnt40033_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "production_register_readiness": production_register_readiness,
        "access_determination_review_readiness": access_determination_review_readiness,
        "archive_disclosure_control_readiness": archive_disclosure_control_readiness,
        "open_disclosure_exceptions": open_disclosure_exceptions,
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

@router.post('/record-production-register')
def record_production_register(payload: dict = Body(...), user=Depends(_require_user)):
    email = user['email']
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    row = _create_row('production_register', payload)
    _append(store, 'production_registers', row, int(policy.get('retain_cycles', 365)))
    _save(email, store)
    return {'ok': True, 'production_register': row, 'summary': _summary_for_email(email)}

@router.post('/record-access-determination-review')
def record_access_determination_review(payload: dict = Body(...), user=Depends(_require_user)):
    email = user['email']
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    row = _create_row('access_determination_review', payload)
    _append(store, 'access_determination_reviews', row, int(policy.get('retain_cycles', 365)))
    _save(email, store)
    return {'ok': True, 'access_determination_review': row, 'summary': _summary_for_email(email)}

@router.post('/record-archive-disclosure-control')
def record_archive_disclosure_control(payload: dict = Body(...), user=Depends(_require_user)):
    email = user['email']
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    row = _create_row('archive_disclosure_control', payload)
    _append(store, 'archive_disclosure_controls', row, int(policy.get('retain_cycles', 365)))
    _save(email, store)
    return {'ok': True, 'archive_disclosure_control': row, 'summary': _summary_for_email(email)}

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
    record_production_register({'register_name': 'supervisory production register FY2025', 'production_register_readiness': 0.99}, user)
    record_access_determination_review({'review_name': 'archive access determination review FY2025', 'access_determination_review_readiness': 0.99}, user)
    record_archive_disclosure_control({'control_name': 'archive disclosure control FY2025', 'archive_disclosure_control_readiness': 0.99}, user)
    run = _evaluate(email, {
        'production_register_readiness': 0.99,
        'access_determination_review_readiness': 0.99,
        'archive_disclosure_control_readiness': 0.99,
        'open_disclosure_exceptions': 0,
    })
    return {'ok': True, 'run': run, 'summary': _summary_for_email(email)}
