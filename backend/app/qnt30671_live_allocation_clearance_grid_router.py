from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, time
router = APIRouter(tags=["live-allocation-clearance-grid"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
CLEARANCE_DIR = ARTIFACTS_DIR / "live_allocation_clearance_grid"
DEFAULT_POLICY = {"priority_clearance_case_count": 8, "minimum_clearance_readiness_score": 86.0, "minimum_clearance_authority_score": 84.0, "minimum_release_alignment_score": 82.0, "minimum_governance_alignment_score": 80.0, "maximum_clearance_stress_score": 24.0}
def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu
def _mesh():
    from backend.app import qnt30670_live_allocation_release_authority_mesh_router as mod
    return mod
def _control():
    from backend.app import qnt30666_live_allocation_control_tower_router as mod
    return mod
def _governance():
    from backend.app import qnt30662_execution_governance_command_router as mod
    return mod
def _compliance():
    from backend.app import qnt30652_institutional_compliance_router as mod
    return mod
def _safe(v:str)->str:
    return hashlib.sha256((v or "").strip().lower().encode()).hexdigest()[:24]
def _path(email:str)->Path:
    CLEARANCE_DIR.mkdir(parents=True, exist_ok=True); return CLEARANCE_DIR / f"{_safe(email)}.json"
def _require_user():
    return _mu()._require_session()
def _now_ts()->int:
    return int(time.time())
def _now_iso()->str:
    return datetime.now(timezone.utc).isoformat()
def _round_money(v)->float:
    return round(float(v or 0.0),2)
def _round_pct(v)->float:
    return round(float(v or 0.0),4)
def _load(email:str)->dict:
    path=_path(email)
    if not path.exists():
        data={"email":email,"policy":dict(DEFAULT_POLICY),"runs":[],"created_at":_now_ts(),"updated_at":_now_ts()}
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))
def _save(email:str,data:dict)->dict:
    data["updated_at"]=_now_ts(); _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8"); return data
def _safe_summary(builder,*args,fallback:dict):
    try:
        return builder(*args)
    except Exception:
        return dict(fallback)
def _clearance_book(dependencies:dict, policy:dict)->list[dict]:
    mesh=dependencies["mesh"]; control=dependencies["control"]; governance=dependencies["governance"]; compliance=dependencies["compliance"]
    mesh_book=mesh.get("mesh_book") or []; mesh_matrix=mesh.get("mesh_matrix") or []
    control_book=control.get("allocation_book") or []; control_matrix=control.get("allocation_matrix") or []
    governance_matrix=governance.get("command_matrix") or []; compliance_matrix=compliance.get("release_matrix") or []
    count=max(int(policy.get("priority_clearance_case_count") or 8),4); base_len=max(len(mesh_book),len(control_book),len(governance_matrix),len(compliance_matrix),1); out=[]
    for idx in range(min(count, max(base_len,count))):
        mb=mesh_book[idx % max(len(mesh_book),1)] if mesh_book else {}
        mm=mesh_matrix[idx % max(len(mesh_matrix),1)] if mesh_matrix else {}
        cb=control_book[idx % max(len(control_book),1)] if control_book else {}
        cm=control_matrix[idx % max(len(control_matrix),1)] if control_matrix else {}
        gm=governance_matrix[idx % max(len(governance_matrix),1)] if governance_matrix else {}
        xp=compliance_matrix[idx % max(len(compliance_matrix),1)] if compliance_matrix else {}
        readiness=min(100.0,float(mb.get("mesh_readiness_score") or 0.0)*0.24 + float(mm.get("mesh_authority_score") or 0.0)*0.18 + float(cm.get("allocation_authority_score") or 0.0)*0.14 + float(gm.get("authority_score") or 0.0)*0.12 + float(xp.get("release_authority_score") or 0.0)*0.10 + 8.0)
        authority=min(100.0,readiness*0.34 + float(mm.get("mesh_authority_score") or 0.0)*0.18 + float(cm.get("allocation_authority_score") or 0.0)*0.14 + float(gm.get("authority_score") or 0.0)*0.10 + 6.0)
        release_alignment=min(100.0,float(mm.get("mesh_authority_score") or 0.0)*0.32 + float(mb.get("release_alignment_score") or 0.0)*0.22 + float(xp.get("release_authority_score") or 0.0)*0.14 + 8.0)
        governance_alignment=min(100.0,float(gm.get("authority_score") or 0.0)*0.34 + float(cm.get("allocation_authority_score") or 0.0)*0.20 + float(mm.get("mesh_authority_score") or 0.0)*0.12 + 8.0)
        stress=max(4.0,35.0 - readiness*0.13 - authority*0.10 - release_alignment*0.08 - governance_alignment*0.06 + idx*0.55)
        status="approve"
        if release_alignment < float(policy.get("minimum_release_alignment_score") or 82.0) or governance_alignment < float(policy.get("minimum_governance_alignment_score") or 80.0): status="review"
        if authority < float(policy.get("minimum_clearance_authority_score") or 84.0) or stress > float(policy.get("maximum_clearance_stress_score") or 24.0): status="hold"
        out.append({"clearance_case_id":f"lacg_{idx+1:02d}","allocator_name":mb.get("allocator_name") or cb.get("allocator_name") or f"Allocator {idx+1}","strategy_id":mb.get("strategy_id") or cb.get("strategy_id") or f"STRAT_{idx+1:02d}","product_id":mb.get("product_id") or cb.get("product_id") or f"QNT_LACG_{idx+1:02d}","jurisdiction":mb.get("jurisdiction") or cb.get("jurisdiction") or "multi-jurisdiction","capital_target_millions":_round_money(mb.get("capital_target_millions") or cb.get("capital_target_millions") or 0.0),"clearance_readiness_score":_round_pct(readiness),"clearance_authority_score":_round_pct(authority),"release_alignment_score":_round_pct(release_alignment),"governance_alignment_score":_round_pct(governance_alignment),"clearance_stress_score":_round_pct(stress),"clearance_status":status})
    return out
def _clearance_lanes(book:list[dict], policy:dict)->list[dict]:
    out=[]
    for idx,row in enumerate(book):
        lane_score=min(100.0,float(row.get("clearance_readiness_score") or 0.0)*0.34 + float(row.get("clearance_authority_score") or 0.0)*0.24 + float(row.get("release_alignment_score") or 0.0)*0.14 + float(row.get("governance_alignment_score") or 0.0)*0.12 + 6.0)
        status="greenlight" if lane_score >= float(policy.get("minimum_clearance_readiness_score") or 86.0) and row.get("clearance_status")=="approve" else ("hold" if row.get("clearance_status")=="hold" else "review")
        out.append({"lane_id":f"lacl_{idx+1:02d}","allocator_name":row.get("allocator_name"),"strategy_id":row.get("strategy_id"),"clearance_window":"live allocation clearance command window","clearance_lane_score":_round_pct(lane_score),"lane_status":status})
    return out
def _clearance_matrix(book:list[dict], lanes:list[dict], policy:dict)->list[dict]:
    out=[]
    for idx,row in enumerate(book):
        lane=lanes[idx % max(len(lanes),1)] if lanes else {}
        authority_score=min(100.0,float(row.get("clearance_readiness_score") or 0.0)*0.30 + float(row.get("clearance_authority_score") or 0.0)*0.24 + float(row.get("release_alignment_score") or 0.0)*0.14 + float(row.get("governance_alignment_score") or 0.0)*0.12 + float(lane.get("clearance_lane_score") or 0.0)*0.12 + 4.0)
        status="approve" if authority_score >= float(policy.get("minimum_clearance_authority_score") or 84.0) and lane.get("lane_status")=="greenlight" and row.get("clearance_status")=="approve" else ("hold" if row.get("clearance_status")=="hold" else "review")
        out.append({"matrix_id":f"lacmx_{idx+1:02d}","allocator_name":row.get("allocator_name"),"strategy_id":row.get("strategy_id"),"product_id":row.get("product_id"),"jurisdiction":row.get("jurisdiction"),"capital_target_millions":row.get("capital_target_millions"),"clearance_authority_score":_round_pct(authority_score),"clearance_authority_status":status})
    return out
def _clearance_queue(book:list[dict], lanes:list[dict], matrix:list[dict])->list[dict]:
    out=[]
    for idx,row in enumerate(book):
        lane=lanes[idx % max(len(lanes),1)] if lanes else {}
        authority=matrix[idx % max(len(matrix),1)] if matrix else {}
        status="approve"
        if authority.get("clearance_authority_status")=="review" or lane.get("lane_status")=="review" or row.get("clearance_status")=="review": status="review"
        if authority.get("clearance_authority_status")=="hold" or row.get("clearance_status")=="hold": status="hold"
        next_action="clear live allocation release and authorize governed execution continuation"
        if status=="review": next_action="refresh governance proof, release evidence, and committee alignment before issuing clearance"
        if status=="hold": next_action="freeze clearance, escalate to institutional oversight, and block live release expansion"
        out.append({"queue_id":f"lacq_{idx+1:02d}","allocator_name":row.get("allocator_name"),"strategy_id":row.get("strategy_id"),"product_id":row.get("product_id"),"jurisdiction":row.get("jurisdiction"),"capital_target_millions":row.get("capital_target_millions"),"next_action":next_action,"owner":"Live Allocation Clearance Grid","queue_status":status})
    return out
def _overview(dependencies:dict, book:list[dict], lanes:list[dict], matrix:list[dict], queue:list[dict])->dict:
    mesh_overview=dependencies["mesh"].get("live_allocation_release_overview") or {}
    control_overview=dependencies["control"].get("live_allocation_overview") or {}
    governance_overview=dependencies["governance"].get("execution_governance_overview") or {}
    compliance_overview=dependencies["compliance"].get("institutional_compliance_overview") or {}
    total_capital=sum(float(x.get("capital_target_millions") or 0.0) for x in book); approve_count=len([x for x in queue if x.get("queue_status")=="approve"]); review_count=len([x for x in queue if x.get("queue_status")=="review"]); hold_count=len([x for x in queue if x.get("queue_status")=="hold"]); green_count=len([x for x in lanes if x.get("lane_status")=="greenlight"]); avg_readiness=sum(float(x.get("clearance_readiness_score") or 0.0) for x in book)/max(len(book),1); avg_authority=sum(float(x.get("clearance_authority_score") or 0.0) for x in book)/max(len(book),1); avg_release=sum(float(x.get("release_alignment_score") or 0.0) for x in book)/max(len(book),1); avg_governance=sum(float(x.get("governance_alignment_score") or 0.0) for x in book)/max(len(book),1); avg_stress=sum(float(x.get("clearance_stress_score") or 0.0) for x in book)/max(len(book),1)
    score=min(100.0,avg_readiness*0.26 + avg_authority*0.22 + avg_release*0.14 + avg_governance*0.12 + (100.0-avg_stress)*0.12 + float(control_overview.get("live_allocation_score") or 76.0)*0.08 + float(mesh_overview.get("live_allocation_release_score") or 78.0)*0.06)
    posture="live-allocation-clear-ready"
    if hold_count: posture="live-allocation-clear-constrained"
    elif review_count > approve_count: posture="live-allocation-clear-reviewing"
    return {"clearance_capital_millions":_round_money(total_capital),"approve_count":approve_count,"review_count":review_count,"hold_count":hold_count,"greenlight_lane_count":green_count,"average_clearance_readiness":_round_pct(avg_readiness),"average_clearance_authority":_round_pct(avg_authority),"average_release_alignment":_round_pct(avg_release),"average_governance_alignment":_round_pct(avg_governance),"average_clearance_stress":_round_pct(avg_stress),"live_allocation_clearance_score":_round_pct(score),"live_allocation_clearance_posture":posture,"live_allocation_release_posture":mesh_overview.get("live_allocation_release_posture"),"live_allocation_posture":control_overview.get("live_allocation_posture"),"execution_governance_posture":governance_overview.get("execution_governance_posture"),"institutional_compliance_posture":compliance_overview.get("institutional_compliance_posture")}
def _actions(overview:dict, queue:list[dict], matrix:list[dict])->list[str]:
    actions=[]
    if overview.get("live_allocation_clearance_posture") != "live-allocation-clear-ready": actions.append("Tighten release evidence, governance alignment, and oversight proof before issuing live clearance.")
    approves=[x for x in queue if x.get("queue_status")=="approve"][:3]
    if approves: actions.append("Authorize live clearance package for " + ", ".join(x.get("allocator_name") for x in approves) + ".")
    reviews=[x for x in queue if x.get("queue_status")=="review"]
    if reviews: actions.append(f"Review {len(reviews)} live clearance cases before authorizing additional scale-up.")
    holds=[x for x in matrix if x.get("clearance_authority_status")=="hold"]
    if holds: actions.append("Hold live clearance package for " + ", ".join(x.get("allocator_name") for x in holds[:2]) + ".")
    return actions
def _build_summary(email:str):
    store=_load(email); policy=store.get("policy") or dict(DEFAULT_POLICY)
    mesh=_safe_summary(_mesh()._build_summary, email, fallback={"live_allocation_release_overview":{"live_allocation_release_score":76.0,"live_allocation_release_posture":"live-allocation-release-building"},"mesh_book":[],"mesh_matrix":[],"mesh_queue":[]})
    control=_safe_summary(_control()._build_summary, email, fallback={"live_allocation_overview":{"live_allocation_score":74.0,"live_allocation_posture":"live-allocation-building"},"allocation_book":[],"allocation_matrix":[]})
    governance=_safe_summary(_governance()._build_summary, email, fallback={"execution_governance_overview":{"execution_governance_score":75.0,"execution_governance_posture":"execution-governance-building"},"command_matrix":[]})
    compliance=_safe_summary(_compliance()._build_summary, email, fallback={"institutional_compliance_overview":{"institutional_compliance_score":77.0,"institutional_compliance_posture":"institutional-compliance-building"},"release_matrix":[]})
    dependencies={"mesh":mesh,"control":control,"governance":governance,"compliance":compliance}; book=_clearance_book(dependencies,policy); lanes=_clearance_lanes(book,policy); matrix=_clearance_matrix(book,lanes,policy); queue=_clearance_queue(book,lanes,matrix); overview=_overview(dependencies,book,lanes,matrix,queue)
    return {"mission":"QNT30671","generated_at":_now_iso(),"policy":policy,"live_allocation_clearance_overview":overview,"clearance_book":book,"clearance_lanes":lanes,"clearance_matrix":matrix,"clearance_queue":queue,"clearance_dependencies":{"live_allocation_release_posture":(mesh.get("live_allocation_release_overview") or {}).get("live_allocation_release_posture"),"live_allocation_release_score":(mesh.get("live_allocation_release_overview") or {}).get("live_allocation_release_score"),"live_allocation_posture":(control.get("live_allocation_overview") or {}).get("live_allocation_posture"),"live_allocation_score":(control.get("live_allocation_overview") or {}).get("live_allocation_score"),"execution_governance_posture":(governance.get("execution_governance_overview") or {}).get("execution_governance_posture"),"execution_governance_score":(governance.get("execution_governance_overview") or {}).get("execution_governance_score"),"institutional_compliance_posture":(compliance.get("institutional_compliance_overview") or {}).get("institutional_compliance_posture"),"institutional_compliance_score":(compliance.get("institutional_compliance_overview") or {}).get("institutional_compliance_score")},"clearance_actions":_actions(overview,queue,matrix)}
@router.get("/api/live-allocation-clearance-grid/summary")
def live_allocation_clearance_grid_summary():
    session=_require_user(); return _build_summary(session.get("email"))
@router.post("/api/live-allocation-clearance-grid/run")
def live_allocation_clearance_grid_run(payload:dict=Body(default=None)):
    session=_require_user(); email=session.get("email"); store=_load(email); summary=_build_summary(email); overview=summary.get("live_allocation_clearance_overview") or {}
    run={"run_id":f"lacg_{time.time_ns()}","mission":"QNT30671","trigger":(payload or {}).get("trigger") or "manual","timestamp":_now_ts(),"generated_at":summary.get("generated_at"),"live_allocation_clearance_posture":overview.get("live_allocation_clearance_posture"),"live_allocation_clearance_score":overview.get("live_allocation_clearance_score"),"approve_count":overview.get("approve_count"),"hold_count":overview.get("hold_count"),"clearance_capital_millions":overview.get("clearance_capital_millions")}
    store.setdefault("runs",[]).insert(0,run); store["runs"]=store.get("runs",[])[:120]; _save(email,store); return {"status":"ok","summary":summary,"run":run}
@router.get("/api/live-allocation-clearance-grid/audit")
def live_allocation_clearance_grid_audit():
    session=_require_user(); email=session.get("email"); store=_load(email); runs=store.get("runs") or []; return {"mission":"QNT30671","run_count":len(runs),"latest_run":runs[0] if runs else None,"runs":runs[:20],"policy":store.get("policy") or dict(DEFAULT_POLICY)}
@router.post("/api/live-allocation-clearance-grid/policy")
def live_allocation_clearance_grid_policy(payload:dict=Body(...)):
    session=_require_user(); email=session.get("email"); store=_load(email); policy=store.get("policy") or dict(DEFAULT_POLICY); allowed=set(DEFAULT_POLICY.keys())
    for key,value in payload.items():
        if key in allowed: policy[key]=value
    store["policy"]=policy; _save(email,store); return {"status":"updated","policy":policy,"summary":_build_summary(email)}
