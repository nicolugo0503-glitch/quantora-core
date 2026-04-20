from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json

router = APIRouter(prefix="/api/board-reporting-agenda-control-annual-meeting-materials-approval-investor-communication-governance-lock-layer", tags=["board-reporting-agenda-control-annual-meeting-materials-approval-investor-communication-governance-lock-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ENGINE_DIR = PROJECT_DIR / "backend" / "artifacts" / "board_reporting_agenda_control_annual_meeting_materials_approval_investor_communication_governance_lock_layer"
DEFAULT_POLICY = {"retain_cycles": 365, "minimum_score": 96.0, "minimum_board_reporting_agenda_readiness": 0.97, "minimum_annual_meeting_materials_readiness": 0.97, "minimum_governance_lock_readiness": 0.97, "maximum_pending_lock_exceptions": 0}

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _require_user():
    return _mu()._require_session()

def _dep_a():
    from backend.app import qnt40025_annual_investor_communications_calendar_board_letter_approval_archive_dissemination_control_layer_router as module
    return module

def _dep_b():
    from backend.app import qnt40024_annual_report_assembly_lp_letter_distribution_financial_statement_archive_certification_layer_router as module
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
        data={"email":email,"policy":dict(DEFAULT_POLICY),"runs":[],"alerts":[],"board_reporting_agendas":[],"annual_meeting_materials":[],"governance_locks":[],"latest_run":None,"last_context":{}}
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
    return {'captured_at':_now_iso(), 'dep_a_summary':{'posture':((a.get('annual_investor_communications_calendar_board_letter_approval_archive_dissemination_control_layer_status') or {}).get('posture')), 'score':la.get('score')}, 'dep_b_summary':{'posture':((b.get('annual_report_assembly_lp_letter_distribution_financial_statement_archive_certification_layer_status') or {}).get('posture')), 'score':lb.get('score')}}

def _summary_for_email(email:str)->dict:
    s=_load(email)
    latest=s.get('latest_run') or {}
    return {'board_reporting_agenda_control_annual_meeting_materials_approval_investor_communication_governance_lock_layer_status':{'posture':latest.get('posture','UNINITIALIZED'),'latest_score':latest.get('score'),'band':latest.get('band','UNSET'),'run_count':len(s.get('runs') or []),'alert_count':len(s.get('alerts') or []),'board_reporting_agenda_count':len(s.get('board_reporting_agendas') or []),'annual_meeting_materials_count':len(s.get('annual_meeting_materials') or []),'governance_lock_count':len(s.get('governance_locks') or []),'operator_review_required':bool(latest.get('operator_review_required',False))},'latest_run':latest,'alerts':s.get('alerts') or [],'policy':s.get('policy') or dict(DEFAULT_POLICY),'last_context':s.get('last_context') or {},'board_reporting_agendas': s.get('board_reporting_agendas') or [],'annual_meeting_materials': s.get('annual_meeting_materials') or [],'governance_locks': s.get('governance_locks') or []}

def _band(score:float)->str:
    if score >= 98.0:
        return 'BOARD_COMMUNICATION_GOVERNANCE_STRONG'
    if score >= 96.0:
        return 'BOARD_COMMUNICATION_GOVERNANCE_CLEAR'
    if score >= 92.0:
        return 'BOARD_COMMUNICATION_GOVERNANCE_WATCH'
    return 'BOARD_COMMUNICATION_GOVERNANCE_REMEDIATION_REQUIRED'

def _evaluate(email:str,payload:dict)->dict:
    store=_load(email)
    policy={**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    ctx=_context(email)
    board_reporting_agenda_readiness = float(payload.get('board_reporting_agenda_readiness', 0.0) or 0.0)
    annual_meeting_materials_readiness = float(payload.get('annual_meeting_materials_readiness', 0.0) or 0.0)
    governance_lock_readiness = float(payload.get('governance_lock_readiness', 0.0) or 0.0)
    score=100.0
    reasons=[]
    alerts=[]
    def penalize(metric, minimum, weight, reason, code):
        nonlocal score
        if metric < minimum:
            score -= round((minimum-metric)*weight,2)
            reasons.append(reason)
            alerts.append(code)
    penalize(board_reporting_agenda_readiness, float(policy.get('minimum_board_reporting_agenda_readiness', 0.97)), 120.0, 'board reporting agenda readiness is below policy', 'BOARD_REPORTING_AGENDA_READINESS_WEAK')
    penalize(annual_meeting_materials_readiness, float(policy.get('minimum_annual_meeting_materials_readiness', 0.97)), 120.0, 'annual meeting materials readiness is below policy', 'ANNUAL_MEETING_MATERIALS_READINESS_WEAK')
    penalize(governance_lock_readiness, float(policy.get('minimum_governance_lock_readiness', 0.97)), 120.0, 'investor communication governance lock readiness is below policy', 'GOVERNANCE_LOCK_READINESS_WEAK')
    if int(payload.get('pending_lock_exceptions',0) or 0) > int(policy.get('maximum_pending_lock_exceptions',0)):
        score -= 8.0 + (int(payload.get('pending_lock_exceptions',0) or 0)-int(policy.get('maximum_pending_lock_exceptions',0)))*2.0
        reasons.append('pending governance lock exceptions exceed policy')
        alerts.append('PENDING_GOVERNANCE_LOCK_EXCEPTIONS_EXCEED_POLICY')
    if ctx.get('dep_a_summary',{}).get('posture') not in {'ANNUAL_COMMUNICATIONS_CONTROL_STRONG','ANNUAL_COMMUNICATIONS_CONTROL_CLEAR','ANNUAL_COMMUNICATIONS_CONTROL_WATCH'}:
        score -= 8.0
        reasons.append('annual investor communications posture must be established before governance lock')
        alerts.append('ANNUAL_COMMUNICATIONS_POSTURE_NOT_ESTABLISHED')
    if ctx.get('dep_b_summary',{}).get('posture') not in {'ANNUAL_REPORT_RELEASE_STRONG','ANNUAL_REPORT_RELEASE_CLEAR','ANNUAL_REPORT_RELEASE_WATCH'}:
        score -= 6.0
        reasons.append('annual report archive posture must be established before governance lock')
        alerts.append('ANNUAL_REPORT_ARCHIVE_POSTURE_NOT_ESTABLISHED')
    score=max(0.0, round(score,2))
    posture=_band(score)
    operator_review_required=bool(score < float(policy.get('minimum_score',96.0)) or int(payload.get('pending_lock_exceptions',0) or 0) > 0)
    run={'run_id':f"qnt40026_{int(datetime.now(timezone.utc).timestamp())}",'captured_at':_now_iso(),'board_reporting_agenda_readiness':board_reporting_agenda_readiness,'annual_meeting_materials_readiness':annual_meeting_materials_readiness,'governance_lock_readiness':governance_lock_readiness,'pending_lock_exceptions':int(payload.get('pending_lock_exceptions',0) or 0),'score':score,'band':posture,'posture':posture,'reasons':reasons,'alerts':alerts,'operator_review_required':operator_review_required}
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

@router.post('/record-board-reporting-agenda')
def record_board_reporting_agenda(payload:dict=Body(...), user=Depends(_require_user)):
    email=user['email']
    store=_load(email)
    policy={**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    row=_create_row('board_reporting_agenda', payload)
    _append(store, 'board_reporting_agendas', row, int(policy.get('retain_cycles',365)))
    _save(email, store)
    return {'ok':True, 'board_reporting_agenda': row, 'summary': _summary_for_email(email)}

@router.post('/approve-annual-meeting-materials')
def approve_annual_meeting_materials(payload:dict=Body(...), user=Depends(_require_user)):
    email=user['email']
    store=_load(email)
    policy={**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    row=_create_row('annual_meeting_materials', payload)
    _append(store, 'annual_meeting_materials', row, int(policy.get('retain_cycles',365)))
    _save(email, store)
    return {'ok':True, 'annual_meeting_materials': row, 'summary': _summary_for_email(email)}

@router.post('/lock-investor-communication-governance')
def lock_investor_communication_governance(payload:dict=Body(...), user=Depends(_require_user)):
    email=user['email']
    store=_load(email)
    policy={**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    row=_create_row('governance_lock', payload)
    _append(store, 'governance_locks', row, int(policy.get('retain_cycles',365)))
    _save(email, store)
    return {'ok':True, 'governance_lock': row, 'summary': _summary_for_email(email)}

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
    record_board_reporting_agenda({'agenda_name':'annual board reporting agenda FY2025','board_reporting_agenda_readiness':0.99}, user)
    approve_annual_meeting_materials({'materials_name':'annual meeting materials FY2025','annual_meeting_materials_readiness':0.99}, user)
    lock_investor_communication_governance({'lock_name':'investor communication governance final lock FY2025','governance_lock_readiness':0.99}, user)
    run=_evaluate(email, {'board_reporting_agenda_readiness':0.99,'annual_meeting_materials_readiness':0.99,'governance_lock_readiness':0.99,'pending_lock_exceptions':0})
    return {'ok':True, 'run':run, 'summary':_summary_for_email(email)}
