from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json

router = APIRouter(prefix="/api/annual-investor-communications-calendar-board-letter-approval-archive-dissemination-control-layer", tags=["annual-investor-communications-calendar-board-letter-approval-archive-dissemination-control-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ENGINE_DIR = PROJECT_DIR / "backend" / "artifacts" / "annual_investor_communications_calendar_board_letter_approval_archive_dissemination_control_layer"
DEFAULT_POLICY = {'retain_cycles': 365, 'minimum_score': 96.0, 'minimum_communications_calendar_readiness': 0.97, 'minimum_board_letter_approval_readiness': 0.97, 'minimum_archive_dissemination_readiness': 0.97, 'maximum_pending_dissemination_exceptions': 0}

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _require_user():
    return _mu()._require_session()

def _dep_a():
    from backend.app import qnt40024_annual_report_assembly_lp_letter_distribution_financial_statement_archive_certification_layer_router as module
    return module

def _dep_b():
    from backend.app import qnt40023_financial_statement_issuance_lp_reporting_pack_release_audit_closure_record_lock_layer_router as module
    return module

def _safe(v:str)->str:
    return hashlib.sha256((v or "").strip().lower().encode()).hexdigest()[:24]

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
        data={"email":email,"policy":dict(DEFAULT_POLICY),"runs":[],"alerts":[],"communications_calendars":[],"board_letter_approvals":[],"archive_disseminations":[],"latest_run":None,"last_context":{}}
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
    return {'captured_at':_now_iso(), 'dep_a_summary':{'posture':((a.get('annual_report_assembly_lp_letter_distribution_financial_statement_archive_certification_layer_status') or {}).get('posture')), 'score':la.get('score')}, 'dep_b_summary':{'posture':((b.get('financial_statement_issuance_lp_reporting_pack_release_audit_closure_record_lock_layer_status') or {}).get('posture')), 'score':lb.get('score')}}

def _summary_for_email(email:str)->dict:
    s=_load(email)
    latest=s.get('latest_run') or {}
    return {'annual_investor_communications_calendar_board_letter_approval_archive_dissemination_control_layer_status':{'posture':latest.get('posture','UNINITIALIZED'),'latest_score':latest.get('score'),'band':latest.get('band','UNSET'),'run_count':len(s.get('runs') or []),'alert_count':len(s.get('alerts') or []),"communications_calendar_count":len(s.get("communications_calendars") or []),"board_letter_approval_count":len(s.get("board_letter_approvals") or []),"archive_dissemination_count":len(s.get("archive_disseminations") or []),'operator_review_required':bool(latest.get('operator_review_required',False))},'latest_run':latest,'alerts':s.get('alerts') or [],'policy':s.get('policy') or dict(DEFAULT_POLICY),'last_context':s.get('last_context') or {},"communications_calendars": s.get("communications_calendars") or [],"board_letter_approvals": s.get("board_letter_approvals") or [],"archive_disseminations": s.get("archive_disseminations") or []}

def _band(score:float)->str:
    if score >= 98.0:
        return "ANNUAL_COMMUNICATIONS_CONTROL_STRONG"
    if score >= 96.0:
        return "ANNUAL_COMMUNICATIONS_CONTROL_CLEAR"
    if score >= 92.0:
        return "ANNUAL_COMMUNICATIONS_CONTROL_WATCH"
    return "ANNUAL_COMMUNICATIONS_CONTROL_REMEDIATION_REQUIRED"

def _evaluate(email:str,payload:dict)->dict:
    store=_load(email)
    policy={**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    ctx=_context(email)
    communications_calendar_readiness = float(payload.get("communications_calendar_readiness", 0.0) or 0.0)
    board_letter_approval_readiness = float(payload.get("board_letter_approval_readiness", 0.0) or 0.0)
    archive_dissemination_readiness = float(payload.get("archive_dissemination_readiness", 0.0) or 0.0)
    score=100.0
    reasons=[]
    alerts=[]
    def penalize(metric, minimum, weight, reason, code):
        nonlocal score
        if metric < minimum:
            score -= round((minimum-metric)*weight,2)
            reasons.append(reason)
            alerts.append(code)
    penalize(communications_calendar_readiness, float(policy.get("minimum_communications_calendar_readiness", 0.97)), 120.0, "communications calendar readiness is below policy", "COMMUNICATIONS_CALENDAR_READINESS_WEAK")
    penalize(board_letter_approval_readiness, float(policy.get("minimum_board_letter_approval_readiness", 0.97)), 120.0, "board letter approval readiness is below policy", "BOARD_LETTER_APPROVAL_READINESS_WEAK")
    penalize(archive_dissemination_readiness, float(policy.get("minimum_archive_dissemination_readiness", 0.97)), 120.0, "archive dissemination readiness is below policy", "ARCHIVE_DISSEMINATION_READINESS_WEAK")
    if int(payload.get('pending_dissemination_exceptions',0) or 0) > int(policy.get('maximum_pending_dissemination_exceptions',0)):
        score -= 8.0 + (int(payload.get('pending_dissemination_exceptions',0) or 0)-int(policy.get('maximum_pending_dissemination_exceptions',0)))*2.0
        reasons.append('pending dissemination exceptions exceed policy')
        alerts.append('PENDING_DISSEMINATION_EXCEPTIONS_EXCEED_POLICY')
    if ctx.get("dep_a_summary",{}).get("posture") not in {"ANNUAL_REPORT_RELEASE_STRONG","ANNUAL_REPORT_RELEASE_CLEAR","ANNUAL_REPORT_RELEASE_WATCH"}:
        score -= 8.0
        reasons.append("annual close archive posture must be established before communications release")
        alerts.append("ANNUAL_CLOSE_ARCHIVE_NOT_ESTABLISHED")
    if ctx.get("dep_b_summary",{}).get("posture") not in {"AUDIT_CLOSURE_RELEASE_STRONG","AUDIT_CLOSURE_RELEASE_CLEAR","AUDIT_CLOSURE_RELEASE_WATCH"}:
        score -= 6.0
        reasons.append("audit closure release posture must be established before annual communications release")
        alerts.append("AUDIT_CLOSURE_RELEASE_NOT_ESTABLISHED")
    score=max(0.0, round(score,2))
    posture=_band(score)
    operator_review_required=bool(score < float(policy.get('minimum_score',96.0)) or int(payload.get('pending_dissemination_exceptions',0) or 0) > 0)
    run={'run_id':f"qnt40025_{int(datetime.now(timezone.utc).timestamp())}",'captured_at':_now_iso(),"communications_calendar_readiness": communications_calendar_readiness,"board_letter_approval_readiness": board_letter_approval_readiness,"archive_dissemination_readiness": archive_dissemination_readiness,"pending_dissemination_exceptions": int(payload.get("pending_dissemination_exceptions",0) or 0),'score':score,'band':posture,'posture':posture,'reasons':reasons,'alerts':alerts,'operator_review_required':operator_review_required}
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

@router.post('/record-communications-calendar')
def record_communications_calendar(payload:dict=Body(...), user=Depends(_require_user)):
    email=user['email']
    store=_load(email)
    policy={**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    row=_create_row('communications_calendar', payload)
    _append(store, 'communications_calendars', row, int(policy.get('retain_cycles',365)))
    _save(email, store)
    return {'ok':True, 'communications_calendar': row, 'summary': _summary_for_email(email)}

@router.post('/approve-board-letter')
def approve_board_letter(payload:dict=Body(...), user=Depends(_require_user)):
    email=user['email']
    store=_load(email)
    policy={**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    row=_create_row('board_letter_approval', payload)
    _append(store, 'board_letter_approvals', row, int(policy.get('retain_cycles',365)))
    _save(email, store)
    return {'ok':True, 'board_letter_approval': row, 'summary': _summary_for_email(email)}

@router.post('/record-archive-dissemination')
def record_archive_dissemination(payload:dict=Body(...), user=Depends(_require_user)):
    email=user['email']
    store=_load(email)
    policy={**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    row=_create_row('archive_dissemination', payload)
    _append(store, 'archive_disseminations', row, int(policy.get('retain_cycles',365)))
    _save(email, store)
    return {'ok':True, 'archive_dissemination': row, 'summary': _summary_for_email(email)}
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
    record_communications_calendar({"calendar_name":"annual investor communications 2026","communications_calendar_readiness":0.99}, user)
    approve_board_letter({"letter_title":"annual board letter FY2025","board_letter_approval_readiness":0.99}, user)
    record_archive_dissemination({"archive_name":"fy2025 archive dissemination","archive_dissemination_readiness":0.99}, user)
    run=_evaluate(email, {"communications_calendar_readiness": 0.99, "board_letter_approval_readiness": 0.99, "archive_dissemination_readiness": 0.99, "pending_dissemination_exceptions": 0})
    return {'ok':True, 'run':run, 'summary':_summary_for_email(email)}
