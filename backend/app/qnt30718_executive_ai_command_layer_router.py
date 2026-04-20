from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, time
router = APIRouter(tags=["executive-ai-command-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "executive_ai_command_layer"
DEFAULT_POLICY = {"retain_commands": 180, "minimum_command_score": 88.0, "minimum_conviction_score": 80.0, "minimum_explainability_score": 82.0, "minimum_capital_readiness_score": 84.0, "maximum_open_exceptions": 1, "require_operator_clear": True, "require_release_clear": True, "require_safety_clear": True, "require_recovery_clear": True, "require_liquidity_support": True, "require_regime_support": True, "require_reporting_clear": True, "require_autonomous_fund_mode_ready": True}

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _operator():
    from backend.app import qnt30702_operator_command_console_router as operator
    return operator

def _release():
    from backend.app import qnt30700_institutional_release_control_router as release
    return release

def _safety():
    from backend.app import qnt30703_live_broker_safety_layer_router as safety
    return safety

def _fund_admin():
    from backend.app import qnt30705_fund_admin_control_center_router as admin
    return admin

def _forensic():
    from backend.app import qnt30706_forensic_audit_system_router as forensic
    return forensic

def _recovery():
    from backend.app import qnt30707_recovery_system_router as recovery
    return recovery

def _strategy():
    from backend.app import qnt30708_strategy_evolution_engine_router as strategy
    return strategy

def _liquidity():
    from backend.app import qnt30709_liquidity_intelligence_system_router as liquidity
    return liquidity

def _regime():
    from backend.app import qnt30710_market_regime_intelligence_system_router as regime
    return regime

def _rotation():
    from backend.app import qnt30711_capital_rotation_command_system_router as rotation
    return rotation

def _defense():
    from backend.app import qnt30712_defensive_systems_command_layer_router as defense
    return defense

def _autonomy():
    from backend.app import qnt30713_autonomous_allocation_governance_layer_router as autonomy
    return autonomy

def _transparency():
    from backend.app import qnt30714_investor_transparency_engine_router as transparency
    return transparency

def _reporting():
    from backend.app import qnt30715_reporting_disclosure_automation_layer_router as reporting
    return reporting

def _afm_ready():
    from backend.app import qnt30716_autonomous_fund_mode_readiness_layer_router as afm
    return afm

def _growth():
    from backend.app import qnt30717_self_growing_capital_engine_router as growth
    return growth

def _safe(v:str)->str:
    return hashlib.sha256((v or "").strip().lower().encode()).hexdigest()[:24]

def _path(email:str)->Path:
    ENGINE_DIR.mkdir(parents=True, exist_ok=True)
    return ENGINE_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _now_ts()->int: return int(time.time())

def _now_iso()->str: return datetime.now(timezone.utc).isoformat()

def _append(store,key,row,retain):
    arr=list(store.get(key) or [])
    arr.insert(0,row)
    store[key]=arr[:max(int(retain or 1),1)]

def _load(email:str)->dict:
    path=_path(email)
    if not path.exists():
        data={"email":email,"policy":dict(DEFAULT_POLICY),"commands":[],"exceptions":[],"command_book":[],"last_context":{},"latest_command":None}
        path.write_text(json.dumps(data,indent=2),encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))

def _save(email,data): _path(email).write_text(json.dumps(data,indent=2),encoding="utf-8")

def _cross_system_context(email:str)->dict:
    operator=_operator()._summary_for_email(email); release=_release()._summary_for_email(email); safety=_safety()._summary_for_email(email); admin=_fund_admin()._summary_for_email(email); forensic=_forensic()._summary_for_email(email); recovery=_recovery()._summary_for_email(email); strategy=_strategy()._summary_for_email(email); liquidity=_liquidity()._summary_for_email(email); regime=_regime()._summary_for_email(email); rotation=_rotation()._summary_for_email(email); defense=_defense()._summary_for_email(email); autonomy=_autonomy()._summary_for_email(email); transparency=_transparency()._summary_for_email(email); reporting=_reporting()._summary_for_email(email); afm=_afm_ready()._summary_for_email(email); growth=_growth()._summary_for_email(email)
    return {"captured_at":_now_iso(),"operator":{"posture":(operator.get("operator_console_status") or {}).get("posture"),"override_required":bool((operator.get("operator_console_status") or {}).get("override_required",False))},"release":{"posture":(release.get("institutional_release_control_status") or {}).get("posture")},"safety":{"posture":(safety.get("safety_layer_status") or {}).get("posture"),"production_ready":(safety.get("safety_layer_status") or {}).get("production_ready")},"fund_admin":{"readiness":(admin.get("fund_admin_status") or {}).get("readiness"),"aum":float(admin.get("aum") or 0.0)},"forensic":{"posture":(forensic.get("forensic_status") or {}).get("posture"),"critical_open_count":(forensic.get("forensic_status") or {}).get("critical_open_count")},"recovery":{"posture":(recovery.get("recovery_status") or {}).get("posture"),"safe_mode":(recovery.get("recovery_status") or {}).get("safe_mode"),"valid_state":(recovery.get("current_validation") or {}).get("valid_state")},"strategy":{"posture":(strategy.get("strategy_evolution_status") or {}).get("posture"),"latest_score":(strategy.get("strategy_evolution_status") or {}).get("latest_score")},"liquidity":{"posture":(liquidity.get("liquidity_intelligence_status") or {}).get("posture"),"latest_score":(liquidity.get("liquidity_intelligence_status") or {}).get("latest_score")},"regime":{"posture":(regime.get("market_regime_intelligence_status") or {}).get("posture"),"latest_score":(regime.get("market_regime_intelligence_status") or {}).get("latest_score")},"rotation":{"posture":(rotation.get("capital_rotation_command_status") or {}).get("posture"),"latest_score":(rotation.get("capital_rotation_command_status") or {}).get("latest_score")},"defense":{"posture":(defense.get("defensive_systems_status") or {}).get("posture"),"latest_score":(defense.get("defensive_systems_status") or {}).get("latest_score")},"autonomy":{"posture":(autonomy.get("autonomous_allocation_governance_status") or {}).get("posture"),"latest_score":(autonomy.get("autonomous_allocation_governance_status") or {}).get("latest_score")},"transparency":{"posture":(transparency.get("investor_transparency_status") or {}).get("posture"),"latest_score":(transparency.get("investor_transparency_status") or {}).get("latest_score")},"reporting":{"posture":(reporting.get("reporting_disclosure_automation_status") or {}).get("posture"),"latest_score":(reporting.get("reporting_disclosure_automation_status") or {}).get("latest_score")},"autonomous_fund_mode":{"posture":(afm.get("autonomous_fund_mode_readiness_status") or {}).get("posture"),"latest_score":(afm.get("autonomous_fund_mode_readiness_status") or {}).get("latest_score"),"needs_operator_review":(afm.get("autonomous_fund_mode_readiness_status") or {}).get("needs_operator_review")},"growth":{"posture":(growth.get("self_growing_capital_status") or {}).get("posture"),"latest_score":(growth.get("self_growing_capital_status") or {}).get("latest_score"),"band":(growth.get("self_growing_capital_status") or {}).get("compounding_band")}}

def _score_command(payload,ctx,policy):
    conviction=float(payload.get("conviction_score") or 0.0); explainability=float(payload.get("explainability_score") or 0.0); capital_readiness=float(payload.get("capital_readiness_score") or 0.0); scenario=float(payload.get("scenario_coverage_pct") or 0.0); cross_system=float(payload.get("cross_system_alignment_score") or 0.0); urgency=float(payload.get("urgency_score") or 0.0); blockers=[]; needs_review=False
    if conviction < float(policy.get("minimum_conviction_score") or 0.0): blockers.append("conviction-below-threshold")
    if explainability < float(policy.get("minimum_explainability_score") or 0.0): blockers.append("explainability-below-threshold")
    if capital_readiness < float(policy.get("minimum_capital_readiness_score") or 0.0): blockers.append("capital-readiness-below-threshold")
    if int(payload.get("open_exceptions") or 0) > int(policy.get("maximum_open_exceptions") or 0): blockers.append("too-many-open-exceptions")
    if policy.get("require_operator_clear") and ctx.get("operator",{}).get("posture") not in ("CLEAR","READY","ACTIVE"): blockers.append("operator-not-clear")
    if policy.get("require_release_clear") and ctx.get("release",{}).get("posture") not in ("READY","CLEAR","ACTIVE"): blockers.append("release-not-clear")
    if policy.get("require_safety_clear") and ctx.get("safety",{}).get("posture") not in ("READY","SAFE","CLEAR"): blockers.append("safety-not-clear")
    if policy.get("require_recovery_clear") and (ctx.get("recovery",{}).get("safe_mode") or not ctx.get("recovery",{}).get("valid_state")): blockers.append("recovery-not-clear")
    if policy.get("require_liquidity_support") and ctx.get("liquidity",{}).get("posture") not in ("READY","CLEAR","FAVORABLE"): blockers.append("liquidity-not-supportive")
    if policy.get("require_regime_support") and ctx.get("regime",{}).get("posture") not in ("READY","CLEAR","FAVORABLE"): blockers.append("regime-not-supportive")
    if policy.get("require_reporting_clear") and ctx.get("reporting",{}).get("posture") not in ("READY","CLEAR","AUTOMATED"): blockers.append("reporting-not-clear")
    if policy.get("require_autonomous_fund_mode_ready") and ctx.get("autonomous_fund_mode",{}).get("posture") not in ("READY","CLEAR","APPROVED"): blockers.append("autonomous-fund-mode-not-ready")
    weighted=conviction*0.24+explainability*0.18+capital_readiness*0.20+scenario*0.14+cross_system*0.16+urgency*0.08
    score=round(max(0.0,min(100.0,weighted)),2)
    if payload.get("live_execute") and (ctx.get("operator",{}).get("override_required") or (urgency>=92 and score<95)): needs_review=True
    posture="APPROVED"
    if blockers: posture="BLOCKED"
    elif needs_review: posture="OPERATOR_REVIEW"
    elif score < float(policy.get("minimum_command_score") or 0.0): posture="WATCH"
    band="HOLD"
    if posture == "APPROVED" and score >= 93: band="ALLOCATE"
    elif posture in ("APPROVED","WATCH") and score >= 88: band="TILT"
    elif posture == "BLOCKED": band="DEFEND"
    return {"score":score,"posture":posture,"recommended_band":band,"operator_review_required":needs_review,"blockers":blockers}

def _summary_for_email(email:str)->dict:
    store=_load(email); latest=store.get("latest_command") or {}
    return {"executive_ai_command_layer_status":{"posture":(latest.get("evaluation") or {}).get("posture","IDLE"),"latest_score":(latest.get("evaluation") or {}).get("score"),"recommended_band":(latest.get("evaluation") or {}).get("recommended_band"),"command_count":len(store.get("commands") or []),"exception_count":len(store.get("exceptions") or [])},"latest_command":latest,"policy":store.get("policy") or dict(DEFAULT_POLICY),"command_book":store.get("command_book") or [],"exceptions":store.get("exceptions") or [],"last_context":store.get("last_context") or {}}

@router.get("/api/executive-ai-command-layer/summary")
def summary(session=Depends(_require_user)): return _summary_for_email(session["email"])

@router.post("/api/executive-ai-command-layer/evaluate")
def evaluate(payload:dict=Body(...), session=Depends(_require_user)):
    email=session["email"]; store=_load(email); policy=store.get("policy") or dict(DEFAULT_POLICY); ctx=_cross_system_context(email); evaluation=_score_command(payload,ctx,policy); command={"command_id":f"exec-ai-{_now_ts()}","created_at":_now_iso(),"command_scope":payload.get("command_scope") or "GLOBAL_EXECUTIVE_COMMAND","capital_directive":payload.get("capital_directive") or "preserve-and-allocate","live_execute":bool(payload.get("live_execute",False)),"inputs":payload,"context":ctx,"evaluation":evaluation}; _append(store,"commands",command,int(policy.get("retain_commands") or 180)); _append(store,"command_book",{"entry_id":f"exec-ai-book-{_now_ts()}","created_at":_now_iso(),"command_id":command["command_id"],"directive":command["capital_directive"],"posture":evaluation.get("posture"),"score":evaluation.get("score"),"recommended_band":evaluation.get("recommended_band")},int(policy.get("retain_commands") or 180));
    if evaluation.get("posture") in ("BLOCKED","OPERATOR_REVIEW","WATCH"): _append(store,"exceptions",{"exception_id":f"exec-ai-ex-{_now_ts()}","created_at":_now_iso(),"command_id":command["command_id"],"posture":evaluation.get("posture"),"score":evaluation.get("score"),"blockers":evaluation.get("blockers") or []},int(policy.get("retain_commands") or 180))
    store["latest_command"]=command; store["last_context"]=ctx; _save(email,store); return {"ok":True,"command":command,"summary":_summary_for_email(email)}

@router.post("/api/executive-ai-command-layer/policy")
def update_policy(payload:dict=Body(...), session=Depends(_require_user)):
    email=session["email"]; store=_load(email); policy=store.get("policy") or dict(DEFAULT_POLICY)
    for key in DEFAULT_POLICY:
        if key in payload: policy[key]=payload[key]
    store["policy"]=policy; _save(email,store); return {"ok":True,"policy":policy}

@router.post("/api/executive-ai-command-layer/bootstrap-demo")
def bootstrap_demo(session=Depends(_require_user)):
    email=session["email"]; store=_load(email); payload={"command_scope":"EXECUTIVE_CAPITAL_COMMAND","capital_directive":"compound-with-controlled-rotation","conviction_score":92.0,"explainability_score":90.0,"capital_readiness_score":91.0,"scenario_coverage_pct":89.0,"cross_system_alignment_score":93.0,"urgency_score":78.0,"open_exceptions":0,"live_execute":False}; ctx=_cross_system_context(email); policy=store.get("policy") or dict(DEFAULT_POLICY); evaluation=_score_command(payload,ctx,policy); command={"command_id":f"exec-ai-{_now_ts()}","created_at":_now_iso(),"command_scope":payload["command_scope"],"capital_directive":payload["capital_directive"],"live_execute":False,"inputs":payload,"context":ctx,"evaluation":evaluation}; _append(store,"commands",command,int(policy.get("retain_commands") or 180)); _append(store,"command_book",{"entry_id":f"exec-ai-book-{_now_ts()}","created_at":_now_iso(),"command_id":command["command_id"],"directive":command["capital_directive"],"posture":evaluation.get("posture"),"score":evaluation.get("score"),"recommended_band":evaluation.get("recommended_band")},int(policy.get("retain_commands") or 180)); store["latest_command"]=command; store["last_context"]=ctx; _save(email,store); return {"ok":True,"summary":_summary_for_email(email)}
