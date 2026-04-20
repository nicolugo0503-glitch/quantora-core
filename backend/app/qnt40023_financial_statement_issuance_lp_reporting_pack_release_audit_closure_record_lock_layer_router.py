from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json

router = APIRouter(prefix="/api/financial-statement-issuance-lp-reporting-pack-release-audit-closure-record-lock-layer", tags=["financial-statement-issuance-lp-reporting-pack-release-audit-closure-record-lock-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ENGINE_DIR = PROJECT_DIR / "backend" / "artifacts" / "financial_statement_issuance_lp_reporting_pack_release_audit_closure_record_lock_layer"
DEFAULT_POLICY = {'retain_cycles': 365, 'minimum_score': 96.0, 'minimum_financial_statement_issuance_readiness': 0.97, 'minimum_lp_reporting_pack_release_readiness': 0.97, 'minimum_audit_closure_record_lock_readiness': 0.97, 'maximum_pending_release_exceptions': 0}

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _require_user():
    return _mu()._require_session()

def _dep_a():
    from backend.app import qnt40022_audit_opinion_readiness_open_item_clearance_financial_statement_release_authorization_layer_router as module
    return module

def _dep_b():
    from backend.app import qnt40015_investor_capital_statement_consolidation_period_close_certification_lp_book_final_lock_layer_router as module
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
        data={"email":email,"policy":dict(DEFAULT_POLICY),"runs":[],"alerts":[],"financial_statement_issuances":[],"lp_reporting_pack_releases":[],"audit_closure_record_locks":[],"latest_run":None,"last_context":{}}
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
    return {'captured_at':_now_iso(), 'dep_a_summary':{'posture':((a.get('audit_opinion_readiness_open_item_clearance_financial_statement_release_authorization_layer_status') or {}).get('posture')), 'score':la.get('score')}, 'dep_b_summary':{'posture':((b.get('investor_capital_statement_consolidation_period_close_certification_lp_book_final_lock_layer_status') or {}).get('posture')), 'score':lb.get('score')}}

def _summary_for_email(email:str)->dict:
    s=_load(email)
    latest=s.get('latest_run') or {}
    return {'financial_statement_issuance_lp_reporting_pack_release_audit_closure_record_lock_layer_status':{'posture':latest.get('posture','UNINITIALIZED'),'latest_score':latest.get('score'),'band':latest.get('band','UNSET'),'run_count':len(s.get('runs') or []),'alert_count':len(s.get('alerts') or []),"financial_statement_issuance_count":len(s.get("financial_statement_issuances") or []),"lp_reporting_pack_release_count":len(s.get("lp_reporting_pack_releases") or []),"audit_closure_record_lock_count":len(s.get("audit_closure_record_locks") or []),'operator_review_required':bool(latest.get('operator_review_required',False))},'latest_run':latest,'alerts':s.get('alerts') or [],'policy':s.get('policy') or dict(DEFAULT_POLICY),'last_context':s.get('last_context') or {},"financial_statement_issuances": s.get("financial_statement_issuances") or [],"lp_reporting_pack_releases": s.get("lp_reporting_pack_releases") or [],"audit_closure_record_locks": s.get("audit_closure_record_locks") or []}

def _band(score:float)->str:
    if score >= 98.0:
        return "AUDIT_CLOSURE_RELEASE_STRONG"
    if score >= 96.0:
        return "AUDIT_CLOSURE_RELEASE_CLEAR"
    if score >= 92.0:
        return "AUDIT_CLOSURE_RELEASE_WATCH"
    return "AUDIT_CLOSURE_RELEASE_REMEDIATION_REQUIRED"

def _evaluate(email:str,payload:dict)->dict:
    store=_load(email)
    policy={**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    ctx=_context(email)
    financial_statement_issuance_readiness = float(payload.get("financial_statement_issuance_readiness", 0.0) or 0.0)
    lp_reporting_pack_release_readiness = float(payload.get("lp_reporting_pack_release_readiness", 0.0) or 0.0)
    audit_closure_record_lock_readiness = float(payload.get("audit_closure_record_lock_readiness", 0.0) or 0.0)
    score=100.0
    reasons=[]
    alerts=[]
    def penalize(metric, minimum, weight, reason, code):
        nonlocal score
        if metric < minimum:
            score -= round((minimum-metric)*weight,2)
            reasons.append(reason)
            alerts.append(code)
    penalize(financial_statement_issuance_readiness, float(policy.get("minimum_financial_statement_issuance_readiness", 0.97)), 120.0, "financial statement issuance readiness is below policy", "FINANCIAL_STATEMENT_ISSUANCE_READINESS_WEAK")
    penalize(lp_reporting_pack_release_readiness, float(policy.get("minimum_lp_reporting_pack_release_readiness", 0.97)), 120.0, "lp reporting pack release readiness is below policy", "LP_REPORTING_PACK_RELEASE_READINESS_WEAK")
    penalize(audit_closure_record_lock_readiness, float(policy.get("minimum_audit_closure_record_lock_readiness", 0.97)), 120.0, "audit closure record lock readiness is below policy", "AUDIT_CLOSURE_RECORD_LOCK_READINESS_WEAK")
    if int(payload.get('pending_release_exceptions',0) or 0) > int(policy.get('maximum_pending_release_exceptions',0)):
        score -= 8.0 + (int(payload.get('pending_release_exceptions',0) or 0)-int(policy.get('maximum_pending_release_exceptions',0)))*2.0
        reasons.append('pending release exceptions exceed policy')
        alerts.append('PENDING_RELEASE_EXCEPTIONS_EXCEED_POLICY')
    if ctx.get("dep_a_summary",{}).get("posture") not in {"AUDIT_RELEASE_STRONG","AUDIT_RELEASE_CLEAR","AUDIT_RELEASE_WATCH"}:
        score -= 8.0
        reasons.append("audit release authorization posture must be established before final issuance")
        alerts.append("AUDIT_RELEASE_AUTHORIZATION_NOT_ESTABLISHED")
    if ctx.get("dep_b_summary",{}).get("posture") not in {"PERIOD_CLOSE_STRONG","PERIOD_CLOSE_CLEAR","PERIOD_CLOSE_WATCH"}:
        score -= 6.0
        reasons.append("period close certification posture must be established before final issuance")
        alerts.append("PERIOD_CLOSE_CERTIFICATION_NOT_ESTABLISHED")
    score=max(0.0, round(score,2))
    posture=_band(score)
    operator_review_required=bool(score < float(policy.get('minimum_score',96.0)) or int(payload.get('pending_release_exceptions',0) or 0) > 0)
    run={'run_id':f"qnt40023_{int(datetime.now(timezone.utc).timestamp())}",'captured_at':_now_iso(),"financial_statement_issuance_readiness": financial_statement_issuance_readiness,"lp_reporting_pack_release_readiness": lp_reporting_pack_release_readiness,"audit_closure_record_lock_readiness": audit_closure_record_lock_readiness,"pending_release_exceptions": int(payload.get("pending_release_exceptions",0) or 0),'score':score,'band':posture,'posture':posture,'reasons':reasons,'alerts':alerts,'operator_review_required':operator_review_required}
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

@router.post('/issue-financial-statements')
def issue_financial_statements(payload:dict=Body(...), user=Depends(_require_user)):
    email=user['email']
    store=_load(email)
    policy={**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    row=_create_row('financial_statement_issuance', payload)
    _append(store, 'financial_statement_issuances', row, int(policy.get('retain_cycles',365)))
    _save(email, store)
    return {'ok':True, 'financial_statement_issuance': row, 'summary': _summary_for_email(email)}

@router.post('/release-lp-reporting-pack')
def release_lp_reporting_pack(payload:dict=Body(...), user=Depends(_require_user)):
    email=user['email']
    store=_load(email)
    policy={**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    row=_create_row('lp_reporting_pack_release', payload)
    _append(store, 'lp_reporting_pack_releases', row, int(policy.get('retain_cycles',365)))
    _save(email, store)
    return {'ok':True, 'lp_reporting_pack_release': row, 'summary': _summary_for_email(email)}

@router.post('/lock-audit-closure-record')
def lock_audit_closure_record(payload:dict=Body(...), user=Depends(_require_user)):
    email=user['email']
    store=_load(email)
    policy={**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    row=_create_row('audit_closure_record_lock', payload)
    _append(store, 'audit_closure_record_locks', row, int(policy.get('retain_cycles',365)))
    _save(email, store)
    return {'ok':True, 'audit_closure_record_lock': row, 'summary': _summary_for_email(email)}
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
    issue_financial_statements({"statement_scope":"FY close","financial_statement_issuance_readiness":0.99}, user)
    release_lp_reporting_pack({"distribution_channel":"investor portal","lp_reporting_pack_release_readiness":0.99}, user)
    lock_audit_closure_record({"lock_scope":"FY close archive","audit_closure_record_lock_readiness":0.99}, user)
    run=_evaluate(email, {"financial_statement_issuance_readiness": 0.99, "lp_reporting_pack_release_readiness": 0.99, "audit_closure_record_lock_readiness": 0.99, "pending_release_exceptions": 0})
    return {'ok':True, 'run':run, 'summary':_summary_for_email(email)}
