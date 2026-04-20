from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json

router = APIRouter(prefix="/api/supervisory-preservation-order-register-archive-chain-of-custody-audit-governance-record-access-challenge-resolution-layer", tags=["supervisory-preservation-order-register-archive-chain-of-custody-audit-governance-record-access-challenge-resolution-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ENGINE_DIR = PROJECT_DIR / "backend" / "artifacts" / "supervisory_preservation_order_register_archive_chain_of_custody_audit_governance_record_access_challenge_resolution_layer"
DEFAULT_POLICY = {
    "retain_cycles": 365,
    "minimum_score": 96.0,
    "minimum_preservation_order_register_readiness": 0.97,
    "minimum_chain_of_custody_audit_readiness": 0.97,
    "minimum_access_challenge_resolution_readiness": 0.97,
    "maximum_open_access_challenges": 0,
}

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _require_user():
    return _mu()._require_session()

def _dep_a():
    from backend.app import qnt40031_supervisory_archive_access_ledger_preservation_directive_tracking_governance_record_custody_assurance_layer_router as module
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
            "preservation_orders": [],
            "chain_of_custody_audits": [],
            "access_challenge_resolutions": [],
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
            "posture": ((a.get("supervisory_archive_access_ledger_preservation_directive_tracking_governance_record_custody_assurance_layer_status") or {}).get("posture")),
            "score": la.get("score"),
        },
    }

def _summary_for_email(email: str) -> dict:
    s = _load(email)
    latest = s.get("latest_run") or {}
    return {
        "supervisory_preservation_order_register_archive_chain_of_custody_audit_governance_record_access_challenge_resolution_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "preservation_order_count": len(s.get("preservation_orders") or []),
            "chain_of_custody_audit_count": len(s.get("chain_of_custody_audits") or []),
            "access_challenge_resolution_count": len(s.get("access_challenge_resolutions") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "preservation_orders": s.get("preservation_orders") or [],
        "chain_of_custody_audits": s.get("chain_of_custody_audits") or [],
        "access_challenge_resolutions": s.get("access_challenge_resolutions") or [],
    }

def _band(score: float) -> str:
    if score >= 98.0:
        return "ACCESS_CHALLENGE_RESOLUTION_STRONG"
    if score >= 96.0:
        return "ACCESS_CHALLENGE_RESOLUTION_CLEAR"
    if score >= 92.0:
        return "ACCESS_CHALLENGE_RESOLUTION_WATCH"
    return "ACCESS_CHALLENGE_RESOLUTION_REMEDIATION_REQUIRED"

def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _context(email)
    preservation_order_register_readiness = float(payload.get("preservation_order_register_readiness", 0.0) or 0.0)
    chain_of_custody_audit_readiness = float(payload.get("chain_of_custody_audit_readiness", 0.0) or 0.0)
    access_challenge_resolution_readiness = float(payload.get("access_challenge_resolution_readiness", 0.0) or 0.0)
    open_access_challenges = int(payload.get("open_access_challenges", 0) or 0)
    score = 100.0
    reasons = []
    alerts = []
    def penalize(metric, minimum, weight, reason, code):
        nonlocal score
        if metric < minimum:
            score -= round((minimum - metric) * weight, 2)
            reasons.append(reason)
            alerts.append(code)
    penalize(preservation_order_register_readiness, float(policy.get("minimum_preservation_order_register_readiness", 0.97)), 120.0, "supervisory preservation order register readiness is below policy", "PRESERVATION_ORDER_REGISTER_READINESS_WEAK")
    penalize(chain_of_custody_audit_readiness, float(policy.get("minimum_chain_of_custody_audit_readiness", 0.97)), 120.0, "archive chain-of-custody audit readiness is below policy", "CHAIN_OF_CUSTODY_AUDIT_READINESS_WEAK")
    penalize(access_challenge_resolution_readiness, float(policy.get("minimum_access_challenge_resolution_readiness", 0.97)), 120.0, "governance record access challenge resolution readiness is below policy", "ACCESS_CHALLENGE_RESOLUTION_READINESS_WEAK")
    if open_access_challenges > int(policy.get("maximum_open_access_challenges", 0)):
        score -= 8.0 + (open_access_challenges - int(policy.get("maximum_open_access_challenges", 0))) * 2.0
        reasons.append("open governance record access challenges exceed policy")
        alerts.append("OPEN_ACCESS_CHALLENGES_EXCEED_POLICY")
    if ctx.get("dep_a_summary", {}).get("posture") not in {"GOVERNANCE_RECORD_CUSTODY_STRONG", "GOVERNANCE_RECORD_CUSTODY_CLEAR", "GOVERNANCE_RECORD_CUSTODY_WATCH"}:
        score -= 8.0
        reasons.append("governance record custody assurance posture must be established before access challenge resolution")
        alerts.append("GOVERNANCE_RECORD_CUSTODY_POSTURE_NOT_ESTABLISHED")
    score = max(0.0, round(score, 2))
    posture = _band(score)
    operator_review_required = bool(score < float(policy.get("minimum_score", 96.0)) or open_access_challenges > 0)
    run = {
        "run_id": f"qnt40032_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "preservation_order_register_readiness": preservation_order_register_readiness,
        "chain_of_custody_audit_readiness": chain_of_custody_audit_readiness,
        "access_challenge_resolution_readiness": access_challenge_resolution_readiness,
        "open_access_challenges": open_access_challenges,
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

@router.post('/record-preservation-order')
def record_preservation_order(payload: dict = Body(...), user=Depends(_require_user)):
    email = user['email']
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    row = _create_row('preservation_order', payload)
    _append(store, 'preservation_orders', row, int(policy.get('retain_cycles', 365)))
    _save(email, store)
    return {'ok': True, 'preservation_order': row, 'summary': _summary_for_email(email)}

@router.post('/record-chain-of-custody-audit')
def record_chain_of_custody_audit(payload: dict = Body(...), user=Depends(_require_user)):
    email = user['email']
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    row = _create_row('chain_of_custody_audit', payload)
    _append(store, 'chain_of_custody_audits', row, int(policy.get('retain_cycles', 365)))
    _save(email, store)
    return {'ok': True, 'chain_of_custody_audit': row, 'summary': _summary_for_email(email)}

@router.post('/record-access-challenge-resolution')
def record_access_challenge_resolution(payload: dict = Body(...), user=Depends(_require_user)):
    email = user['email']
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    row = _create_row('access_challenge_resolution', payload)
    _append(store, 'access_challenge_resolutions', row, int(policy.get('retain_cycles', 365)))
    _save(email, store)
    return {'ok': True, 'access_challenge_resolution': row, 'summary': _summary_for_email(email)}

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
    record_preservation_order({'order_name': 'supervisory preservation order register FY2025', 'preservation_order_register_readiness': 0.99}, user)
    record_chain_of_custody_audit({'audit_name': 'archive chain of custody audit FY2025', 'chain_of_custody_audit_readiness': 0.99}, user)
    record_access_challenge_resolution({'challenge_name': 'governance record access challenge resolution FY2025', 'access_challenge_resolution_readiness': 0.99}, user)
    run = _evaluate(email, {
        'preservation_order_register_readiness': 0.99,
        'chain_of_custody_audit_readiness': 0.99,
        'access_challenge_resolution_readiness': 0.99,
        'open_access_challenges': 0,
    })
    return {'ok': True, 'run': run, 'summary': _summary_for_email(email)}
