from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json

router = APIRouter(prefix="/api/governance-record-retention-schedule-board-retrieval-index-permanent-archive-supervision-layer", tags=["governance-record-retention-schedule-board-retrieval-index-permanent-archive-supervision-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ENGINE_DIR = PROJECT_DIR / "backend" / "artifacts" / "governance_record_retention_schedule_board_retrieval_index_permanent_archive_supervision_layer"
DEFAULT_POLICY = {
    "retain_cycles": 365,
    "minimum_score": 96.0,
    "minimum_retention_schedule_readiness": 0.97,
    "minimum_retrieval_index_readiness": 0.97,
    "minimum_archive_supervision_readiness": 0.97,
    "maximum_open_archive_exceptions": 0,
}

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _require_user():
    return _mu()._require_session()

def _dep_a():
    from backend.app import qnt40028_annual_governance_binder_assembly_board_certification_release_permanent_record_seal_layer_router as module
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
            "retention_schedules": [],
            "retrieval_indexes": [],
            "archive_supervisions": [],
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
        "governance_record_retention_schedule_board_retrieval_index_permanent_archive_supervision_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "retention_schedule_count": len(s.get("retention_schedules") or []),
            "retrieval_index_count": len(s.get("retrieval_indexes") or []),
            "archive_supervision_count": len(s.get("archive_supervisions") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "retention_schedules": s.get("retention_schedules") or [],
        "retrieval_indexes": s.get("retrieval_indexes") or [],
        "archive_supervisions": s.get("archive_supervisions") or [],
    }

def _band(score: float) -> str:
    if score >= 98.0:
        return "PERMANENT_ARCHIVE_SUPERVISION_STRONG"
    if score >= 96.0:
        return "PERMANENT_ARCHIVE_SUPERVISION_CLEAR"
    if score >= 92.0:
        return "PERMANENT_ARCHIVE_SUPERVISION_WATCH"
    return "PERMANENT_ARCHIVE_SUPERVISION_REMEDIATION_REQUIRED"

def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _context(email)
    retention_schedule_readiness = float(payload.get("retention_schedule_readiness", 0.0) or 0.0)
    retrieval_index_readiness = float(payload.get("retrieval_index_readiness", 0.0) or 0.0)
    archive_supervision_readiness = float(payload.get("archive_supervision_readiness", 0.0) or 0.0)
    open_archive_exceptions = int(payload.get("open_archive_exceptions", 0) or 0)
    score = 100.0
    reasons = []
    alerts = []
    def penalize(metric, minimum, weight, reason, code):
        nonlocal score
        if metric < minimum:
            score -= round((minimum - metric) * weight, 2)
            reasons.append(reason)
            alerts.append(code)
    penalize(retention_schedule_readiness, float(policy.get("minimum_retention_schedule_readiness", 0.97)), 120.0, "retention schedule readiness is below policy", "RETENTION_SCHEDULE_READINESS_WEAK")
    penalize(retrieval_index_readiness, float(policy.get("minimum_retrieval_index_readiness", 0.97)), 120.0, "retrieval index readiness is below policy", "RETRIEVAL_INDEX_READINESS_WEAK")
    penalize(archive_supervision_readiness, float(policy.get("minimum_archive_supervision_readiness", 0.97)), 120.0, "archive supervision readiness is below policy", "ARCHIVE_SUPERVISION_READINESS_WEAK")
    if open_archive_exceptions > int(policy.get("maximum_open_archive_exceptions", 0)):
        score -= 8.0 + (open_archive_exceptions - int(policy.get("maximum_open_archive_exceptions", 0))) * 2.0
        reasons.append("open permanent-archive exceptions exceed policy")
        alerts.append("OPEN_PERMANENT_ARCHIVE_EXCEPTIONS_EXCEED_POLICY")
    if ctx.get("dep_a_summary", {}).get("posture") not in {"PERMANENT_RECORD_SEAL_STRONG", "PERMANENT_RECORD_SEAL_CLEAR", "PERMANENT_RECORD_SEAL_WATCH"}:
        score -= 8.0
        reasons.append("permanent record seal posture must be established before archive supervision")
        alerts.append("PERMANENT_RECORD_SEAL_POSTURE_NOT_ESTABLISHED")
    score = max(0.0, round(score, 2))
    posture = _band(score)
    operator_review_required = bool(score < float(policy.get("minimum_score", 96.0)) or open_archive_exceptions > 0)
    run = {
        "run_id": f"qnt40029_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "retention_schedule_readiness": retention_schedule_readiness,
        "retrieval_index_readiness": retrieval_index_readiness,
        "archive_supervision_readiness": archive_supervision_readiness,
        "open_archive_exceptions": open_archive_exceptions,
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
def record_retention_schedule(payload: dict = Body(...), user=Depends(_require_user)):
    email = user['email']
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    row = _create_row('retention_schedule', payload)
    _append(store, 'retention_schedules', row, int(policy.get('retain_cycles', 365)))
    _save(email, store)
    return {'ok': True, 'retention_schedule': row, 'summary': _summary_for_email(email)}

@router.post('/record-board-retrieval-index')
def record_board_retrieval_index(payload: dict = Body(...), user=Depends(_require_user)):
    email = user['email']
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    row = _create_row('retrieval_index', payload)
    _append(store, 'retrieval_indexes', row, int(policy.get('retain_cycles', 365)))
    _save(email, store)
    return {'ok': True, 'retrieval_index': row, 'summary': _summary_for_email(email)}

@router.post('/record-permanent-archive-supervision')
def record_permanent_archive_supervision(payload: dict = Body(...), user=Depends(_require_user)):
    email = user['email']
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    row = _create_row('archive_supervision', payload)
    _append(store, 'archive_supervisions', row, int(policy.get('retain_cycles', 365)))
    _save(email, store)
    return {'ok': True, 'archive_supervision': row, 'summary': _summary_for_email(email)}

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
    record_retention_schedule({'schedule_name': 'annual governance retention schedule FY2025', 'retention_schedule_readiness': 0.99}, user)
    record_board_retrieval_index({'index_name': 'board retrieval index FY2025', 'retrieval_index_readiness': 0.99}, user)
    record_permanent_archive_supervision({'supervision_name': 'permanent archive supervision FY2025', 'archive_supervision_readiness': 0.99}, user)
    run = _evaluate(email, {'retention_schedule_readiness': 0.99, 'retrieval_index_readiness': 0.99, 'archive_supervision_readiness': 0.99, 'open_archive_exceptions': 0})
    return {'ok': True, 'run': run, 'summary': _summary_for_email(email)}
