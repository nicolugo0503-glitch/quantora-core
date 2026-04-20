from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["post-close-capital-activation-grid"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ACTIVATION_DIR = ARTIFACTS_DIR / "post_close_capital_activation_grid"

DEFAULT_POLICY = {
    "priority_activation_count": 8,
    "minimum_activation_readiness": 79.0,
    "minimum_capital_release_score": 75.0,
    "minimum_strategy_alignment_score": 77.0,
    "minimum_deployment_readiness": 74.0,
    "maximum_activation_drag": 24.0,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _closing():
    from backend.app import qnt30659_institutional_closing_router as closing
    return closing


def _strategic():
    from backend.app import qnt30650_strategic_decision_router as strategic
    return strategic


def _treasury():
    from backend.app import qnt30655_sovereign_treasury_router as treasury
    return treasury


def _mobility():
    from backend.app import qnt30656_capital_mobility_router as mobility
    return mobility


def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]


def _path(email: str) -> Path:
    ACTIVATION_DIR.mkdir(parents=True, exist_ok=True)
    return ACTIVATION_DIR / f"{_safe(email)}.json"


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


def _safe_summary(builder, email: str, fallback: dict):
    try:
        return builder(email)
    except Exception:
        return dict(fallback)


def _activation_grid(dependencies: dict, policy: dict) -> list[dict]:
    closing = dependencies["closing"]
    strategic = dependencies["strategic"]
    treasury = dependencies["treasury"]
    mobility = dependencies["mobility"]
    closes = closing.get("close_book") or []
    release_queue = closing.get("final_release_queue") or []
    directives = strategic.get("capital_directives") or []
    products = strategic.get("product_decisions") or []
    routes = treasury.get("funding_routes") or []
    corridors = mobility.get("mobility_corridors") or mobility.get("transfer_queues") or []
    count = max(int(policy.get("priority_activation_count") or 8), 4)
    rows = []
    base_len = max(len(closes), 1)
    for idx in range(min(count, max(base_len, count))):
        close = closes[idx % base_len] if closes else {}
        rel = release_queue[idx % max(len(release_queue), 1)] if release_queue else {}
        directive = directives[idx % max(len(directives), 1)] if directives else {}
        product = products[idx % max(len(products), 1)] if products else {}
        route = routes[idx % max(len(routes), 1)] if routes else {}
        corridor = corridors[idx % max(len(corridors), 1)] if corridors else {}
        close_readiness = float(close.get("close_readiness_score") or 70.0)
        wire = float(close.get("wire_authority_score") or 70.0)
        strategic_alignment = min(100.0,
            (float(directive.get("confidence") or 0.76) * 100.0) * 0.52 +
            (84.0 if str(product.get("action") or "").upper() in {"SCALE", "ACTIVATE"} else 69.0) * 0.28 +
            close_readiness * 0.20
        )
        deployment = min(100.0,
            close_readiness * 0.34 +
            wire * 0.18 +
            float(route.get("route_readiness_score") or route.get("funding_readiness_score") or 72.0) * 0.20 +
            float(corridor.get("mobility_score") or corridor.get("corridor_score") or 71.0) * 0.18 +
            7.0
        )
        activation = min(100.0,
            strategic_alignment * 0.34 +
            deployment * 0.28 +
            close_readiness * 0.22 +
            wire * 0.16
        )
        drag = max(6.0, 41.0 - activation * 0.16 - deployment * 0.07 + idx * 0.9)
        rows.append({
            "activation_id": f"pcag_{idx+1:02d}",
            "allocator_name": close.get("allocator_name") or f"Allocator {idx+1}",
            "vehicle": close.get("vehicle") or route.get("vehicle_name") or "Institutional sleeve",
            "product_id": product.get("product_id") or f"QNT_ACTIVATION_{idx+1:02d}",
            "strategy_id": directive.get("strategy_id") or f"STRAT_{idx+1:02d}",
            "planned_activation_millions": _round_money(close.get("planned_commitment_millions") or route.get("planned_amount_millions") or 0.0),
            "activation_readiness_score": _round_pct(activation),
            "capital_release_score": _round_pct(wire),
            "strategy_alignment_score": _round_pct(strategic_alignment),
            "deployment_readiness_score": _round_pct(deployment),
            "activation_drag_score": _round_pct(drag),
            "status": "activate" if rel.get("release_status") == "launch" and activation >= float(policy.get("minimum_activation_readiness") or 79.0) and drag <= float(policy.get("maximum_activation_drag") or 24.0) else "stage",
        })
    return rows


def _deployment_lanes(dependencies: dict, grid: list[dict], policy: dict) -> list[dict]:
    treasury = dependencies["treasury"]
    mobility = dependencies["mobility"]
    routes = treasury.get("funding_routes") or []
    corridors = mobility.get("mobility_corridors") or mobility.get("transfer_queues") or []
    out = []
    for idx, row in enumerate(grid):
        route = routes[idx % max(len(routes), 1)] if routes else {}
        corridor = corridors[idx % max(len(corridors), 1)] if corridors else {}
        deploy = min(100.0,
            float(row.get("deployment_readiness_score") or 0.0) * 0.40 +
            float(route.get("route_readiness_score") or route.get("funding_readiness_score") or 71.0) * 0.24 +
            float(corridor.get("mobility_score") or corridor.get("corridor_score") or 70.0) * 0.22 +
            8.0
        )
        out.append({
            "lane_id": f"lane_{idx+1:02d}",
            "allocator_name": row.get("allocator_name"),
            "strategy_id": row.get("strategy_id"),
            "deployment_route": route.get("route_name") or route.get("route") or corridor.get("corridor_name") or corridor.get("route_name") or "governed-capital-route",
            "deployment_readiness_score": _round_pct(deploy),
            "capital_window": route.get("deployment_window") or route.get("window") or "T+1 / committee release",
            "lane_status": "greenlight" if deploy >= float(policy.get("minimum_deployment_readiness") or 74.0) else "hold",
        })
    return out


def _release_matrix(dependencies: dict, grid: list[dict], lanes: list[dict], policy: dict) -> list[dict]:
    strategic = dependencies["strategic"]
    products = strategic.get("product_decisions") or []
    out = []
    for idx, row in enumerate(grid):
        lane = lanes[idx % max(len(lanes), 1)] if lanes else {}
        product = products[idx % max(len(products), 1)] if products else {}
        product_pressure = 84.0 if str(product.get("action") or "").upper() in {"SCALE", "ACTIVATE"} else 68.0
        release = min(100.0,
            float(row.get("activation_readiness_score") or 0.0) * 0.36 +
            float(row.get("capital_release_score") or 0.0) * 0.22 +
            float(row.get("strategy_alignment_score") or 0.0) * 0.18 +
            float(lane.get("deployment_readiness_score") or 0.0) * 0.14 +
            product_pressure * 0.10
        )
        out.append({
            "release_id": f"arm_{idx+1:02d}",
            "allocator_name": row.get("allocator_name"),
            "product_id": row.get("product_id"),
            "strategy_id": row.get("strategy_id"),
            "capital_release_score": _round_pct(release),
            "release_status": "release" if release >= float(policy.get("minimum_capital_release_score") or 75.0) and lane.get("lane_status") == "greenlight" else "hold",
        })
    return out


def _activation_queue(grid: list[dict], lanes: list[dict], release_matrix: list[dict], policy: dict) -> list[dict]:
    out = []
    for idx, row in enumerate(grid):
        lane = lanes[idx % max(len(lanes), 1)] if lanes else {}
        release = release_matrix[idx % max(len(release_matrix), 1)] if release_matrix else {}
        status = "launch"
        if lane.get("lane_status") != "greenlight" or release.get("release_status") != "release":
            status = "prepare"
        if float(row.get("strategy_alignment_score") or 0.0) < float(policy.get("minimum_strategy_alignment_score") or 77.0):
            status = "hold"
        out.append({
            "queue_id": f"aq_{idx+1:02d}",
            "allocator_name": row.get("allocator_name"),
            "product_id": row.get("product_id"),
            "strategy_id": row.get("strategy_id"),
            "next_action": "deploy capital into governed strategy sleeve and start attribution clock" if status == "launch" else ("resolve strategic alignment or committee overrides before deployment" if status == "hold" else "finish route prep, confirm release window, and stage activation package"),
            "owner": "Post-Close Capital Activation Committee",
            "queue_status": status,
        })
    return out


def _overview(dependencies: dict, grid: list[dict], lanes: list[dict], release_matrix: list[dict], queue: list[dict]) -> dict:
    closing_overview = (dependencies["closing"].get("closing_command_overview") or {})
    strategic = dependencies["strategic"]
    strategic_score = float(strategic.get("confidence_score") or 76.0)
    treasury_score = float((dependencies["treasury"].get("treasury_overview") or {}).get("treasury_score") or 72.0)
    total_capital = sum(float(x.get("planned_activation_millions") or 0.0) for x in grid)
    activate_count = len([x for x in grid if x.get("status") == "activate"])
    release_count = len([x for x in release_matrix if x.get("release_status") == "release"])
    green_count = len([x for x in lanes if x.get("lane_status") == "greenlight"])
    launch_count = len([x for x in queue if x.get("queue_status") == "launch"])
    avg_activation = sum(float(x.get("activation_readiness_score") or 0.0) for x in grid) / max(len(grid), 1)
    avg_alignment = sum(float(x.get("strategy_alignment_score") or 0.0) for x in grid) / max(len(grid), 1)
    avg_release = sum(float(x.get("capital_release_score") or 0.0) for x in release_matrix) / max(len(release_matrix), 1)
    avg_drag = sum(float(x.get("activation_drag_score") or 0.0) for x in grid) / max(len(grid), 1)
    score = min(100.0,
        avg_activation * 0.34 + avg_alignment * 0.22 + avg_release * 0.18 + (100.0 - avg_drag) * 0.12 + strategic_score * 0.08 + treasury_score * 0.06
    )
    posture = "post-close-activation-ready"
    if launch_count < max(2, len(queue) // 2):
        posture = "post-close-activation-building"
    if avg_drag > 24.0:
        posture = "post-close-activation-constrained"
    return {
        "activation_target_millions": _round_money(total_capital),
        "activation_ready_count": activate_count,
        "release_ready_count": release_count,
        "greenlight_lane_count": green_count,
        "launch_ready_count": launch_count,
        "average_activation_readiness": _round_pct(avg_activation),
        "average_strategy_alignment": _round_pct(avg_alignment),
        "average_capital_release": _round_pct(avg_release),
        "average_activation_drag": _round_pct(avg_drag),
        "post_close_activation_score": _round_pct(score),
        "post_close_activation_posture": posture,
        "closing_command_posture": closing_overview.get("closing_command_posture"),
    }


def _actions(overview: dict, queue: list[dict], release_matrix: list[dict]) -> list[str]:
    actions = []
    if overview.get("post_close_activation_posture") != "post-close-activation-ready":
        actions.append("Tighten post-close deployment governance before accelerating capital activation.")
    launches = [x for x in queue if x.get("queue_status") == "launch"][:3]
    if launches:
        actions.append("Launch activation for " + ", ".join(x.get("allocator_name") for x in launches) + ".")
    holds = [x for x in release_matrix if x.get("release_status") != "release"]
    if holds:
        actions.append("Resolve capital release blockers for " + ", ".join(x.get("allocator_name") for x in holds[:2]) + " before sleeve deployment.")
    staged = [x for x in queue if x.get("queue_status") == "prepare"]
    if staged:
        actions.append(f"Stage {len(staged)} activation packages for committee release and treasury dispatch.")
    return actions


def _build_summary(email: str):
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    closing = _safe_summary(_closing()._build_summary, email, {
        "closing_command_overview": {"closing_command_score": 72.0, "closing_command_posture": "closing-command-building"},
        "close_book": [],
        "final_release_queue": [],
    })
    strategic = _safe_summary(_strategic()._build_summary, email, {
        "confidence_score": 76.0,
        "capital_directives": [],
        "product_decisions": [],
        "operating_posture": "strategic-building",
    })
    treasury = _safe_summary(_treasury()._build_summary, email, {
        "treasury_overview": {"treasury_score": 72.0, "treasury_posture": "balanced"},
        "funding_routes": [],
    })
    mobility = _safe_summary(_mobility()._build_summary, email, {
        "mobility_overview": {"mobility_score": 71.0, "mobility_posture": "governed-mobility"},
        "mobility_corridors": [],
        "transfer_queues": [],
    })
    dependencies = {"closing": closing, "strategic": strategic, "treasury": treasury, "mobility": mobility}
    grid = _activation_grid(dependencies, policy)
    lanes = _deployment_lanes(dependencies, grid, policy)
    release_matrix = _release_matrix(dependencies, grid, lanes, policy)
    queue = _activation_queue(grid, lanes, release_matrix, policy)
    overview = _overview(dependencies, grid, lanes, release_matrix, queue)
    return {
        "mission": "QNT30660",
        "generated_at": _now_iso(),
        "policy": policy,
        "post_close_activation_overview": overview,
        "activation_grid": grid,
        "deployment_lanes": lanes,
        "capital_release_matrix": release_matrix,
        "activation_queue": queue,
        "activation_dependencies": {
            "closing_command_posture": (closing.get("closing_command_overview") or {}).get("closing_command_posture"),
            "closing_command_score": (closing.get("closing_command_overview") or {}).get("closing_command_score"),
            "strategic_posture": strategic.get("operating_posture"),
            "strategic_score": strategic.get("confidence_score"),
            "treasury_posture": (treasury.get("treasury_overview") or {}).get("treasury_posture"),
            "treasury_score": (treasury.get("treasury_overview") or {}).get("treasury_score"),
            "mobility_posture": (mobility.get("mobility_overview") or {}).get("mobility_posture"),
            "mobility_score": (mobility.get("mobility_overview") or {}).get("mobility_score"),
        },
        "activation_actions": _actions(overview, queue, release_matrix),
    }


@router.get("/api/post-close-capital-activation-grid/summary")
def post_close_capital_activation_summary():
    session = _require_user()
    return _build_summary(session.get("email"))


@router.post("/api/post-close-capital-activation-grid/run")
def post_close_capital_activation_run(payload: dict = Body(default=None)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    summary = _build_summary(email)
    overview = summary.get("post_close_activation_overview") or {}
    run = {
        "run_id": f"pcag_{time.time_ns()}",
        "mission": "QNT30660",
        "trigger": (payload or {}).get("trigger") or "manual",
        "timestamp": _now_ts(),
        "generated_at": summary.get("generated_at"),
        "post_close_activation_posture": overview.get("post_close_activation_posture"),
        "post_close_activation_score": overview.get("post_close_activation_score"),
        "launch_ready_count": overview.get("launch_ready_count"),
        "release_ready_count": overview.get("release_ready_count"),
        "activation_target_millions": overview.get("activation_target_millions"),
    }
    store.setdefault("runs", []).insert(0, run)
    store["runs"] = store.get("runs", [])[:120]
    _save(email, store)
    return {"status": "ok", "summary": summary, "run": run}


@router.get("/api/post-close-capital-activation-grid/audit")
def post_close_capital_activation_audit():
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    runs = store.get("runs") or []
    return {
        "mission": "QNT30660",
        "run_count": len(runs),
        "latest_run": runs[0] if runs else None,
        "runs": runs[:20],
        "policy": store.get("policy") or dict(DEFAULT_POLICY),
    }


@router.post("/api/post-close-capital-activation-grid/policy")
def post_close_capital_activation_policy(payload: dict = Body(...)):
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
