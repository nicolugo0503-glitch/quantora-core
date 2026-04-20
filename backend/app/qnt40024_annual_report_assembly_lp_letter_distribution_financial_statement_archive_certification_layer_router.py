from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json

router = APIRouter(prefix="/api/annual-report-assembly-lp-letter-distribution-financial-statement-archive-certification-layer", tags=["annual-report-assembly-lp-letter-distribution-financial-statement-archive-certification-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ENGINE_DIR = PROJECT_DIR / "backend" / "artifacts" / "annual_report_assembly_lp_letter_distribution_financial_statement_archive_certification_layer"
DEFAULT_POLICY = {'retain_cycles': 365, 'minimum_score': 96.0, 'minimum_annual_report_assembly_readiness': 0.97, 'minimum_lp_letter_distribution_readiness': 0.97, 'minimum_archive_certification_readiness': 0.97, 'maximum_pending_archive_exceptions': 0}

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _require_user():
    return _mu()._require_session()

def _dep_a():
    from backend.app import qnt40023_financial_statement_issuance_lp_reporting_pack_release_audit_closure_record_lock_layer_router as module
    return module

def _dep_b():
    from backend.app import qnt30766_regulatory_records_retention_legal_hold_supervisory_retrieval_command_layer_router as module
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
        data={"email":email,"policy":dict(DEFAULT_POLICY),"runs":[],"alerts":[],"annual_report_assemblies":[],"lp_letter_distributions":[],"archive_certifications":[],"latest_run":None,"last_context":{}}
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
    return {'captured_at':_now_iso(), 'dep_a_summary':{'posture':((a.get('financial_statement_issuance_lp_reporting_pack_release_audit_closure_record_lock_layer_status') or {}).get('posture')), 'score':la.get('score')}, 'dep_b_summary':{'posture':((b.get('regulatory_records_retention_legal_hold_supervisory_retrieval_status') or {}).get('posture')), 'score':lb.get('score')}}

def _summary_for_email(email:str)->dict:
    s=_load(email)
    latest=s.get('latest_run') or {}
    return {'annual_report_assembly_lp_letter_distribution_financial_statement_archive_certification_layer_status':{'posture':latest.get('posture','UNINITIALIZED'),'latest_score':latest.get('score'),'band':latest.get('band','UNSET'),'run_count':len(s.get('runs') or []),'alert_count':len(s.get('alerts') or []),"annual_report_assemblie_count":len(s.get("annual_report_assemblies") or []),"lp_letter_distribution_count":len(s.get("lp_letter_distributions") or []),"archive_certification_count":len(s.get("archive_certifications") or []),'operator_review_required':bool(latest.get('operator_review_required',False))},'latest_run':latest,'alerts':s.get('alerts') or [],'policy':s.get('policy') or dict(DEFAULT_POLICY),'last_context':s.get('last_context') or {},"annual_report_assemblies": s.get("annual_report_assemblies") or [],"lp_letter_distributions": s.get("lp_letter_distributions") or [],"archive_certifications": s.get("archive_certifications") or []}

def _band(score:float)->str:
    if score >= 98.0:
        return "ANNUAL_REPORT_RELEASE_STRONG"
    if score >= 96.0:
        return "ANNUAL_REPORT_RELEASE_CLEAR"
    if score >= 92.0:
        return "ANNUAL_REPORT_RELEASE_WATCH"
    return "ANNUAL_REPORT_RELEASE_REMEDIATION_REQUIRED"

def _evaluate(email:str,payload:dict)->dict:
    store=_load(email)
    policy={**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    ctx=_context(email)
    annual_report_assembly_readiness = float(payload.get("annual_report_assembly_readiness", 0.0) or 0.0)
    lp_letter_distribution_readiness = float(payload.get("lp_letter_distribution_readiness", 0.0) or 0.0)
    archive_certification_readiness = float(payload.get("archive_certification_readiness", 0.0) or 0.0)
    score=100.0
    reasons=[]
    alerts=[]
    def penalize(metric, minimum, weight, reason, code):
        nonlocal score
        if metric < minimum:
            score -= round((minimum-metric)*weight,2)
            reasons.append(reason)
            alerts.append(code)
    penalize(annual_report_assembly_readiness, float(policy.get("minimum_annual_report_assembly_readiness", 0.97)), 120.0, "annual report assembly readiness is below policy", "ANNUAL_REPORT_ASSEMBLY_READINESS_WEAK")
    penalize(lp_letter_distribution_readiness, float(policy.get("minimum_lp_letter_distribution_readiness", 0.97)), 120.0, "lp letter distribution readiness is below policy", "LP_LETTER_DISTRIBUTION_READINESS_WEAK")
    penalize(archive_certification_readiness, float(policy.get("minimum_archive_certification_readiness", 0.97)), 120.0, "archive certification readiness is below policy", "ARCHIVE_CERTIFICATION_READINESS_WEAK")
    if int(payload.get('pending_archive_exceptions',0) or 0) > int(policy.get('maximum_pending_archive_exceptions',0)):
        score -= 8.0 + (int(payload.get('pending_archive_exceptions',0) or 0)-int(policy.get('maximum_pending_archive_exceptions',0)))*2.0
        reasons.append('pending archive exceptions exceed policy')
        alerts.append('PENDING_ARCHIVE_EXCEPTIONS_EXCEED_POLICY')
    if ctx.get("dep_a_summary",{}).get("posture") not in {"AUDIT_CLOSURE_RELEASE_STRONG","AUDIT_CLOSURE_RELEASE_CLEAR","AUDIT_CLOSURE_RELEASE_WATCH"}:
        score -= 8.0
        reasons.append("audit closure release posture must be established before annual report issuance")
        alerts.append("AUDIT_CLOSURE_RELEASE_NOT_ESTABLISHED")
    if ctx.get("dep_b_summary",{}).get("posture") in {None, "UNINITIALIZED"}:
        score -= 4.0
        reasons.append("records retention evidence must exist before archive certification")
        alerts.append("RECORDS_RETENTION_EVIDENCE_MISSING")
    score=max(0.0, round(score,2))
    posture=_band(score)
    operator_review_required=bool(score < float(policy.get('minimum_score',96.0)) or int(payload.get('pending_archive_exceptions',0) or 0) > 0)
    run={'run_id':f"qnt40024_{int(datetime.now(timezone.utc).timestamp())}",'captured_at':_now_iso(),"annual_report_assembly_readiness": annual_report_assembly_readiness,"lp_letter_distribution_readiness": lp_letter_distribution_readiness,"archive_certification_readiness": archive_certification_readiness,"pending_archive_exceptions": int(payload.get("pending_archive_exceptions",0) or 0),'score':score,'band':posture,'posture':posture,'reasons':reasons,'alerts':alerts,'operator_review_required':operator_review_required}
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

@router.post('/assemble-annual-report')
def assemble_annual_report(payload:dict=Body(...), user=Depends(_require_user)):
    email=user['email']
    store=_load(email)
    policy={**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    row=_create_row('annual_report_assemblie', payload)
    _append(store, 'annual_report_assemblies', row, int(policy.get('retain_cycles',365)))
    _save(email, store)
    return {'ok':True, 'annual_report_assembly': row, 'summary': _summary_for_email(email)}

@router.post('/distribute-lp-letter')
def distribute_lp_letter(payload:dict=Body(...), user=Depends(_require_user)):
    email=user['email']
    store=_load(email)
    policy={**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    row=_create_row('lp_letter_distribution', payload)
    _append(store, 'lp_letter_distributions', row, int(policy.get('retain_cycles',365)))
    _save(email, store)
    return {'ok':True, 'lp_letter_distribution': row, 'summary': _summary_for_email(email)}

@router.post('/certify-financial-statement-archive')
def certify_financial_statement_archive(payload:dict=Body(...), user=Depends(_require_user)):
    email=user['email']
    store=_load(email)
    policy={**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    row=_create_row('archive_certification', payload)
    _append(store, 'archive_certifications', row, int(policy.get('retain_cycles',365)))
    _save(email, store)
    return {'ok':True, 'archive_certification': row, 'summary': _summary_for_email(email)}
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
    assemble_annual_report({"report_scope":"annual report","annual_report_assembly_readiness":0.99}, user)
    distribute_lp_letter({"distribution_channel":"investor notice and secure delivery","lp_letter_distribution_readiness":0.99}, user)
    certify_financial_statement_archive({"archive_scope":"FY close archive","archive_certification_readiness":0.99}, user)
    run=_evaluate(email, {"annual_report_assembly_readiness": 0.99, "lp_letter_distribution_readiness": 0.99, "archive_certification_readiness": 0.99, "pending_archive_exceptions": 0})
    return {'ok':True, 'run':run, 'summary':_summary_for_email(email)}
