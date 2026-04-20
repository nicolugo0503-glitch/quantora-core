from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["allocation-release-convergence-layer"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
CONVERGENCE_DIR = ARTIFACTS_DIR / "allocation_release_convergence_layer"

DEFAULT_POLICY = {
    "priority_convergence_case_count": 8,
    "minimum_convergence_readiness_score": 86.0,
    "minimum_convergence_authority_score": 84.0,
    "minimum_release_alignment_score": 81.0,
    "minimum_compliance_alignment_score": 80.0,
    "maximum_convergence_stress_score": 24.0,
}

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _escalation():
    from backend.app import qnt30668_allocation_escalation_command_router as mod
    return mod

def _release():
    from backend.app import qnt30664_institutional_release_authority_router as mod
    return mod

def _dispatch():
    from backend.app import qnt30665_capital_dispatch_supervision_router as mod
    return mod

def _compliance():
    from backend.app import qnt30652_institutional_compliance_router as mod
    return mod

def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _path(email: str) -> Path:
    CONVERGENCE_DIR.mkdir(parents=True, exist_ok=True)
    return CONVERGENCE_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _now_ts() -> int:
    return int(time.time())

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _round_money(v) -> float:
    return round(float(v or 0.0), 2)

def _round_pct(v) -> float:
    return round(float(v or 0.0), 4)

def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {
            "email": email,
            "policy": dict(DEFAULT_POLICY),
            "runs": [],
            "created_at": _now_ts(),
            "updated_at": _now_ts(),
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))

def _save(email: str, data: dict) -> dict:
    data["updated_at"] = _now_ts()
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data

def _safe_summary(builder, *args, fallback: dict):
    try:
        return builder(*args)
    except Exception:
        return dict(fallback)

def _convergence_book(dependencies: dict, policy: dict) -> list[dict]:
    escalation = dependencies["escalation"]
    dispatch = dependencies["dispatch"]
    release = dependencies["release"]
    compliance = dependencies["compliance"]
    escalation_book = escalation.get("escalation_book") or escalation.get("convergence_book") or []
    release_matrix = release.get("release_matrix") or []
    dispatch_queue = dispatch.get("dispatch_queue") or dispatch.get("convergence_queue") or []
    compliance_matrix = compliance.get("release_matrix") or []
    dispatch_matrix = dispatch.get("dispatch_matrix") or []
    release_book = release.get("release_book") or []
    
    count = max(int(policy.get("priority_convergence_case_count") or 8), 4)
    base_len = max(len(escalation_book), len(release_book), len(release_book), len(compliance_matrix), 1)
    out = []
    for idx in range(min(count, max(base_len, count))):
        ob = escalation_book[idx % max(len(escalation_book), 1)] if escalation_book else {}
        om = release_matrix[idx % max(len(release_matrix), 1)] if release_matrix else {}
        oq = dispatch_queue[idx % max(len(dispatch_queue), 1)] if dispatch_queue else {}
        cb = release_book[idx % max(len(release_book), 1)] if release_book else {}
        au = dispatch_matrix[idx % max(len(dispatch_matrix), 1)] if dispatch_matrix else {}
        
        
        cm = compliance_matrix[idx % max(len(compliance_matrix), 1)] if compliance_matrix else {}
        readiness = min(100.0,
            float(eb.get("oversight_readiness_score") or 0.0) * 0.24 +
            float(rm.get("oversight_authority_score") or 0.0) * 0.18 +
            float(dm.get("authority_score") or 0.0) * 0.12 +
            float(rb.get("release_readiness_score") or 0.0) * 0.12 +
            float(rm.get("release_authority_score") or 0.0) * 0.10 +
            float(cm.get("release_authority_score") or 0.0) * 0.10 +
            6.0
        )
        authority = min(100.0,
            readiness * 0.34 +
            float(rm.get("oversight_authority_score") or 0.0) * 0.20 +
            float(rm.get("release_authority_score") or 0.0) * 0.16 +
            float(dm.get("authority_score") or 0.0) * 0.12 +
            5.0
        )
        release_alignment = min(100.0,
            float(rm.get("release_authority_score") or 0.0) * 0.38 +
            float(rb.get("release_readiness_score") or 0.0) * 0.24 +
            float(eb.get("governance_alignment_score") or 0.0) * 0.12 +
            7.0
        )
        compliance_alignment = min(100.0,
            float(cm.get("release_authority_score") or 0.0) * 0.42 +
            float(eb.get("governance_alignment_score") or 0.0) * 0.18 +
            float(eb.get("committee_alignment_score") or 0.0) * 0.10 +
            7.0
        )
        stress = max(4.0, 35.0 - readiness * 0.13 - authority * 0.10 - release_alignment * 0.08 - compliance_alignment * 0.06 + idx * 0.55)
        status = "approve"
        if release_alignment < float(policy.get("minimum_release_alignment_score") or 81.0) or compliance_alignment < float(policy.get("minimum_compliance_alignment_score") or 80.0):
            status = "review"
        if authority < float(policy.get("minimum_convergence_authority_score") or 84.0) or stress > float(policy.get("maximum_convergence_stress_score") or 24.0) or dq.get("queue_status") == "hold":
            status = "hold"
        out.append({
            "convergence_case_id": f"arc_{idx+1:02d}",
            "allocator_name": eb.get("allocator_name") or rb.get("allocator_name") or rb.get("allocator_name") or f"Allocator {idx+1}",
            "strategy_id": eb.get("strategy_id") or rb.get("strategy_id") or rb.get("strategy_id") or f"STRAT_{idx+1:02d}",
            "product_id": eb.get("product_id") or rb.get("product_id") or rb.get("product_id") or f"QNT_AEC_{idx+1:02d}",
            "jurisdiction": eb.get("jurisdiction") or rb.get("jurisdiction") or rb.get("jurisdiction") or "multi-jurisdiction",
            "capital_target_millions": _round_money(eb.get("capital_target_millions") or rb.get("capital_target_millions") or 0.0),
            "convergence_readiness_score": _round_pct(readiness),
            "convergence_authority_score": _round_pct(authority),
            "release_alignment_score": _round_pct(release_alignment),
            "compliance_alignment_score": _round_pct(compliance_alignment),
            "convergence_stress_score": _round_pct(stress),
            "convergence_status": status,
        })
    return out

def _convergence_lanes(book: list[dict], policy: dict) -> list[dict]:
    out = []
    for idx, row in enumerate(book):
        lane_score = min(100.0,
            float(row.get("convergence_readiness_score") or 0.0) * 0.34 +
            float(row.get("convergence_authority_score") or 0.0) * 0.24 +
            float(row.get("release_alignment_score") or 0.0) * 0.14 +
            float(row.get("compliance_alignment_score") or 0.0) * 0.12 +
            6.0
        )
        status = "greenlight" if lane_score >= float(policy.get("minimum_convergence_readiness_score") or 86.0) and row.get("convergence_status") == "approve" else ("hold" if row.get("convergence_status") == "hold" else "review")
        out.append({
            "lane_id": f"arl_{idx+1:02d}",
            "allocator_name": row.get("allocator_name"),
            "strategy_id": row.get("strategy_id"),
            "convergence_window": "allocation release convergence command window",
            "convergence_lane_score": _round_pct(lane_score),
            "lane_status": status,
        })
    return out

def _convergence_matrix(book: list[dict], lanes: list[dict], policy: dict) -> list[dict]:
    out = []
    for idx, row in enumerate(book):
        lane = lanes[idx % max(len(lanes), 1)] if lanes else {}
        authority_score = min(100.0,
            float(row.get("convergence_readiness_score") or 0.0) * 0.30 +
            float(row.get("convergence_authority_score") or 0.0) * 0.24 +
            float(row.get("release_alignment_score") or 0.0) * 0.14 +
            float(row.get("compliance_alignment_score") or 0.0) * 0.12 +
            float(lane.get("convergence_lane_score") or 0.0) * 0.12 +
            4.0
        )
        status = "approve" if authority_score >= float(policy.get("minimum_convergence_authority_score") or 84.0) and lane.get("lane_status") == "greenlight" and row.get("convergence_status") == "approve" else ("hold" if row.get("convergence_status") == "hold" else "review")
        out.append({
            "matrix_id": f"arm_{idx+1:02d}",
            "allocator_name": row.get("allocator_name"),
            "strategy_id": row.get("strategy_id"),
            "product_id": row.get("product_id"),
            "jurisdiction": row.get("jurisdiction"),
            "capital_target_millions": row.get("capital_target_millions"),
            "convergence_authority_score": _round_pct(authority_score),
            "convergence_authority_status": status,
        })
    return out

def _convergence_queue(book: list[dict], lanes: list[dict], matrix: list[dict]) -> list[dict]:
    out = []
    for idx, row in enumerate(book):
        lane = lanes[idx % max(len(lanes), 1)] if lanes else {}
        authority = matrix[idx % max(len(matrix), 1)] if matrix else {}
        status = "approve"
        if authority.get("convergence_authority_status") == "review" or lane.get("lane_status") == "review" or row.get("convergence_status") == "review":
            status = "review"
        if authority.get("convergence_authority_status") == "hold" or row.get("convergence_status") == "hold":
            status = "hold"
        next_action = "approve controlled scale-up and maintain governed allocation release convergence discipline"
        if status == "review":
            next_action = "refresh release evidence, committee posture, and compliance proof before scaling the allocation case"
        if status == "hold":
            next_action = "freeze scale-up, escalate to institutional authority, and block downstream release expansion"
        out.append({
            "queue_id": f"arq_{idx+1:02d}",
            "allocator_name": row.get("allocator_name"),
            "strategy_id": row.get("strategy_id"),
            "product_id": row.get("product_id"),
            "jurisdiction": row.get("jurisdiction"),
            "capital_target_millions": row.get("capital_target_millions"),
            "next_action": next_action,
            "owner": "Allocation Release Convergence Layer",
            "queue_status": status,
        })
    return out

def _overview(dependencies: dict, book: list[dict], lanes: list[dict], matrix: list[dict], queue: list[dict]) -> dict:
    escalation_overview = dependencies["escalation"].get("allocation_escalation_overview") or dependencies["escalation"].get("allocation_release_convergence_overview") or {}
    dispatch_overview = dependencies["dispatch"].get("capital_dispatch_overview") or {}
    release_overview = dependencies["release"].get("institutional_release_overview") or {}
    compliance_overview = dependencies["compliance"].get("institutional_compliance_overview") or {}
    total_capital = sum(float(x.get("capital_target_millions") or 0.0) for x in book)
    approve_count = len([x for x in queue if x.get("queue_status") == "approve"])
    review_count = len([x for x in queue if x.get("queue_status") == "review"])
    hold_count = len([x for x in queue if x.get("queue_status") == "hold"])
    green_count = len([x for x in lanes if x.get("lane_status") == "greenlight"])
    avg_readiness = sum(float(x.get("convergence_readiness_score") or 0.0) for x in book) / max(len(book), 1)
    avg_authority = sum(float(x.get("convergence_authority_score") or 0.0) for x in book) / max(len(book), 1)
    avg_release = sum(float(x.get("release_alignment_score") or 0.0) for x in book) / max(len(book), 1)
    avg_compliance = sum(float(x.get("compliance_alignment_score") or 0.0) for x in book) / max(len(book), 1)
    avg_stress = sum(float(x.get("convergence_stress_score") or 0.0) for x in book) / max(len(book), 1)
    score = min(100.0,
        avg_readiness * 0.26 + avg_authority * 0.22 + avg_release * 0.14 + avg_compliance * 0.12 + (100.0 - avg_stress) * 0.12 + float(release_overview.get("institutional_release_score") or 76.0) * 0.08 + float(oversight_overview.get("allocation_escalation_score") or 78.0) * 0.06
    )
    posture = "allocation-convergence-ready"
    if hold_count:
        posture = "allocation-convergence-constrained"
    elif review_count > approve_count:
        posture = "allocation-convergence-reviewing"
    return {
        "convergent_capital_millions": _round_money(total_capital),
        "approve_count": approve_count,
        "review_count": review_count,
        "hold_count": hold_count,
        "greenlight_lane_count": green_count,
        "average_convergence_readiness": _round_pct(avg_readiness),
        "average_convergence_authority": _round_pct(avg_authority),
        "average_release_alignment": _round_pct(avg_release),
        "average_compliance_alignment": _round_pct(avg_compliance),
        "average_convergence_stress": _round_pct(avg_stress),
        "allocation_convergence_score": _round_pct(score),
        "allocation_convergence_posture": posture,
        "allocation_escalation_posture": oversight_overview.get("allocation_escalation_posture"),
        "capital_dispatch_posture": committee_overview.get("capital_dispatch_posture"),
        "institutional_release_posture": release_overview.get("institutional_release_posture"),
        "institutional_compliance_posture": compliance_overview.get("institutional_compliance_posture"),
    }

def _actions(overview: dict, queue: list[dict], matrix: list[dict]) -> list[str]:
    actions = []
    if overview.get("allocation_convergence_posture") != "allocation-convergence-ready":
        actions.append("Tighten release, committee, and compliance evidence before increasing live allocation scale.")
    approves = [x for x in queue if x.get("queue_status") == "approve"][:3]
    if approves:
        actions.append("Approve convergence package for " + ", ".join(x.get("allocator_name") for x in approves) + ".")
    reviews = [x for x in queue if x.get("queue_status") == "review"]
    if reviews:
        actions.append(f"Review {len(reviews)} convergence cases before authorizing additional scale-up.")
    holds = [x for x in matrix if x.get("convergence_authority_status") == "hold"]
    if holds:
        actions.append("Hold convergence package for " + ", ".join(x.get("allocator_name") for x in holds[:2]) + ".")
    return actions

def _build_summary(email: str):
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    escalation = _safe_summary(_escalation()._build_summary, email, fallback={
        "allocation_release_convergence_overview": {"allocation_release_convergence_score": 76.0, "allocation_release_convergence_posture": "allocation-release-convergence-building"},
        "convergence_book": [],
        "convergence_matrix": [],
        "convergence_queue": [],
    })
    release = _safe_summary(_release()._build_summary, email, fallback={
        "institutional_release_overview": {"institutional_release_score": 74.0, "institutional_release_posture": "institutional-release-building"},
        "release_book": [],
        "release_matrix": [],
    })
    dispatch = _safe_summary(_dispatch()._build_summary, email, fallback={
        "capital_dispatch_overview": {"capital_dispatch_score": 75.0, "capital_dispatch_posture": "capital-dispatch-building"},
        "dispatch_book": [],
        "dispatch_matrix": [],
        "dispatch_queue": [],
    })
    compliance = _safe_summary(_compliance()._build_summary, email, fallback={
        "institutional_compliance_overview": {"institutional_compliance_score": 77.0, "institutional_compliance_posture": "institutional-compliance-building"},
        "release_matrix": [],
    })
    dependencies = {"escalation": escalation, "release": release, "dispatch": dispatch, "compliance": compliance}
    book = _convergence_book(dependencies, policy)
    lanes = _convergence_lanes(book, policy)
    matrix = _convergence_matrix(book, lanes, policy)
    queue = _convergence_queue(book, lanes, matrix)
    overview = _overview(dependencies, book, lanes, matrix, queue)
    return {
        "mission": "QNT30669",
        "generated_at": _now_iso(),
        "policy": policy,
        "allocation_convergence_overview": overview,
        "convergence_book": book,
        "convergence_lanes": lanes,
        "convergence_matrix": matrix,
        "convergence_queue": queue,
        "convergence_dependencies": {
                        "allocation_escalation_posture": (escalation.get("allocation_escalation_overview") or {}).get("allocation_escalation_posture"),
            "allocation_escalation_score": (escalation.get("allocation_escalation_overview") or {}).get("allocation_escalation_score"),
            "institutional_release_posture": (release.get("institutional_release_overview") or {}).get("institutional_release_posture"),
            "institutional_release_score": (release.get("institutional_release_overview") or {}).get("institutional_release_score"),
            "capital_dispatch_posture": (dispatch.get("capital_dispatch_overview") or {}).get("capital_dispatch_posture"),
            "capital_dispatch_score": (dispatch.get("capital_dispatch_overview") or {}).get("capital_dispatch_score"),
            "institutional_compliance_posture": (compliance.get("institutional_compliance_overview") or {}).get("institutional_compliance_posture"),
            "institutional_compliance_score": (compliance.get("institutional_compliance_overview") or {}).get("institutional_compliance_score"),
        },
        "convergence_actions": _actions(overview, queue, matrix),
    }

@router.get("/api/allocation-release-convergence-layer/summary")
def allocation_release_convergence_layer_summary():
    session = _require_user()
    return _build_summary(session.get("email"))

@router.post("/api/allocation-release-convergence-layer/run")
def allocation_release_convergence_layer_run(payload: dict = Body(default=None)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    summary = _build_summary(email)
    overview = summary.get("allocation_convergence_overview") or {}
    run = {
        "run_id": f"arc_{time.time_ns()}",
        "mission": "QNT30669",
        "trigger": (payload or {}).get("trigger") or "manual",
        "timestamp": _now_ts(),
        "generated_at": summary.get("generated_at"),
        "allocation_convergence_posture": overview.get("allocation_convergence_posture"),
        "allocation_convergence_score": overview.get("allocation_convergence_score"),
        "approve_count": overview.get("approve_count"),
        "hold_count": overview.get("hold_count"),
        "convergent_capital_millions": overview.get("convergent_capital_millions"),
    }
    store.setdefault("runs", []).insert(0, run)
    store["runs"] = store.get("runs", [])[:120]
    _save(email, store)
    return {"status": "ok", "summary": summary, "run": run}

@router.get("/api/allocation-release-convergence-layer/audit")
def allocation_release_convergence_layer_audit():
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    runs = store.get("runs") or []
    return {
        "mission": "QNT30669",
        "run_count": len(runs),
        "latest_run": runs[0] if runs else None,
        "runs": runs[:20],
        "policy": store.get("policy") or dict(DEFAULT_POLICY),
    }

@router.post("/api/allocation-release-convergence-layer/policy")
def allocation_release_convergence_layer_policy(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    allowed = set(DEFAULT_POLICY.keys())
    for key, value in payload.items():
        if key in allowed:
            policy[key] = value
    store["policy"] = policy
    _save(email, store)
    return {"status": "updated", "policy": policy, "summary": _build_summary(email)}
