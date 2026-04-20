from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["capital-dispatch-supervision-layer"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
DISPATCH_DIR = ARTIFACTS_DIR / "capital_dispatch_supervision_layer"

DEFAULT_POLICY = {
    "priority_dispatch_case_count": 8,
    "minimum_dispatch_readiness_score": 86.0,
    "minimum_supervision_clearance_score": 84.0,
    "minimum_execution_alignment_score": 80.0,
    "minimum_treasury_alignment_score": 78.0,
    "maximum_dispatch_stress_score": 23.0,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _release():
    from backend.app import qnt30664_institutional_release_authority_router as release
    return release


def _deployment():
    from backend.app import qnt30661_live_capital_deployment_router as deployment
    return deployment


def _governance():
    from backend.app import qnt30662_execution_governance_command_router as governance
    return governance


def _treasury():
    from backend.app import qnt30655_sovereign_treasury_router as treasury
    return treasury


def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]


def _path(email: str) -> Path:
    DISPATCH_DIR.mkdir(parents=True, exist_ok=True)
    return DISPATCH_DIR / f"{_safe(email)}.json"


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


def _dispatch_book(dependencies: dict, policy: dict) -> list[dict]:
    release = dependencies["release"]
    deployment = dependencies["deployment"]
    governance = dependencies["governance"]
    treasury = dependencies["treasury"]
    release_book = release.get("release_book") or []
    release_matrix = release.get("release_matrix") or []
    release_queue = release.get("release_queue") or []
    deployment_book = deployment.get("deployment_book") or []
    deployment_queue = deployment.get("deployment_queue") or []
    command_matrix = governance.get("command_matrix") or []
    governance_queue = governance.get("governance_queue") or []
    funding_routes = treasury.get("funding_routes") or []
    settlement_grid = treasury.get("settlement_grid") or []
    count = max(int(policy.get("priority_dispatch_case_count") or 8), 4)
    base_len = max(len(release_book), len(deployment_book), len(command_matrix), 1)
    out = []
    for idx in range(min(count, max(base_len, count))):
        rb = release_book[idx % max(len(release_book), 1)] if release_book else {}
        rm = release_matrix[idx % max(len(release_matrix), 1)] if release_matrix else {}
        rq = release_queue[idx % max(len(release_queue), 1)] if release_queue else {}
        db = deployment_book[idx % max(len(deployment_book), 1)] if deployment_book else {}
        dq = deployment_queue[idx % max(len(deployment_queue), 1)] if deployment_queue else {}
        cm = command_matrix[idx % max(len(command_matrix), 1)] if command_matrix else {}
        gq = governance_queue[idx % max(len(governance_queue), 1)] if governance_queue else {}
        fr = funding_routes[idx % max(len(funding_routes), 1)] if funding_routes else {}
        sg = settlement_grid[idx % max(len(settlement_grid), 1)] if settlement_grid else {}
        dispatch_readiness = min(100.0,
            float(rm.get("release_authority_score") or 0.0) * 0.22 +
            float(rb.get("release_readiness_score") or 0.0) * 0.20 +
            float(db.get("live_readiness_score") or 0.0) * 0.16 +
            float(db.get("execution_clearance_score") or 0.0) * 0.12 +
            float(cm.get("command_score") or 0.0) * 0.12 +
            float(fr.get("funding_route_score") or 0.0) * 0.08 +
            float(sg.get("settlement_readiness_score") or 0.0) * 0.06 +
            5.0
        )
        supervision_clearance = min(100.0,
            dispatch_readiness * 0.36 +
            float(cm.get("command_score") or 0.0) * 0.22 +
            float(db.get("execution_clearance_score") or 0.0) * 0.14 +
            float(rm.get("release_authority_score") or 0.0) * 0.10 +
            4.0
        )
        execution_alignment = min(100.0,
            float(db.get("execution_clearance_score") or 0.0) * 0.36 +
            float(db.get("broker_readiness_score") or 0.0) * 0.18 +
            float(cm.get("command_score") or 0.0) * 0.16 +
            (86.0 if dq.get("queue_status") == "launch" else 75.0 if dq.get("queue_status") == "prepare" else 58.0) * 0.12 +
            5.0
        )
        treasury_alignment = min(100.0,
            float(fr.get("funding_route_score") or 0.0) * 0.34 +
            float(sg.get("settlement_readiness_score") or 0.0) * 0.22 +
            float(rm.get("mobility_alignment_score") or 0.0) * 0.14 +
            float(dispatch_readiness) * 0.10 +
            6.0
        )
        dispatch_stress = max(4.0,
            33.0 - dispatch_readiness * 0.13 - supervision_clearance * 0.11 - execution_alignment * 0.07 - treasury_alignment * 0.06 + idx * 0.6
        )
        status = "dispatch"
        if execution_alignment < float(policy.get("minimum_execution_alignment_score") or 80.0) or treasury_alignment < float(policy.get("minimum_treasury_alignment_score") or 78.0):
            status = "review"
        if supervision_clearance < float(policy.get("minimum_supervision_clearance_score") or 84.0) or dispatch_stress > float(policy.get("maximum_dispatch_stress_score") or 23.0) or rq.get("queue_status") == "hold" or gq.get("queue_status") == "halt":
            status = "hold"
        out.append({
            "dispatch_case_id": f"dsp_{idx+1:02d}",
            "allocator_name": rb.get("allocator_name") or db.get("allocator_name") or cm.get("allocator_name") or f"Allocator {idx+1}",
            "strategy_id": rb.get("strategy_id") or db.get("strategy_id") or cm.get("strategy_id") or f"STRAT_{idx+1:02d}",
            "product_id": rb.get("product_id") or db.get("product_id") or cm.get("product_id") or f"QNT_DISPATCH_{idx+1:02d}",
            "jurisdiction": rb.get("jurisdiction") or fr.get("jurisdiction") or sg.get("jurisdiction") or "multi-jurisdiction",
            "capital_target_millions": _round_money(db.get("capital_target_millions") or fr.get("route_target_millions") or 0.0),
            "dispatch_readiness_score": _round_pct(dispatch_readiness),
            "supervision_clearance_score": _round_pct(supervision_clearance),
            "execution_alignment_score": _round_pct(execution_alignment),
            "treasury_alignment_score": _round_pct(treasury_alignment),
            "dispatch_stress_score": _round_pct(dispatch_stress),
            "dispatch_status": status,
        })
    return out


def _dispatch_lanes(book: list[dict], policy: dict) -> list[dict]:
    out = []
    for idx, row in enumerate(book):
        lane_score = min(100.0,
            float(row.get("dispatch_readiness_score") or 0.0) * 0.34 +
            float(row.get("supervision_clearance_score") or 0.0) * 0.24 +
            float(row.get("execution_alignment_score") or 0.0) * 0.14 +
            float(row.get("treasury_alignment_score") or 0.0) * 0.12 +
            6.0
        )
        out.append({
            "lane_id": f"dsl_{idx+1:02d}",
            "allocator_name": row.get("allocator_name"),
            "strategy_id": row.get("strategy_id"),
            "dispatch_window": "governed capital dispatch supervision cycle",
            "dispatch_lane_score": _round_pct(lane_score),
            "lane_status": "greenlight" if lane_score >= float(policy.get("minimum_dispatch_readiness_score") or 86.0) and row.get("dispatch_status") == "dispatch" else ("hold" if row.get("dispatch_status") == "hold" else "review"),
        })
    return out


def _dispatch_matrix(book: list[dict], lanes: list[dict], policy: dict) -> list[dict]:
    out = []
    for idx, row in enumerate(book):
        lane = lanes[idx % max(len(lanes), 1)] if lanes else {}
        dispatch_score = min(100.0,
            float(row.get("dispatch_readiness_score") or 0.0) * 0.30 +
            float(row.get("supervision_clearance_score") or 0.0) * 0.24 +
            float(row.get("execution_alignment_score") or 0.0) * 0.14 +
            float(row.get("treasury_alignment_score") or 0.0) * 0.12 +
            float(lane.get("dispatch_lane_score") or 0.0) * 0.12 +
            4.0
        )
        status = "dispatch" if dispatch_score >= float(policy.get("minimum_supervision_clearance_score") or 84.0) and lane.get("lane_status") == "greenlight" and row.get("dispatch_status") == "dispatch" else ("hold" if row.get("dispatch_status") == "hold" else "review")
        out.append({
            "matrix_id": f"dsm_{idx+1:02d}",
            "allocator_name": row.get("allocator_name"),
            "strategy_id": row.get("strategy_id"),
            "product_id": row.get("product_id"),
            "jurisdiction": row.get("jurisdiction"),
            "capital_target_millions": row.get("capital_target_millions"),
            "dispatch_authority_score": _round_pct(dispatch_score),
            "dispatch_authority_status": status,
        })
    return out


def _dispatch_queue(book: list[dict], lanes: list[dict], matrix: list[dict]) -> list[dict]:
    out = []
    for idx, row in enumerate(book):
        lane = lanes[idx % max(len(lanes), 1)] if lanes else {}
        authority = matrix[idx % max(len(matrix), 1)] if matrix else {}
        status = "dispatch"
        if authority.get("dispatch_authority_status") == "review" or lane.get("lane_status") == "review" or row.get("dispatch_status") == "review":
            status = "review"
        if authority.get("dispatch_authority_status") == "hold" or row.get("dispatch_status") == "hold":
            status = "hold"
        next_action = "authorize supervised capital dispatch and hand off to live execution governance"
        if status == "review":
            next_action = "refresh execution routing package, confirm treasury path, and re-run dispatch supervision"
        if status == "hold":
            next_action = "freeze capital dispatch, escalate stress package, and block downstream execution release"
        out.append({
            "queue_id": f"dsq_{idx+1:02d}",
            "allocator_name": row.get("allocator_name"),
            "strategy_id": row.get("strategy_id"),
            "product_id": row.get("product_id"),
            "jurisdiction": row.get("jurisdiction"),
            "capital_target_millions": row.get("capital_target_millions"),
            "next_action": next_action,
            "owner": "Capital Dispatch Supervision",
            "queue_status": status,
        })
    return out


def _overview(dependencies: dict, book: list[dict], lanes: list[dict], matrix: list[dict], queue: list[dict]) -> dict:
    release_overview = dependencies["release"].get("institutional_release_authority_overview") or {}
    deployment_overview = dependencies["deployment"].get("live_capital_deployment_overview") or {}
    governance_overview = dependencies["governance"].get("execution_governance_overview") or {}
    treasury_overview = dependencies["treasury"].get("treasury_overview") or {}
    total_capital = sum(float(x.get("capital_target_millions") or 0.0) for x in book)
    dispatch_count = len([x for x in queue if x.get("queue_status") == "dispatch"])
    review_count = len([x for x in queue if x.get("queue_status") == "review"])
    hold_count = len([x for x in queue if x.get("queue_status") == "hold"])
    green_count = len([x for x in lanes if x.get("lane_status") == "greenlight"])
    avg_readiness = sum(float(x.get("dispatch_readiness_score") or 0.0) for x in book) / max(len(book), 1)
    avg_clearance = sum(float(x.get("supervision_clearance_score") or 0.0) for x in book) / max(len(book), 1)
    avg_execution = sum(float(x.get("execution_alignment_score") or 0.0) for x in book) / max(len(book), 1)
    avg_treasury = sum(float(x.get("treasury_alignment_score") or 0.0) for x in book) / max(len(book), 1)
    avg_stress = sum(float(x.get("dispatch_stress_score") or 0.0) for x in book) / max(len(book), 1)
    score = min(100.0,
        avg_readiness * 0.26 + avg_clearance * 0.22 + avg_execution * 0.14 + avg_treasury * 0.12 + (100.0 - avg_stress) * 0.12 + float(governance_overview.get("execution_governance_score") or 76.0) * 0.08 + float(release_overview.get("institutional_release_authority_score") or 78.0) * 0.06
    )
    posture = "capital-dispatch-ready"
    if hold_count:
        posture = "capital-dispatch-constrained"
    elif review_count > dispatch_count:
        posture = "capital-dispatch-reviewing"
    return {
        "dispatch_governed_capital_millions": _round_money(total_capital),
        "dispatch_count": dispatch_count,
        "review_count": review_count,
        "hold_count": hold_count,
        "greenlight_lane_count": green_count,
        "average_dispatch_readiness": _round_pct(avg_readiness),
        "average_supervision_clearance": _round_pct(avg_clearance),
        "average_execution_alignment": _round_pct(avg_execution),
        "average_treasury_alignment": _round_pct(avg_treasury),
        "average_dispatch_stress": _round_pct(avg_stress),
        "capital_dispatch_supervision_score": _round_pct(score),
        "capital_dispatch_supervision_posture": posture,
        "execution_governance_posture": governance_overview.get("execution_governance_posture"),
        "live_capital_deployment_posture": deployment_overview.get("live_capital_deployment_posture"),
        "institutional_release_authority_posture": release_overview.get("institutional_release_authority_posture"),
        "treasury_posture": treasury_overview.get("treasury_posture"),
    }


def _actions(overview: dict, queue: list[dict], matrix: list[dict]) -> list[str]:
    actions = []
    if overview.get("capital_dispatch_supervision_posture") != "capital-dispatch-ready":
        actions.append("Tighten dispatch supervision, funding certainty, and execution controls before widening capital dispatch velocity.")
    dispatches = [x for x in queue if x.get("queue_status") == "dispatch"][:3]
    if dispatches:
        actions.append("Dispatch capital for " + ", ".join(x.get("allocator_name") for x in dispatches) + ".")
    reviews = [x for x in queue if x.get("queue_status") == "review"]
    if reviews:
        actions.append(f"Review {len(reviews)} dispatch cases for execution alignment and treasury sufficiency before releasing capital.")
    holds = [x for x in matrix if x.get("dispatch_authority_status") == "hold"]
    if holds:
        actions.append("Hold dispatch package for " + ", ".join(x.get("allocator_name") for x in holds[:2]) + ".")
    return actions


def _build_summary(email: str):
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    release = _safe_summary(_release()._build_summary, email, fallback={
        "institutional_release_authority_overview": {"institutional_release_authority_score": 76.0, "institutional_release_authority_posture": "institutional-release-authority-building"},
        "release_book": [],
        "release_matrix": [],
        "release_queue": [],
    })
    deployment = _safe_summary(_deployment()._build_summary, email, fallback={
        "live_capital_deployment_overview": {"live_capital_deployment_score": 74.0, "live_capital_deployment_posture": "live-capital-deployment-building"},
        "deployment_book": [],
        "deployment_queue": [],
    })
    governance = _safe_summary(_governance()._build_summary, email, fallback={
        "execution_governance_overview": {"execution_governance_score": 75.0, "execution_governance_posture": "execution-governance-building"},
        "command_matrix": [],
        "governance_queue": [],
    })
    treasury = _safe_summary(_treasury()._build_summary, email, fallback={
        "treasury_overview": {"treasury_readiness_score": 75.0, "treasury_posture": "treasury-building"},
        "funding_routes": [],
        "settlement_grid": [],
    })
    dependencies = {"release": release, "deployment": deployment, "governance": governance, "treasury": treasury}
    book = _dispatch_book(dependencies, policy)
    lanes = _dispatch_lanes(book, policy)
    matrix = _dispatch_matrix(book, lanes, policy)
    queue = _dispatch_queue(book, lanes, matrix)
    overview = _overview(dependencies, book, lanes, matrix, queue)
    return {
        "mission": "QNT30665",
        "generated_at": _now_iso(),
        "policy": policy,
        "capital_dispatch_supervision_overview": overview,
        "dispatch_book": book,
        "dispatch_lanes": lanes,
        "dispatch_matrix": matrix,
        "dispatch_queue": queue,
        "dispatch_dependencies": {
            "institutional_release_authority_posture": (release.get("institutional_release_authority_overview") or {}).get("institutional_release_authority_posture"),
            "institutional_release_authority_score": (release.get("institutional_release_authority_overview") or {}).get("institutional_release_authority_score"),
            "live_capital_deployment_posture": (deployment.get("live_capital_deployment_overview") or {}).get("live_capital_deployment_posture"),
            "live_capital_deployment_score": (deployment.get("live_capital_deployment_overview") or {}).get("live_capital_deployment_score"),
            "execution_governance_posture": (governance.get("execution_governance_overview") or {}).get("execution_governance_posture"),
            "execution_governance_score": (governance.get("execution_governance_overview") or {}).get("execution_governance_score"),
            "treasury_posture": (treasury.get("treasury_overview") or {}).get("treasury_posture"),
            "treasury_readiness_score": (treasury.get("treasury_overview") or {}).get("treasury_readiness_score"),
        },
        "dispatch_actions": _actions(overview, queue, matrix),
    }


@router.get("/api/capital-dispatch-supervision-layer/summary")
def capital_dispatch_supervision_summary():
    session = _require_user()
    return _build_summary(session.get("email"))


@router.post("/api/capital-dispatch-supervision-layer/run")
def capital_dispatch_supervision_run(payload: dict = Body(default=None)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    summary = _build_summary(email)
    overview = summary.get("capital_dispatch_supervision_overview") or {}
    run = {
        "run_id": f"dsp_{time.time_ns()}",
        "mission": "QNT30665",
        "trigger": (payload or {}).get("trigger") or "manual",
        "timestamp": _now_ts(),
        "generated_at": summary.get("generated_at"),
        "capital_dispatch_supervision_posture": overview.get("capital_dispatch_supervision_posture"),
        "capital_dispatch_supervision_score": overview.get("capital_dispatch_supervision_score"),
        "dispatch_count": overview.get("dispatch_count"),
        "hold_count": overview.get("hold_count"),
        "dispatch_governed_capital_millions": overview.get("dispatch_governed_capital_millions"),
    }
    store.setdefault("runs", []).insert(0, run)
    store["runs"] = store.get("runs", [])[:120]
    _save(email, store)
    return {"status": "ok", "summary": summary, "run": run}


@router.get("/api/capital-dispatch-supervision-layer/audit")
def capital_dispatch_supervision_audit():
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    runs = store.get("runs") or []
    return {
        "mission": "QNT30665",
        "run_count": len(runs),
        "latest_run": runs[0] if runs else None,
        "runs": runs[:20],
        "policy": store.get("policy") or dict(DEFAULT_POLICY),
    }


@router.post("/api/capital-dispatch-supervision-layer/policy")
def capital_dispatch_supervision_policy(payload: dict = Body(...)):
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
