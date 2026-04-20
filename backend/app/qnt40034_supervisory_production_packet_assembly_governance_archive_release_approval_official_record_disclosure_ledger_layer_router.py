from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json

router = APIRouter(prefix="/api/supervisory-production-packet-assembly-governance-archive-release-approval-official-record-disclosure-ledger-layer", tags=["supervisory-production-packet-assembly-governance-archive-release-approval-official-record-disclosure-ledger-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ENGINE_DIR = PROJECT_DIR / "backend" / "artifacts" / "supervisory_production_packet_assembly_governance_archive_release_approval_official_record_disclosure_ledger_layer"
DEFAULT_POLICY = {
    "retain_cycles": 365,
    "minimum_score": 96.0,
    "minimum_production_packet_readiness": 0.97,
    "minimum_release_approval_readiness": 0.97,
    "minimum_disclosure_ledger_readiness": 0.97,
    "maximum_open_disclosure_issues": 0,
}

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _require_user():
    return _mu()._require_session()

def _dep_a():
    from backend.app import qnt40033_supervisory_record_production_register_access_determination_review_governance_archive_disclosure_control_layer_router as module
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
            "production_packets": [],
            "release_approvals": [],
            "disclosure_ledgers": [],
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
            "posture": ((a.get("supervisory_record_production_register_access_determination_review_governance_archive_disclosure_control_layer_status") or {}).get("posture")),
            "score": la.get("score"),
        },
    }

def _summary_for_email(email: str) -> dict:
    s = _load(email)
    latest = s.get("latest_run") or {}
    return {
        "supervisory_production_packet_assembly_governance_archive_release_approval_official_record_disclosure_ledger_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "production_packet_count": len(s.get("production_packets") or []),
            "release_approval_count": len(s.get("release_approvals") or []),
            "disclosure_ledger_count": len(s.get("disclosure_ledgers") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "production_packets": s.get("production_packets") or [],
        "release_approvals": s.get("release_approvals") or [],
        "disclosure_ledgers": s.get("disclosure_ledgers") or [],
    }

def _band(score: float) -> str:
    if score >= 98.0:
        return "OFFICIAL_RECORD_DISCLOSURE_LEDGER_STRONG"
    if score >= 96.0:
        return "OFFICIAL_RECORD_DISCLOSURE_LEDGER_CLEAR"
    if score >= 92.0:
        return "OFFICIAL_RECORD_DISCLOSURE_LEDGER_WATCH"
    return "OFFICIAL_RECORD_DISCLOSURE_LEDGER_REMEDIATION_REQUIRED"

def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _context(email)
    production_packet_readiness = float(payload.get("production_packet_readiness", 0.0) or 0.0)
    release_approval_readiness = float(payload.get("release_approval_readiness", 0.0) or 0.0)
    disclosure_ledger_readiness = float(payload.get("disclosure_ledger_readiness", 0.0) or 0.0)
    open_disclosure_issues = int(payload.get("open_disclosure_issues", 0) or 0)
    score = 100.0
    reasons = []
    alerts = []
    def penalize(metric, minimum, weight, reason, code):
        nonlocal score
        if metric < minimum:
            score -= round((minimum - metric) * weight, 2)
            reasons.append(reason)
            alerts.append(code)
    penalize(production_packet_readiness, float(policy.get("minimum_production_packet_readiness", 0.97)), 120.0, "supervisory production packet readiness is below policy", "PRODUCTION_PACKET_READINESS_WEAK")
    penalize(release_approval_readiness, float(policy.get("minimum_release_approval_readiness", 0.97)), 120.0, "governance archive release approval readiness is below policy", "RELEASE_APPROVAL_READINESS_WEAK")
    penalize(disclosure_ledger_readiness, float(policy.get("minimum_disclosure_ledger_readiness", 0.97)), 120.0, "official record disclosure ledger readiness is below policy", "DISCLOSURE_LEDGER_READINESS_WEAK")
    if open_disclosure_issues > int(policy.get("maximum_open_disclosure_issues", 0)):
        score -= 8.0 + (open_disclosure_issues - int(policy.get("maximum_open_disclosure_issues", 0))) * 2.0
        reasons.append("open official record disclosure issues exceed policy")
        alerts.append("OPEN_DISCLOSURE_ISSUES_EXCEED_POLICY")
    if ctx.get("dep_a_summary", {}).get("posture") not in {"GOVERNANCE_ARCHIVE_DISCLOSURE_STRONG", "GOVERNANCE_ARCHIVE_DISCLOSURE_CLEAR", "GOVERNANCE_ARCHIVE_DISCLOSURE_WATCH"}:
        score -= 8.0
        reasons.append("governance archive disclosure posture must be established before official record disclosure ledger release")
        alerts.append("ARCHIVE_DISCLOSURE_POSTURE_NOT_ESTABLISHED")
    score = max(0.0, round(score, 2))
    posture = _band(score)
    operator_review_required = bool(score < float(policy.get("minimum_score", 96.0)) or open_disclosure_issues > 0)
    run = {
        "run_id": f"qnt40034_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "production_packet_readiness": production_packet_readiness,
        "release_approval_readiness": release_approval_readiness,
        "disclosure_ledger_readiness": disclosure_ledger_readiness,
        "open_disclosure_issues": open_disclosure_issues,
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

@router.post('/record-production-packet')
def record_production_packet(payload: dict = Body(...), user=Depends(_require_user)):
    email = user['email']
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    row = _create_row('production_packet', payload)
    _append(store, 'production_packets', row, int(policy.get('retain_cycles', 365)))
    _save(email, store)
    return {'ok': True, 'production_packet': row, 'summary': _summary_for_email(email)}

@router.post('/record-release-approval')
def record_release_approval(payload: dict = Body(...), user=Depends(_require_user)):
    email = user['email']
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    row = _create_row('release_approval', payload)
    _append(store, 'release_approvals', row, int(policy.get('retain_cycles', 365)))
    _save(email, store)
    return {'ok': True, 'release_approval': row, 'summary': _summary_for_email(email)}

@router.post('/record-disclosure-ledger')
def record_disclosure_ledger(payload: dict = Body(...), user=Depends(_require_user)):
    email = user['email']
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    row = _create_row('disclosure_ledger', payload)
    _append(store, 'disclosure_ledgers', row, int(policy.get('retain_cycles', 365)))
    _save(email, store)
    return {'ok': True, 'disclosure_ledger': row, 'summary': _summary_for_email(email)}

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
    record_production_packet({'packet_name': 'official supervisory production packet FY2025', 'production_packet_readiness': 0.99}, user)
    record_release_approval({'approval_name': 'governance archive release approval FY2025', 'release_approval_readiness': 0.99}, user)
    record_disclosure_ledger({'ledger_name': 'official record disclosure ledger FY2025', 'disclosure_ledger_readiness': 0.99}, user)
    run = _evaluate(email, {
        'production_packet_readiness': 0.99,
        'release_approval_readiness': 0.99,
        'disclosure_ledger_readiness': 0.99,
        'open_disclosure_issues': 0,
    })
    return {'ok': True, 'run': run, 'summary': _summary_for_email(email)}
