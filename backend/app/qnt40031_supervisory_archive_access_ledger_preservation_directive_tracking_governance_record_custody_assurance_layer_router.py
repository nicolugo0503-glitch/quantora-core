from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json

router = APIRouter(prefix="/api/supervisory-archive-access-ledger-preservation-directive-tracking-governance-record-custody-assurance-layer", tags=["supervisory-archive-access-ledger-preservation-directive-tracking-governance-record-custody-assurance-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ENGINE_DIR = PROJECT_DIR / "backend" / "artifacts" / "supervisory_archive_access_ledger_preservation_directive_tracking_governance_record_custody_assurance_layer"
DEFAULT_POLICY = {
    "retain_cycles": 365,
    "minimum_score": 96.0,
    "minimum_access_ledger_readiness": 0.97,
    "minimum_preservation_directive_tracking_readiness": 0.97,
    "minimum_custody_assurance_readiness": 0.97,
    "maximum_open_custody_exceptions": 0,
}

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _require_user():
    return _mu()._require_session()

def _dep_a():
    from backend.app import qnt40030_governance_archive_exception_review_retrieval_breach_escalation_supervisory_preservation_override_layer_router as module
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
            "access_ledgers": [],
            "preservation_directives": [],
            "custody_assurances": [],
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
            "posture": ((a.get("governance_archive_exception_review_retrieval_breach_escalation_supervisory_preservation_override_layer_status") or {}).get("posture")),
            "score": la.get("score"),
        },
    }

def _summary_for_email(email: str) -> dict:
    s = _load(email)
    latest = s.get("latest_run") or {}
    return {
        "supervisory_archive_access_ledger_preservation_directive_tracking_governance_record_custody_assurance_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "access_ledger_count": len(s.get("access_ledgers") or []),
            "preservation_directive_count": len(s.get("preservation_directives") or []),
            "custody_assurance_count": len(s.get("custody_assurances") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "access_ledgers": s.get("access_ledgers") or [],
        "preservation_directives": s.get("preservation_directives") or [],
        "custody_assurances": s.get("custody_assurances") or [],
    }

def _band(score: float) -> str:
    if score >= 98.0:
        return "GOVERNANCE_RECORD_CUSTODY_STRONG"
    if score >= 96.0:
        return "GOVERNANCE_RECORD_CUSTODY_CLEAR"
    if score >= 92.0:
        return "GOVERNANCE_RECORD_CUSTODY_WATCH"
    return "GOVERNANCE_RECORD_CUSTODY_REMEDIATION_REQUIRED"

def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _context(email)
    access_ledger_readiness = float(payload.get("access_ledger_readiness", 0.0) or 0.0)
    preservation_directive_tracking_readiness = float(payload.get("preservation_directive_tracking_readiness", 0.0) or 0.0)
    custody_assurance_readiness = float(payload.get("custody_assurance_readiness", 0.0) or 0.0)
    open_custody_exceptions = int(payload.get("open_custody_exceptions", 0) or 0)
    score = 100.0
    reasons = []
    alerts = []
    def penalize(metric, minimum, weight, reason, code):
        nonlocal score
        if metric < minimum:
            score -= round((minimum - metric) * weight, 2)
            reasons.append(reason)
            alerts.append(code)
    penalize(access_ledger_readiness, float(policy.get("minimum_access_ledger_readiness", 0.97)), 120.0, "supervisory archive access ledger readiness is below policy", "ACCESS_LEDGER_READINESS_WEAK")
    penalize(preservation_directive_tracking_readiness, float(policy.get("minimum_preservation_directive_tracking_readiness", 0.97)), 120.0, "preservation directive tracking readiness is below policy", "PRESERVATION_DIRECTIVE_TRACKING_WEAK")
    penalize(custody_assurance_readiness, float(policy.get("minimum_custody_assurance_readiness", 0.97)), 120.0, "governance record custody assurance readiness is below policy", "CUSTODY_ASSURANCE_READINESS_WEAK")
    if open_custody_exceptions > int(policy.get("maximum_open_custody_exceptions", 0)):
        score -= 8.0 + (open_custody_exceptions - int(policy.get("maximum_open_custody_exceptions", 0))) * 2.0
        reasons.append("open governance record custody exceptions exceed policy")
        alerts.append("OPEN_CUSTODY_EXCEPTIONS_EXCEED_POLICY")
    if ctx.get("dep_a_summary", {}).get("posture") not in {"SUPERVISORY_PRESERVATION_OVERRIDE_STRONG", "SUPERVISORY_PRESERVATION_OVERRIDE_CLEAR", "SUPERVISORY_PRESERVATION_OVERRIDE_WATCH"}:
        score -= 8.0
        reasons.append("supervisory preservation override posture must be established before archive custody assurance")
        alerts.append("SUPERVISORY_PRESERVATION_OVERRIDE_POSTURE_NOT_ESTABLISHED")
    score = max(0.0, round(score, 2))
    posture = _band(score)
    operator_review_required = bool(score < float(policy.get("minimum_score", 96.0)) or open_custody_exceptions > 0)
    run = {
        "run_id": f"qnt40031_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "access_ledger_readiness": access_ledger_readiness,
        "preservation_directive_tracking_readiness": preservation_directive_tracking_readiness,
        "custody_assurance_readiness": custody_assurance_readiness,
        "open_custody_exceptions": open_custody_exceptions,
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

@router.post('/record-access-ledger')
def record_access_ledger(payload: dict = Body(...), user=Depends(_require_user)):
    email = user['email']
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    row = _create_row('access_ledger', payload)
    _append(store, 'access_ledgers', row, int(policy.get('retain_cycles', 365)))
    _save(email, store)
    return {'ok': True, 'access_ledger': row, 'summary': _summary_for_email(email)}

@router.post('/record-preservation-directive')
def record_preservation_directive(payload: dict = Body(...), user=Depends(_require_user)):
    email = user['email']
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    row = _create_row('preservation_directive', payload)
    _append(store, 'preservation_directives', row, int(policy.get('retain_cycles', 365)))
    _save(email, store)
    return {'ok': True, 'preservation_directive': row, 'summary': _summary_for_email(email)}

@router.post('/record-custody-assurance')
def record_custody_assurance(payload: dict = Body(...), user=Depends(_require_user)):
    email = user['email']
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    row = _create_row('custody_assurance', payload)
    _append(store, 'custody_assurances', row, int(policy.get('retain_cycles', 365)))
    _save(email, store)
    return {'ok': True, 'custody_assurance': row, 'summary': _summary_for_email(email)}

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
    record_access_ledger({'ledger_name': 'supervisory archive access ledger FY2025', 'access_ledger_readiness': 0.99}, user)
    record_preservation_directive({'directive_name': 'preservation directive tracking FY2025', 'preservation_directive_tracking_readiness': 0.99}, user)
    record_custody_assurance({'assurance_name': 'governance record custody assurance FY2025', 'custody_assurance_readiness': 0.99}, user)
    run = _evaluate(email, {
        'access_ledger_readiness': 0.99,
        'preservation_directive_tracking_readiness': 0.99,
        'custody_assurance_readiness': 0.99,
        'open_custody_exceptions': 0,
    })
    return {'ok': True, 'run': run, 'summary': _summary_for_email(email)}
