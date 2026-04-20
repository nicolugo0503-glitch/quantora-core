from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, time
router = APIRouter(tags=["live-allocation-release-authority-mesh"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
MESH_DIR = ARTIFACTS_DIR / "live_allocation_release_authority_mesh"
DEFAULT_POLICY = {"priority_mesh_case_count": 8, "minimum_mesh_readiness_score": 86.0, "minimum_mesh_authority_score": 84.0, "minimum_release_alignment_score": 82.0, "minimum_dispatch_alignment_score": 80.0, "maximum_mesh_stress_score": 24.0}
def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu
def _convergence():
    from backend.app import qnt30669_allocation_release_convergence_layer_router as mod
    return mod
def _control():
    from backend.app import qnt30666_live_allocation_control_tower_router as mod
    return mod
def _dispatch():
    from backend.app import qnt30665_capital_dispatch_supervision_router as mod
    return mod
def _compliance():
    from backend.app import qnt30652_institutional_compliance_router as mod
    return mod
def _safe(v:str)->str:
    return hashlib.sha256((v or "").strip().lower().encode()).hexdigest()[:24]
def _path(email:str)->Path:
    MESH_DIR.mkdir(parents=True, exist_ok=True); return MESH_DIR / f"{_safe(email)}.json"
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
def _mesh_book(dependencies:dict, policy:dict)->list[dict]:
    convergence=dependencies["convergence"]; control=dependencies["control"]; dispatch=dependencies["dispatch"]; compliance=dependencies["compliance"]
    convergence_book=convergence.get("convergence_book") or []; convergence_matrix=convergence.get("convergence_matrix") or []
    control_book=control.get("allocation_book") or []; control_matrix=control.get("allocation_matrix") or []
    dispatch_matrix=dispatch.get("dispatch_matrix") or []; compliance_matrix=compliance.get("release_matrix") or []
    count=max(int(policy.get("priority_mesh_case_count") or 8),4); base_len=max(len(convergence_book),len(control_book),len(dispatch_matrix),len(compliance_matrix),1); out=[]
    for idx in range(min(count, max(base_len,count))):
        cv=convergence_book[idx % max(len(convergence_book),1)] if convergence_book else {}
        cm=convergence_matrix[idx % max(len(convergence_matrix),1)] if convergence_matrix else {}
        cb=control_book[idx % max(len(control_book),1)] if control_book else {}
        ct=control_matrix[idx % max(len(control_matrix),1)] if control_matrix else {}
        dm=dispatch_matrix[idx % max(len(dispatch_matrix),1)] if dispatch_matrix else {}
        xp=compliance_matrix[idx % max(len(compliance_matrix),1)] if compliance_matrix else {}
        readiness=min(100.0,float(cv.get("convergence_readiness_score") or 0.0)*0.26 + float(ct.get("allocation_authority_score") or 0.0)*0.18 + float(cm.get("convergence_authority_score") or 0.0)*0.16 + float(dm.get("authority_score") or 0.0)*0.12 + float(xp.get("release_authority_score") or 0.0)*0.08 + 8.0)
        authority=min(100.0,readiness*0.34 + float(cm.get("convergence_authority_score") or 0.0)*0.20 + float(ct.get("allocation_authority_score") or 0.0)*0.16 + float(dm.get("authority_score") or 0.0)*0.10 + 6.0)
        release_alignment=min(100.0,float(cm.get("convergence_authority_score") or 0.0)*0.34 + float(cv.get("release_alignment_score") or 0.0)*0.22 + float(xp.get("release_authority_score") or 0.0)*0.14 + 8.0)
        dispatch_alignment=min(100.0,float(dm.get("authority_score") or 0.0)*0.36 + float(ct.get("allocation_authority_score") or 0.0)*0.18 + float(cv.get("convergence_authority_score") or 0.0)*0.12 + 8.0)
        stress=max(4.0,35.0 - readiness*0.13 - authority*0.10 - release_alignment*0.08 - dispatch_alignment*0.06 + idx*0.55)
        status="approve"
        if release_alignment < float(policy.get("minimum_release_alignment_score") or 82.0) or dispatch_alignment < float(policy.get("minimum_dispatch_alignment_score") or 80.0): status="review"
        if authority < float(policy.get("minimum_mesh_authority_score") or 84.0) or stress > float(policy.get("maximum_mesh_stress_score") or 24.0): status="hold"
        out.append({"mesh_case_id":f"larm_{idx+1:02d}","allocator_name":cv.get("allocator_name") or cb.get("allocator_name") or f"Allocator {idx+1}","strategy_id":cv.get("strategy_id") or cb.get("strategy_id") or f"STRAT_{idx+1:02d}","product_id":cv.get("product_id") or cb.get("product_id") or f"QNT_LARM_{idx+1:02d}","jurisdiction":cv.get("jurisdiction") or cb.get("jurisdiction") or "multi-jurisdiction","capital_target_millions":_round_money(cv.get("capital_target_millions") or cb.get("capital_target_millions") or 0.0),"mesh_readiness_score":_round_pct(readiness),"mesh_authority_score":_round_pct(authority),"release_alignment_score":_round_pct(release_alignment),"dispatch_alignment_score":_round_pct(dispatch_alignment),"mesh_stress_score":_round_pct(stress),"mesh_status":status})
    return out
def _mesh_lanes(book:list[dict], policy:dict)->list[dict]:
    out=[]
    for idx,row in enumerate(book):
        lane_score=min(100.0,float(row.get("mesh_readiness_score") or 0.0)*0.34 + float(row.get("mesh_authority_score") or 0.0)*0.24 + float(row.get("release_alignment_score") or 0.0)*0.14 + float(row.get("dispatch_alignment_score") or 0.0)*0.12 + 6.0)
        status="greenlight" if lane_score >= float(policy.get("minimum_mesh_readiness_score") or 86.0) and row.get("mesh_status")=="approve" else ("hold" if row.get("mesh_status")=="hold" else "review")
        out.append({"lane_id":f"larl_{idx+1:02d}","allocator_name":row.get("allocator_name"),"strategy_id":row.get("strategy_id"),"mesh_window":"live allocation release authority command window","mesh_lane_score":_round_pct(lane_score),"lane_status":status})
    return out
def _mesh_matrix(book:list[dict], lanes:list[dict], policy:dict)->list[dict]:
    out=[]
    for idx,row in enumerate(book):
        lane=lanes[idx % max(len(lanes),1)] if lanes else {}
        authority_score=min(100.0,float(row.get("mesh_readiness_score") or 0.0)*0.30 + float(row.get("mesh_authority_score") or 0.0)*0.24 + float(row.get("release_alignment_score") or 0.0)*0.14 + float(row.get("dispatch_alignment_score") or 0.0)*0.12 + float(lane.get("mesh_lane_score") or 0.0)*0.12 + 4.0)
        status="approve" if authority_score >= float(policy.get("minimum_mesh_authority_score") or 84.0) and lane.get("lane_status")=="greenlight" and row.get("mesh_status")=="approve" else ("hold" if row.get("mesh_status")=="hold" else "review")
        out.append({"matrix_id":f"larmx_{idx+1:02d}","allocator_name":row.get("allocator_name"),"strategy_id":row.get("strategy_id"),"product_id":row.get("product_id"),"jurisdiction":row.get("jurisdiction"),"capital_target_millions":row.get("capital_target_millions"),"mesh_authority_score":_round_pct(authority_score),"mesh_authority_status":status})
    return out
def _mesh_queue(book:list[dict], lanes:list[dict], matrix:list[dict])->list[dict]:
    out=[]
    for idx,row in enumerate(book):
        lane=lanes[idx % max(len(lanes),1)] if lanes else {}
        authority=matrix[idx % max(len(matrix),1)] if matrix else {}
        status="approve"
        if authority.get("mesh_authority_status")=="review" or lane.get("lane_status")=="review" or row.get("mesh_status")=="review": status="review"
        if authority.get("mesh_authority_status")=="hold" or row.get("mesh_status")=="hold": status="hold"
        next_action="approve live allocation release and maintain governed authority mesh discipline"
        if status=="review": next_action="refresh convergence proof, dispatch evidence, and release alignment before authorizing live release"
        if status=="hold": next_action="freeze live release authority, escalate to institutional oversight, and block downstream allocation expansion"
        out.append({"queue_id":f"larq_{idx+1:02d}","allocator_name":row.get("allocator_name"),"strategy_id":row.get("strategy_id"),"product_id":row.get("product_id"),"jurisdiction":row.get("jurisdiction"),"capital_target_millions":row.get("capital_target_millions"),"next_action":next_action,"owner":"Live Allocation Release Authority Mesh","queue_status":status})
    return out
def _overview(dependencies:dict, book:list[dict], lanes:list[dict], matrix:list[dict], queue:list[dict])->dict:
    convergence_overview=dependencies["convergence"].get("allocation_convergence_overview") or {}
    control_overview=dependencies["control"].get("live_allocation_overview") or {}
    dispatch_overview=dependencies["dispatch"].get("capital_dispatch_overview") or {}
    compliance_overview=dependencies["compliance"].get("institutional_compliance_overview") or {}
    total_capital=sum(float(x.get("capital_target_millions") or 0.0) for x in book); approve_count=len([x for x in queue if x.get("queue_status")=="approve"]); review_count=len([x for x in queue if x.get("queue_status")=="review"]); hold_count=len([x for x in queue if x.get("queue_status")=="hold"]); green_count=len([x for x in lanes if x.get("lane_status")=="greenlight"]); avg_readiness=sum(float(x.get("mesh_readiness_score") or 0.0) for x in book)/max(len(book),1); avg_authority=sum(float(x.get("mesh_authority_score") or 0.0) for x in book)/max(len(book),1); avg_release=sum(float(x.get("release_alignment_score") or 0.0) for x in book)/max(len(book),1); avg_dispatch=sum(float(x.get("dispatch_alignment_score") or 0.0) for x in book)/max(len(book),1); avg_stress=sum(float(x.get("mesh_stress_score") or 0.0) for x in book)/max(len(book),1)
    score=min(100.0,avg_readiness*0.26 + avg_authority*0.22 + avg_release*0.14 + avg_dispatch*0.12 + (100.0-avg_stress)*0.12 + float(control_overview.get("live_allocation_score") or 76.0)*0.08 + float(convergence_overview.get("allocation_convergence_score") or 78.0)*0.06)
    posture="live-allocation-release-ready"
    if hold_count: posture="live-allocation-release-constrained"
    elif review_count > approve_count: posture="live-allocation-release-reviewing"
    return {"mesh_capital_millions":_round_money(total_capital),"approve_count":approve_count,"review_count":review_count,"hold_count":hold_count,"greenlight_lane_count":green_count,"average_mesh_readiness":_round_pct(avg_readiness),"average_mesh_authority":_round_pct(avg_authority),"average_release_alignment":_round_pct(avg_release),"average_dispatch_alignment":_round_pct(avg_dispatch),"average_mesh_stress":_round_pct(avg_stress),"live_allocation_release_score":_round_pct(score),"live_allocation_release_posture":posture,"allocation_convergence_posture":convergence_overview.get("allocation_convergence_posture"),"live_allocation_posture":control_overview.get("live_allocation_posture"),"capital_dispatch_posture":dispatch_overview.get("capital_dispatch_posture"),"institutional_compliance_posture":compliance_overview.get("institutional_compliance_posture")}
def _actions(overview:dict, queue:list[dict], matrix:list[dict])->list[str]:
    actions=[]
    if overview.get("live_allocation_release_posture") != "live-allocation-release-ready": actions.append("Tighten convergence, dispatch, and compliance evidence before increasing live release scale.")
    approves=[x for x in queue if x.get("queue_status")=="approve"][:3]
    if approves: actions.append("Approve live release package for " + ", ".join(x.get("allocator_name") for x in approves) + ".")
    reviews=[x for x in queue if x.get("queue_status")=="review"]
    if reviews: actions.append(f"Review {len(reviews)} live release cases before authorizing additional scale-up.")
    holds=[x for x in matrix if x.get("mesh_authority_status")=="hold"]
    if holds: actions.append("Hold live release package for " + ", ".join(x.get("allocator_name") for x in holds[:2]) + ".")
    return actions
def _build_summary(email:str):
    store=_load(email); policy=store.get("policy") or dict(DEFAULT_POLICY)
    convergence=_safe_summary(_convergence()._build_summary, email, fallback={"allocation_convergence_overview":{"allocation_convergence_score":76.0,"allocation_convergence_posture":"allocation-convergence-building"},"convergence_book":[],"convergence_matrix":[],"convergence_queue":[]})
    control=_safe_summary(_control()._build_summary, email, fallback={"live_allocation_overview":{"live_allocation_score":74.0,"live_allocation_posture":"live-allocation-building"},"allocation_book":[],"allocation_matrix":[]})
    dispatch=_safe_summary(_dispatch()._build_summary, email, fallback={"capital_dispatch_overview":{"capital_dispatch_score":75.0,"capital_dispatch_posture":"capital-dispatch-building"},"dispatch_book":[],"dispatch_matrix":[],"dispatch_queue":[]})
    compliance=_safe_summary(_compliance()._build_summary, email, fallback={"institutional_compliance_overview":{"institutional_compliance_score":77.0,"institutional_compliance_posture":"institutional-compliance-building"},"release_matrix":[]})
    dependencies={"convergence":convergence,"control":control,"dispatch":dispatch,"compliance":compliance}; book=_mesh_book(dependencies,policy); lanes=_mesh_lanes(book,policy); matrix=_mesh_matrix(book,lanes,policy); queue=_mesh_queue(book,lanes,matrix); overview=_overview(dependencies,book,lanes,matrix,queue)
    return {"mission":"QNT30670","generated_at":_now_iso(),"policy":policy,"live_allocation_release_overview":overview,"mesh_book":book,"mesh_lanes":lanes,"mesh_matrix":matrix,"mesh_queue":queue,"mesh_dependencies":{"allocation_convergence_posture":(convergence.get("allocation_convergence_overview") or {}).get("allocation_convergence_posture"),"allocation_convergence_score":(convergence.get("allocation_convergence_overview") or {}).get("allocation_convergence_score"),"live_allocation_posture":(control.get("live_allocation_overview") or {}).get("live_allocation_posture"),"live_allocation_score":(control.get("live_allocation_overview") or {}).get("live_allocation_score"),"capital_dispatch_posture":(dispatch.get("capital_dispatch_overview") or {}).get("capital_dispatch_posture"),"capital_dispatch_score":(dispatch.get("capital_dispatch_overview") or {}).get("capital_dispatch_score"),"institutional_compliance_posture":(compliance.get("institutional_compliance_overview") or {}).get("institutional_compliance_posture"),"institutional_compliance_score":(compliance.get("institutional_compliance_overview") or {}).get("institutional_compliance_score")},"mesh_actions":_actions(overview,queue,matrix)}
@router.get("/api/live-allocation-release-authority-mesh/summary")
def live_allocation_release_authority_mesh_summary():
    session=_require_user(); return _build_summary(session.get("email"))
@router.post("/api/live-allocation-release-authority-mesh/run")
def live_allocation_release_authority_mesh_run(payload:dict=Body(default=None)):
    session=_require_user(); email=session.get("email"); store=_load(email); summary=_build_summary(email); overview=summary.get("live_allocation_release_overview") or {}
    run={"run_id":f"larm_{time.time_ns()}","mission":"QNT30670","trigger":(payload or {}).get("trigger") or "manual","timestamp":_now_ts(),"generated_at":summary.get("generated_at"),"live_allocation_release_posture":overview.get("live_allocation_release_posture"),"live_allocation_release_score":overview.get("live_allocation_release_score"),"approve_count":overview.get("approve_count"),"hold_count":overview.get("hold_count"),"mesh_capital_millions":overview.get("mesh_capital_millions")}
    store.setdefault("runs",[]).insert(0,run); store["runs"]=store.get("runs",[])[:120]; _save(email,store); return {"status":"ok","summary":summary,"run":run}
@router.get("/api/live-allocation-release-authority-mesh/audit")
def live_allocation_release_authority_mesh_audit():
    session=_require_user(); email=session.get("email"); store=_load(email); runs=store.get("runs") or []; return {"mission":"QNT30670","run_count":len(runs),"latest_run":runs[0] if runs else None,"runs":runs[:20],"policy":store.get("policy") or dict(DEFAULT_POLICY)}
@router.post("/api/live-allocation-release-authority-mesh/policy")
def live_allocation_release_authority_mesh_policy(payload:dict=Body(...)):
    session=_require_user(); email=session.get("email"); store=_load(email); policy=store.get("policy") or dict(DEFAULT_POLICY); allowed=set(DEFAULT_POLICY.keys())
    for key,value in payload.items():
        if key in allowed: policy[key]=value
    store["policy"]=policy; _save(email,store); return {"status":"updated","policy":policy,"summary":_build_summary(email)}
