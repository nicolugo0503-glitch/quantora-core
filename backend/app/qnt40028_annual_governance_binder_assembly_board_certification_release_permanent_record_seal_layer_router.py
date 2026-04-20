from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json

router = APIRouter(prefix="/api/annual-governance-binder-assembly-board-certification-release-permanent-record-seal-layer", tags=["annual-governance-binder-assembly-board-certification-release-permanent-record-seal-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ENGINE_DIR = PROJECT_DIR / "backend" / "artifacts" / "annual_governance_binder_assembly_board_certification_release_permanent_record_seal_layer"
DEFAULT_POLICY = {
    "retain_cycles": 365,
    "minimum_score": 96.0,
    "minimum_annual_governance_binder_readiness": 0.97,
    "minimum_board_certification_release_readiness": 0.97,
    "minimum_permanent_record_seal_readiness": 0.97,
    "maximum_pending_record_exceptions": 0,
}

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _require_user():
    return _mu()._require_session()

def _dep_a():
    from backend.app import qnt40027_board_resolution_archive_committee_approval_trace_annual_governance_evidence_lock_layer_router as module
    return module

def _dep_b():
    from backend.app import qnt40026_board_reporting_agenda_control_annual_meeting_materials_approval_investor_communication_governance_lock_layer_router as module
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
            "annual_governance_binders": [],
            "board_certification_releases": [],
            "permanent_record_seals": [],
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
    b = _dep_b()._summary_for_email(email)
    la = a.get("latest_run") or {}
    lb = b.get("latest_run") or {}
    return {
        "captured_at": _now_iso(),
        "dep_a_summary": {
            "posture": ((a.get("board_resolution_archive_committee_approval_trace_annual_governance_evidence_lock_layer_status") or {}).get("posture")),
            "score": la.get("score"),
        },
        "dep_b_summary": {
            "posture": ((b.get("board_reporting_agenda_control_annual_meeting_materials_approval_investor_communication_governance_lock_layer_status") or {}).get("posture")),
            "score": lb.get("score"),
        },
    }

def _summary_for_email(email: str) -> dict:
    s = _load(email)
    latest = s.get("latest_run") or {}
    return {
        "annual_governance_binder_assembly_board_certification_release_permanent_record_seal_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "annual_governance_binder_count": len(s.get("annual_governance_binders") or []),
            "board_certification_release_count": len(s.get("board_certification_releases") or []),
            "permanent_record_seal_count": len(s.get("permanent_record_seals") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "annual_governance_binders": s.get("annual_governance_binders") or [],
        "board_certification_releases": s.get("board_certification_releases") or [],
        "permanent_record_seals": s.get("permanent_record_seals") or [],
    }

def _band(score: float) -> str:
    if score >= 98.0:
        return "PERMANENT_RECORD_SEAL_STRONG"
    if score >= 96.0:
        return "PERMANENT_RECORD_SEAL_CLEAR"
    if score >= 92.0:
        return "PERMANENT_RECORD_SEAL_WATCH"
    return "PERMANENT_RECORD_SEAL_REMEDIATION_REQUIRED"

def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _context(email)
    annual_governance_binder_readiness = float(payload.get("annual_governance_binder_readiness", 0.0) or 0.0)
    board_certification_release_readiness = float(payload.get("board_certification_release_readiness", 0.0) or 0.0)
    permanent_record_seal_readiness = float(payload.get("permanent_record_seal_readiness", 0.0) or 0.0)
    pending_record_exceptions = int(payload.get("pending_record_exceptions", 0) or 0)
    score = 100.0
    reasons = []
    alerts = []
    def penalize(metric, minimum, weight, reason, code):
        nonlocal score
        if metric < minimum:
            score -= round((minimum - metric) * weight, 2)
            reasons.append(reason)
            alerts.append(code)
    penalize(annual_governance_binder_readiness, float(policy.get("minimum_annual_governance_binder_readiness", 0.97)), 120.0, "annual governance binder readiness is below policy", "ANNUAL_GOVERNANCE_BINDER_READINESS_WEAK")
    penalize(board_certification_release_readiness, float(policy.get("minimum_board_certification_release_readiness", 0.97)), 120.0, "board certification release readiness is below policy", "BOARD_CERTIFICATION_RELEASE_READINESS_WEAK")
    penalize(permanent_record_seal_readiness, float(policy.get("minimum_permanent_record_seal_readiness", 0.97)), 120.0, "permanent record seal readiness is below policy", "PERMANENT_RECORD_SEAL_READINESS_WEAK")
    if pending_record_exceptions > int(policy.get("maximum_pending_record_exceptions", 0)):
        score -= 8.0 + (pending_record_exceptions - int(policy.get("maximum_pending_record_exceptions", 0))) * 2.0
        reasons.append("pending permanent-record exceptions exceed policy")
        alerts.append("PENDING_PERMANENT_RECORD_EXCEPTIONS_EXCEED_POLICY")
    if ctx.get("dep_a_summary", {}).get("posture") not in {"ANNUAL_GOVERNANCE_EVIDENCE_STRONG", "ANNUAL_GOVERNANCE_EVIDENCE_CLEAR", "ANNUAL_GOVERNANCE_EVIDENCE_WATCH"}:
        score -= 8.0
        reasons.append("annual governance evidence lock posture must be established before permanent record seal")
        alerts.append("ANNUAL_GOVERNANCE_EVIDENCE_LOCK_POSTURE_NOT_ESTABLISHED")
    if ctx.get("dep_b_summary", {}).get("posture") not in {"BOARD_COMMUNICATION_GOVERNANCE_STRONG", "BOARD_COMMUNICATION_GOVERNANCE_CLEAR", "BOARD_COMMUNICATION_GOVERNANCE_WATCH"}:
        score -= 6.0
        reasons.append("board communication governance posture must be established before board certification release")
        alerts.append("BOARD_COMMUNICATION_GOVERNANCE_POSTURE_NOT_ESTABLISHED")
    score = max(0.0, round(score, 2))
    posture = _band(score)
    operator_review_required = bool(score < float(policy.get("minimum_score", 96.0)) or pending_record_exceptions > 0)
    run = {
        "run_id": f"qnt40028_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "annual_governance_binder_readiness": annual_governance_binder_readiness,
        "board_certification_release_readiness": board_certification_release_readiness,
        "permanent_record_seal_readiness": permanent_record_seal_readiness,
        "pending_record_exceptions": pending_record_exceptions,
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

@router.post('/assemble-annual-governance-binder')
def assemble_annual_governance_binder(payload: dict = Body(...), user=Depends(_require_user)):
    email = user['email']
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    row = _create_row('annual_governance_binder', payload)
    _append(store, 'annual_governance_binders', row, int(policy.get('retain_cycles', 365)))
    _save(email, store)
    return {'ok': True, 'annual_governance_binder': row, 'summary': _summary_for_email(email)}

@router.post('/release-board-certification')
def release_board_certification(payload: dict = Body(...), user=Depends(_require_user)):
    email = user['email']
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    row = _create_row('board_certification_release', payload)
    _append(store, 'board_certification_releases', row, int(policy.get('retain_cycles', 365)))
    _save(email, store)
    return {'ok': True, 'board_certification_release': row, 'summary': _summary_for_email(email)}

@router.post('/seal-permanent-record')
def seal_permanent_record(payload: dict = Body(...), user=Depends(_require_user)):
    email = user['email']
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    row = _create_row('permanent_record_seal', payload)
    _append(store, 'permanent_record_seals', row, int(policy.get('retain_cycles', 365)))
    _save(email, store)
    return {'ok': True, 'permanent_record_seal': row, 'summary': _summary_for_email(email)}

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
    try:
        _dep_b().bootstrap_demo(user)
    except Exception:
        pass
    assemble_annual_governance_binder({'binder_name': 'annual governance binder FY2025', 'annual_governance_binder_readiness': 0.99}, user)
    release_board_certification({'certification_name': 'board certification release FY2025', 'board_certification_release_readiness': 0.99}, user)
    seal_permanent_record({'seal_name': 'permanent record seal FY2025', 'permanent_record_seal_readiness': 0.99}, user)
    run = _evaluate(email, {'annual_governance_binder_readiness': 0.99, 'board_certification_release_readiness': 0.99, 'permanent_record_seal_readiness': 0.99, 'pending_record_exceptions': 0})
    return {'ok': True, 'run': run, 'summary': _summary_for_email(email)}
