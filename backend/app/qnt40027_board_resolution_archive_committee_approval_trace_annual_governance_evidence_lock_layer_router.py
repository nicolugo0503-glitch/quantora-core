from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json

router = APIRouter(prefix="/api/board-resolution-archive-committee-approval-trace-annual-governance-evidence-lock-layer", tags=["board-resolution-archive-committee-approval-trace-annual-governance-evidence-lock-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ENGINE_DIR = PROJECT_DIR / "backend" / "artifacts" / "board_resolution_archive_committee_approval_trace_annual_governance_evidence_lock_layer"
DEFAULT_POLICY = {"retain_cycles": 365, "minimum_score": 96.0, "minimum_board_resolution_archive_readiness": 0.97, "minimum_committee_approval_trace_readiness": 0.97, "minimum_annual_governance_evidence_lock_readiness": 0.97, "maximum_pending_evidence_exceptions": 0}

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _require_user():
    return _mu()._require_session()

def _dep_a():
    from backend.app import qnt40026_board_reporting_agenda_control_annual_meeting_materials_approval_investor_communication_governance_lock_layer_router as module
    return module

def _dep_b():
    from backend.app import qnt40025_annual_investor_communications_calendar_board_letter_approval_archive_dissemination_control_layer_router as module
    return module

def _safe(v:str)->str:
    return hashlib.sha256((v or '').strip().lower().encode()).hexdigest()[:24]

def _path(email:str)->Path:
    ENGINE_DIR.mkdir(parents=True, exist_ok=True)
    return ENGINE_DIR / f"{_safe(email)}.json"

def _now_iso():
    return datetime.now(timezone.utc).isoformat()

def _append(store,key,row,retain):
    arr=list(store.get(key) or [])
    arr.insert(0,row)
    store[key]=arr[:max(int(retain or 1),1)]

def _load(email:str)->dict:
    path=_path(email)
    if not path.exists():
        data={"email":email,"policy":dict(DEFAULT_POLICY),"runs":[],"alerts":[],"board_resolution_archives":[],"committee_approval_traces":[],"annual_governance_evidence_locks":[],"latest_run":None,"last_context":{}}
        path.write_text(json.dumps(data, indent=2), encoding='utf-8')
        return data
    return json.loads(path.read_text(encoding='utf-8'))

def _save(email,data):
    _path(email).write_text(json.dumps(data, indent=2), encoding='utf-8')

def _context(email:str)->dict:
    a=_dep_a()._summary_for_email(email)
    b=_dep_b()._summary_for_email(email)
    la=a.get('latest_run') or {}
    lb=b.get('latest_run') or {}
    return {'captured_at':_now_iso(), 'dep_a_summary':{'posture':((a.get('board_reporting_agenda_control_annual_meeting_materials_approval_investor_communication_governance_lock_layer_status') or {}).get('posture')), 'score':la.get('score')}, 'dep_b_summary':{'posture':((b.get('annual_investor_communications_calendar_board_letter_approval_archive_dissemination_control_layer_status') or {}).get('posture')), 'score':lb.get('score')}}

def _summary_for_email(email:str)->dict:
    s=_load(email)
    latest=s.get('latest_run') or {}
    return {'board_resolution_archive_committee_approval_trace_annual_governance_evidence_lock_layer_status':{'posture':latest.get('posture','UNINITIALIZED'),'latest_score':latest.get('score'),'band':latest.get('band','UNSET'),'run_count':len(s.get('runs') or []),'alert_count':len(s.get('alerts') or []),'board_resolution_archive_count':len(s.get('board_resolution_archives') or []),'committee_approval_trace_count':len(s.get('committee_approval_traces') or []),'annual_governance_evidence_lock_count':len(s.get('annual_governance_evidence_locks') or []),'operator_review_required':bool(latest.get('operator_review_required',False))},'latest_run':latest,'alerts':s.get('alerts') or [],'policy':s.get('policy') or dict(DEFAULT_POLICY),'last_context':s.get('last_context') or {},'board_resolution_archives': s.get('board_resolution_archives') or [],'committee_approval_traces': s.get('committee_approval_traces') or [],'annual_governance_evidence_locks': s.get('annual_governance_evidence_locks') or []}

def _band(score:float)->str:
    if score >= 98.0:
        return 'ANNUAL_GOVERNANCE_EVIDENCE_STRONG'
    if score >= 96.0:
        return 'ANNUAL_GOVERNANCE_EVIDENCE_CLEAR'
    if score >= 92.0:
        return 'ANNUAL_GOVERNANCE_EVIDENCE_WATCH'
    return 'ANNUAL_GOVERNANCE_EVIDENCE_REMEDIATION_REQUIRED'

def _evaluate(email:str,payload:dict)->dict:
    store=_load(email)
    policy={**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    ctx=_context(email)
    board_resolution_archive_readiness = float(payload.get('board_resolution_archive_readiness', 0.0) or 0.0)
    committee_approval_trace_readiness = float(payload.get('committee_approval_trace_readiness', 0.0) or 0.0)
    annual_governance_evidence_lock_readiness = float(payload.get('annual_governance_evidence_lock_readiness', 0.0) or 0.0)
    score=100.0
    reasons=[]
    alerts=[]
    def penalize(metric, minimum, weight, reason, code):
        nonlocal score
        if metric < minimum:
            score -= round((minimum-metric)*weight,2)
            reasons.append(reason)
            alerts.append(code)
    penalize(board_resolution_archive_readiness, float(policy.get('minimum_board_resolution_archive_readiness', 0.97)), 120.0, 'board resolution archive readiness is below policy', 'BOARD_RESOLUTION_ARCHIVE_READINESS_WEAK')
    penalize(committee_approval_trace_readiness, float(policy.get('minimum_committee_approval_trace_readiness', 0.97)), 120.0, 'committee approval trace readiness is below policy', 'COMMITTEE_APPROVAL_TRACE_READINESS_WEAK')
    penalize(annual_governance_evidence_lock_readiness, float(policy.get('minimum_annual_governance_evidence_lock_readiness', 0.97)), 120.0, 'annual governance evidence lock readiness is below policy', 'ANNUAL_GOVERNANCE_EVIDENCE_LOCK_READINESS_WEAK')
    if int(payload.get('pending_evidence_exceptions',0) or 0) > int(policy.get('maximum_pending_evidence_exceptions',0)):
        score -= 8.0 + (int(payload.get('pending_evidence_exceptions',0) or 0)-int(policy.get('maximum_pending_evidence_exceptions',0)))*2.0
        reasons.append('pending annual governance evidence exceptions exceed policy')
        alerts.append('PENDING_ANNUAL_GOVERNANCE_EVIDENCE_EXCEPTIONS_EXCEED_POLICY')
    if ctx.get('dep_a_summary',{}).get('posture') not in {'BOARD_COMMUNICATION_GOVERNANCE_STRONG','BOARD_COMMUNICATION_GOVERNANCE_CLEAR','BOARD_COMMUNICATION_GOVERNANCE_WATCH'}:
        score -= 8.0
        reasons.append('board communication governance posture must be established before evidence lock')
        alerts.append('BOARD_COMMUNICATION_GOVERNANCE_POSTURE_NOT_ESTABLISHED')
    if ctx.get('dep_b_summary',{}).get('posture') not in {'ANNUAL_COMMUNICATIONS_CONTROL_STRONG','ANNUAL_COMMUNICATIONS_CONTROL_CLEAR','ANNUAL_COMMUNICATIONS_CONTROL_WATCH'}:
        score -= 6.0
        reasons.append('annual investor communications posture must be established before governance evidence lock')
        alerts.append('ANNUAL_INVESTOR_COMMUNICATIONS_POSTURE_NOT_ESTABLISHED')
    score=max(0.0, round(score,2))
    posture=_band(score)
    operator_review_required=bool(score < float(policy.get('minimum_score',96.0)) or int(payload.get('pending_evidence_exceptions',0) or 0) > 0)
    run={'run_id':f"qnt40027_{int(datetime.now(timezone.utc).timestamp())}",'captured_at':_now_iso(),'board_resolution_archive_readiness':board_resolution_archive_readiness,'committee_approval_trace_readiness':committee_approval_trace_readiness,'annual_governance_evidence_lock_readiness':annual_governance_evidence_lock_readiness,'pending_evidence_exceptions':int(payload.get('pending_evidence_exceptions',0) or 0),'score':score,'band':posture,'posture':posture,'reasons':reasons,'alerts':alerts,'operator_review_required':operator_review_required}
    _append(store,'runs',run,int(policy.get('retain_cycles',365)))
    store['latest_run']=run
    store['alerts']=[{'captured_at':_now_iso(),'code':code} for code in alerts]
    store['last_context']=ctx
    _save(email,store)
    return run

def _create_row(kind,payload):
    return {'id':f"{kind}_{int(datetime.now(timezone.utc).timestamp())}",'captured_at':_now_iso(), **payload}

@router.get('/summary')
def summary(user=Depends(_require_user)):
    return _summary_for_email(user['email'])

@router.post('/evaluate')
def evaluate(payload:dict=Body(...), user=Depends(_require_user)):
    return {'ok':True,'run':_evaluate(user['email'], payload),'summary':_summary_for_email(user['email'])}

@router.post('/record-board-resolution-archive')
def record_board_resolution_archive(payload:dict=Body(...), user=Depends(_require_user)):
    email=user['email']
    store=_load(email)
    policy={**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    row=_create_row('board_resolution_archive', payload)
    _append(store, 'board_resolution_archives', row, int(policy.get('retain_cycles',365)))
    _save(email, store)
    return {'ok':True, 'board_resolution_archive': row, 'summary': _summary_for_email(email)}

@router.post('/record-committee-approval-trace')
def record_committee_approval_trace(payload:dict=Body(...), user=Depends(_require_user)):
    email=user['email']
    store=_load(email)
    policy={**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    row=_create_row('committee_approval_trace', payload)
    _append(store, 'committee_approval_traces', row, int(policy.get('retain_cycles',365)))
    _save(email, store)
    return {'ok':True, 'committee_approval_trace': row, 'summary': _summary_for_email(email)}

@router.post('/lock-annual-governance-evidence')
def lock_annual_governance_evidence(payload:dict=Body(...), user=Depends(_require_user)):
    email=user['email']
    store=_load(email)
    policy={**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    row=_create_row('annual_governance_evidence_lock', payload)
    _append(store, 'annual_governance_evidence_locks', row, int(policy.get('retain_cycles',365)))
    _save(email, store)
    return {'ok':True, 'annual_governance_evidence_lock': row, 'summary': _summary_for_email(email)}

@router.get('/policy')
def policy(user=Depends(_require_user)):
    return {'ok':True,'policy':_load(user['email']).get('policy') or dict(DEFAULT_POLICY)}

@router.post('/policy')
def set_policy(payload:dict=Body(...), user=Depends(_require_user)):
    email=user['email']
    store=_load(email)
    store['policy']={**dict(DEFAULT_POLICY), **(store.get('policy') or {}), **payload}
    _save(email, store)
    return {'ok':True,'policy':store['policy']}

@router.post('/bootstrap-demo')
def bootstrap_demo(user=Depends(_require_user)):
    email=user['email']
    _dep_a().bootstrap_demo(user)
    try:
        _dep_b().bootstrap_demo(user)
    except Exception:
        pass
    record_board_resolution_archive({'archive_name':'board resolution archive FY2025','board_resolution_archive_readiness':0.99}, user)
    record_committee_approval_trace({'trace_name':'committee approval trace FY2025','committee_approval_trace_readiness':0.99}, user)
    lock_annual_governance_evidence({'lock_name':'annual governance evidence lock FY2025','annual_governance_evidence_lock_readiness':0.99}, user)
    run=_evaluate(email, {'board_resolution_archive_readiness':0.99,'committee_approval_trace_readiness':0.99,'annual_governance_evidence_lock_readiness':0.99,'pending_evidence_exceptions':0})
    return {'ok':True, 'run':run, 'summary':_summary_for_email(email)}
