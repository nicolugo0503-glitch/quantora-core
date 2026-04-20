from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["live-allocation-control-tower"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
TOWER_DIR = ARTIFACTS_DIR / "live_allocation_control_tower"

DEFAULT_POLICY = {
    "priority_allocation_case_count": 8,
    "minimum_allocation_readiness_score": 87.0,
    "minimum_control_authority_score": 85.0,
    "minimum_strategy_alignment_score": 82.0,
    "minimum_execution_alignment_score": 80.0,
    "maximum_allocation_stress_score": 22.0,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _dispatch():
    from backend.app import qnt30665_capital_dispatch_supervision_router as dispatch
    return dispatch


def _deployment():
    from backend.app import qnt30661_live_capital_deployment_router as deployment
    return deployment


def _governance():
    from backend.app import qnt30662_execution_governance_command_router as governance
    return governance


def _strategic():
    from backend.app import qnt30650_strategic_decision_router as strategic
    return strategic


def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]


def _path(email: str) -> Path:
    TOWER_DIR.mkdir(parents=True, exist_ok=True)
    return TOWER_DIR / f"{_safe(email)}.json"


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


def _allocation_book(dependencies: dict, policy: dict) -> list[dict]:
    dispatch = dependencies["dispatch"]
    deployment = dependencies["deployment"]
    governance = dependencies["governance"]
    strategic = dependencies["strategic"]
    dispatch_book = dispatch.get("dispatch_book") or []
    dispatch_matrix = dispatch.get("dispatch_matrix") or []
    dispatch_queue = dispatch.get("dispatch_queue") or []
    deployment_book = deployment.get("deployment_book") or []
    governance_matrix = governance.get("command_matrix") or []
    governance_queue = governance.get("governance_queue") or []
    capital_directives = strategic.get("capital_directives") or []
    strategy_rankings = strategic.get("strategy_rankings") or []
    count = max(int(policy.get("priority_allocation_case_count") or 8), 4)
    base_len = max(len(dispatch_book), len(deployment_book), len(governance_matrix), len(capital_directives), 1)
    out = []
    for idx in range(min(count, max(base_len, count))):
        db = dispatch_book[idx % max(len(dispatch_book), 1)] if dispatch_book else {}
        dm = dispatch_matrix[idx % max(len(dispatch_matrix), 1)] if dispatch_matrix else {}
        dq = dispatch_queue[idx % max(len(dispatch_queue), 1)] if dispatch_queue else {}
        dep = deployment_book[idx % max(len(deployment_book), 1)] if deployment_book else {}
        gm = governance_matrix[idx % max(len(governance_matrix), 1)] if governance_matrix else {}
        gq = governance_queue[idx % max(len(governance_queue), 1)] if governance_queue else {}
        cd = capital_directives[idx % max(len(capital_directives), 1)] if capital_directives else {}
        sr = strategy_rankings[idx % max(len(strategy_rankings), 1)] if strategy_rankings else {}
        allocation_readiness = min(100.0,
            float(db.get("dispatch_readiness_score") or 0.0) * 0.22 +
            float(dm.get("dispatch_authority_score") or 0.0) * 0.18 +
            float(dep.get("live_readiness_score") or 0.0) * 0.14 +
            float(dep.get("execution_clearance_score") or 0.0) * 0.10 +
            float(gm.get("command_score") or 0.0) * 0.10 +
            float(sr.get("strategy_score") or sr.get("rank_score") or 0.0) * 0.10 +
            float(cd.get("confidence") or 0.0) * 100.0 * 0.08 +
            6.0
        )
        control_authority = min(100.0,
            allocation_readiness * 0.34 +
            float(gm.get("command_score") or 0.0) * 0.24 +
            float(dm.get("dispatch_authority_score") or 0.0) * 0.16 +
            float(dep.get("execution_clearance_score") or 0.0) * 0.10 +
            5.0
        )
        strategy_alignment = min(100.0,
            float(sr.get("strategy_score") or sr.get("rank_score") or 0.0) * 0.40 +
            float(cd.get("confidence") or 0.0) * 100.0 * 0.20 +
            float(db.get("execution_alignment_score") or 0.0) * 0.12 +
            6.0
        )
        execution_alignment = min(100.0,
            float(dep.get("execution_clearance_score") or 0.0) * 0.34 +
            float(db.get("execution_alignment_score") or 0.0) * 0.28 +
            float(gm.get("command_score") or 0.0) * 0.16 +
            5.0
        )
        allocation_stress = max(4.0,
            33.0 - allocation_readiness * 0.13 - control_authority * 0.11 - strategy_alignment * 0.07 - execution_alignment * 0.06 + idx * 0.55
        )
        status = "allocate"
        if strategy_alignment < float(policy.get("minimum_strategy_alignment_score") or 82.0) or execution_alignment < float(policy.get("minimum_execution_alignment_score") or 80.0):
            status = "review"
        if control_authority < float(policy.get("minimum_control_authority_score") or 85.0) or allocation_stress > float(policy.get("maximum_allocation_stress_score") or 22.0) or dq.get("queue_status") == "hold" or gq.get("queue_status") == "halt":
            status = "hold"
        out.append({
            "allocation_case_id": f"alc_{idx+1:02d}",
            "allocator_name": db.get("allocator_name") or dep.get("allocator_name") or gm.get("allocator_name") or f"Allocator {idx+1}",
            "strategy_id": db.get("strategy_id") or dep.get("strategy_id") or gm.get("strategy_id") or cd.get("strategy_id") or f"STRAT_{idx+1:02d}",
            "product_id": db.get("product_id") or dep.get("product_id") or gm.get("product_id") or cd.get("product_id") or f"QNT_ALLOC_{idx+1:02d}",
            "jurisdiction": db.get("jurisdiction") or dep.get("jurisdiction") or gm.get("jurisdiction") or "multi-jurisdiction",
            "capital_target_millions": _round_money(db.get("capital_target_millions") or dep.get("capital_target_millions") or 0.0),
            "allocation_readiness_score": _round_pct(allocation_readiness),
            "control_authority_score": _round_pct(control_authority),
            "strategy_alignment_score": _round_pct(strategy_alignment),
            "execution_alignment_score": _round_pct(execution_alignment),
            "allocation_stress_score": _round_pct(allocation_stress),
            "allocation_status": status,
        })
    return out


def _allocation_lanes(book: list[dict], policy: dict) -> list[dict]:
    out = []
    for idx, row in enumerate(book):
        lane_score = min(100.0,
            float(row.get("allocation_readiness_score") or 0.0) * 0.34 +
            float(row.get("control_authority_score") or 0.0) * 0.24 +
            float(row.get("strategy_alignment_score") or 0.0) * 0.14 +
            float(row.get("execution_alignment_score") or 0.0) * 0.12 +
            6.0
        )
        out.append({
            "lane_id": f"lal_{idx+1:02d}",
            "allocator_name": row.get("allocator_name"),
            "strategy_id": row.get("strategy_id"),
            "allocation_window": "live allocation control window",
            "allocation_lane_score": _round_pct(lane_score),
            "lane_status": "greenlight" if lane_score >= float(policy.get("minimum_allocation_readiness_score") or 87.0) and row.get("allocation_status") == "allocate" else ("hold" if row.get("allocation_status") == "hold" else "review"),
        })
    return out


def _allocation_matrix(book: list[dict], lanes: list[dict], policy: dict) -> list[dict]:
    out = []
    for idx, row in enumerate(book):
        lane = lanes[idx % max(len(lanes), 1)] if lanes else {}
        allocation_score = min(100.0,
            float(row.get("allocation_readiness_score") or 0.0) * 0.30 +
            float(row.get("control_authority_score") or 0.0) * 0.24 +
            float(row.get("strategy_alignment_score") or 0.0) * 0.14 +
            float(row.get("execution_alignment_score") or 0.0) * 0.12 +
            float(lane.get("allocation_lane_score") or 0.0) * 0.12 +
            4.0
        )
        status = "allocate" if allocation_score >= float(policy.get("minimum_control_authority_score") or 85.0) and lane.get("lane_status") == "greenlight" and row.get("allocation_status") == "allocate" else ("hold" if row.get("allocation_status") == "hold" else "review")
        out.append({
            "matrix_id": f"lam_{idx+1:02d}",
            "allocator_name": row.get("allocator_name"),
            "strategy_id": row.get("strategy_id"),
            "product_id": row.get("product_id"),
            "jurisdiction": row.get("jurisdiction"),
            "capital_target_millions": row.get("capital_target_millions"),
            "allocation_authority_score": _round_pct(allocation_score),
            "allocation_authority_status": status,
        })
    return out


def _allocation_queue(book: list[dict], lanes: list[dict], matrix: list[dict]) -> list[dict]:
    out = []
    for idx, row in enumerate(book):
        lane = lanes[idx % max(len(lanes), 1)] if lanes else {}
        authority = matrix[idx % max(len(matrix), 1)] if matrix else {}
        status = "allocate"
        if authority.get("allocation_authority_status") == "review" or lane.get("lane_status") == "review" or row.get("allocation_status") == "review":
            status = "review"
        if authority.get("allocation_authority_status") == "hold" or row.get("allocation_status") == "hold":
            status = "hold"
        next_action = "authorize live allocation, route governed capital, and hand off to oversight loops"
        if status == "review":
            next_action = "refresh strategy fit, dispatch package, and execution control inputs before allocation"
        if status == "hold":
            next_action = "freeze live allocation, escalate control break, and block downstream capital routing"
        out.append({
            "queue_id": f"laq_{idx+1:02d}",
            "allocator_name": row.get("allocator_name"),
            "strategy_id": row.get("strategy_id"),
            "product_id": row.get("product_id"),
            "jurisdiction": row.get("jurisdiction"),
            "capital_target_millions": row.get("capital_target_millions"),
            "next_action": next_action,
            "owner": "Live Allocation Control Tower",
            "queue_status": status,
        })
    return out


def _overview(dependencies: dict, book: list[dict], lanes: list[dict], matrix: list[dict], queue: list[dict]) -> dict:
    dispatch_overview = dependencies["dispatch"].get("capital_dispatch_supervision_overview") or {}
    deployment_overview = dependencies["deployment"].get("live_capital_deployment_overview") or {}
    governance_overview = dependencies["governance"].get("execution_governance_overview") or {}
    strategic_overview = dependencies["strategic"].get("strategic_decision_overview") or {}
    total_capital = sum(float(x.get("capital_target_millions") or 0.0) for x in book)
    allocate_count = len([x for x in queue if x.get("queue_status") == "allocate"])
    review_count = len([x for x in queue if x.get("queue_status") == "review"])
    hold_count = len([x for x in queue if x.get("queue_status") == "hold"])
    green_count = len([x for x in lanes if x.get("lane_status") == "greenlight"])
    avg_readiness = sum(float(x.get("allocation_readiness_score") or 0.0) for x in book) / max(len(book), 1)
    avg_authority = sum(float(x.get("control_authority_score") or 0.0) for x in book) / max(len(book), 1)
    avg_strategy = sum(float(x.get("strategy_alignment_score") or 0.0) for x in book) / max(len(book), 1)
    avg_execution = sum(float(x.get("execution_alignment_score") or 0.0) for x in book) / max(len(book), 1)
    avg_stress = sum(float(x.get("allocation_stress_score") or 0.0) for x in book) / max(len(book), 1)
    score = min(100.0,
        avg_readiness * 0.26 + avg_authority * 0.22 + avg_strategy * 0.14 + avg_execution * 0.12 + (100.0 - avg_stress) * 0.12 + float(governance_overview.get("execution_governance_score") or 76.0) * 0.08 + float(strategic_overview.get("strategic_decision_score") or 78.0) * 0.06
    )
    posture = "live-allocation-ready"
    if hold_count:
        posture = "live-allocation-constrained"
    elif review_count > allocate_count:
        posture = "live-allocation-reviewing"
    return {
        "allocatable_capital_millions": _round_money(total_capital),
        "allocate_count": allocate_count,
        "review_count": review_count,
        "hold_count": hold_count,
        "greenlight_lane_count": green_count,
        "average_allocation_readiness": _round_pct(avg_readiness),
        "average_control_authority": _round_pct(avg_authority),
        "average_strategy_alignment": _round_pct(avg_strategy),
        "average_execution_alignment": _round_pct(avg_execution),
        "average_allocation_stress": _round_pct(avg_stress),
        "live_allocation_control_score": _round_pct(score),
        "live_allocation_control_posture": posture,
        "capital_dispatch_supervision_posture": dispatch_overview.get("capital_dispatch_supervision_posture"),
        "live_capital_deployment_posture": deployment_overview.get("live_capital_deployment_posture"),
        "execution_governance_posture": governance_overview.get("execution_governance_posture"),
        "strategic_decision_posture": strategic_overview.get("strategic_decision_posture"),
    }


def _actions(overview: dict, queue: list[dict], matrix: list[dict]) -> list[str]:
    actions = []
    if overview.get("live_allocation_control_posture") != "live-allocation-ready":
        actions.append("Tighten live allocation controls, strategic fit, and execution certainty before increasing allocation velocity.")
    allocs = [x for x in queue if x.get("queue_status") == "allocate"][:3]
    if allocs:
        actions.append("Allocate capital for " + ", ".join(x.get("allocator_name") for x in allocs) + ".")
    reviews = [x for x in queue if x.get("queue_status") == "review"]
    if reviews:
        actions.append(f"Review {len(reviews)} live allocation cases for strategy fit and control sufficiency before capital routing.")
    holds = [x for x in matrix if x.get("allocation_authority_status") == "hold"]
    if holds:
        actions.append("Hold allocation package for " + ", ".join(x.get("allocator_name") for x in holds[:2]) + ".")
    return actions


def _build_summary(email: str):
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    dispatch = _safe_summary(_dispatch()._build_summary, email, fallback={
        "capital_dispatch_supervision_overview": {"capital_dispatch_supervision_score": 76.0, "capital_dispatch_supervision_posture": "capital-dispatch-supervision-building"},
        "dispatch_book": [],
        "dispatch_matrix": [],
        "dispatch_queue": [],
    })
    deployment = _safe_summary(_deployment()._build_summary, email, fallback={
        "live_capital_deployment_overview": {"live_capital_deployment_score": 74.0, "live_capital_deployment_posture": "live-capital-deployment-building"},
        "deployment_book": [],
    })
    governance = _safe_summary(_governance()._build_summary, email, fallback={
        "execution_governance_overview": {"execution_governance_score": 75.0, "execution_governance_posture": "execution-governance-building"},
        "command_matrix": [],
        "governance_queue": [],
    })
    strategic = _safe_summary(_strategic()._build_summary, email, fallback={
        "strategic_decision_overview": {"strategic_decision_score": 77.0, "strategic_decision_posture": "strategic-decision-building"},
        "capital_directives": [],
        "strategy_rankings": [],
    })
    dependencies = {"dispatch": dispatch, "deployment": deployment, "governance": governance, "strategic": strategic}
    book = _allocation_book(dependencies, policy)
    lanes = _allocation_lanes(book, policy)
    matrix = _allocation_matrix(book, lanes, policy)
    queue = _allocation_queue(book, lanes, matrix)
    overview = _overview(dependencies, book, lanes, matrix, queue)
    return {
        "mission": "QNT30666",
        "generated_at": _now_iso(),
        "policy": policy,
        "live_allocation_control_overview": overview,
        "allocation_book": book,
        "allocation_lanes": lanes,
        "allocation_matrix": matrix,
        "allocation_queue": queue,
        "allocation_dependencies": {
            "capital_dispatch_supervision_posture": (dispatch.get("capital_dispatch_supervision_overview") or {}).get("capital_dispatch_supervision_posture"),
            "capital_dispatch_supervision_score": (dispatch.get("capital_dispatch_supervision_overview") or {}).get("capital_dispatch_supervision_score"),
            "live_capital_deployment_posture": (deployment.get("live_capital_deployment_overview") or {}).get("live_capital_deployment_posture"),
            "live_capital_deployment_score": (deployment.get("live_capital_deployment_overview") or {}).get("live_capital_deployment_score"),
            "execution_governance_posture": (governance.get("execution_governance_overview") or {}).get("execution_governance_posture"),
            "execution_governance_score": (governance.get("execution_governance_overview") or {}).get("execution_governance_score"),
            "strategic_decision_posture": (strategic.get("strategic_decision_overview") or {}).get("strategic_decision_posture"),
            "strategic_decision_score": (strategic.get("strategic_decision_overview") or {}).get("strategic_decision_score"),
        },
        "allocation_actions": _actions(overview, queue, matrix),
    }


@router.get("/api/live-allocation-control-tower/summary")
def live_allocation_control_summary():
    session = _require_user()
    return _build_summary(session.get("email"))


@router.post("/api/live-allocation-control-tower/run")
def live_allocation_control_run(payload: dict = Body(default=None)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    summary = _build_summary(email)
    overview = summary.get("live_allocation_control_overview") or {}
    run = {
        "run_id": f"alc_{time.time_ns()}",
        "mission": "QNT30666",
        "trigger": (payload or {}).get("trigger") or "manual",
        "timestamp": _now_ts(),
        "generated_at": summary.get("generated_at"),
        "live_allocation_control_posture": overview.get("live_allocation_control_posture"),
        "live_allocation_control_score": overview.get("live_allocation_control_score"),
        "allocate_count": overview.get("allocate_count"),
        "hold_count": overview.get("hold_count"),
        "allocatable_capital_millions": overview.get("allocatable_capital_millions"),
    }
    store.setdefault("runs", []).insert(0, run)
    store["runs"] = store.get("runs", [])[:120]
    _save(email, store)
    return {"status": "ok", "summary": summary, "run": run}


@router.get("/api/live-allocation-control-tower/audit")
def live_allocation_control_audit():
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    runs = store.get("runs") or []
    return {
        "mission": "QNT30666",
        "run_count": len(runs),
        "latest_run": runs[0] if runs else None,
        "runs": runs[:20],
        "policy": store.get("policy") or dict(DEFAULT_POLICY),
    }


@router.post("/api/live-allocation-control-tower/policy")
def live_allocation_control_policy(payload: dict = Body(...)):
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
