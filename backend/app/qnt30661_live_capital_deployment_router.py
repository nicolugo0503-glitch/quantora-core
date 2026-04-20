from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["live-capital-deployment-orchestrator"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
DEPLOY_DIR = ARTIFACTS_DIR / "live_capital_deployment_orchestrator"

DEFAULT_POLICY = {
    "priority_deployment_count": 8,
    "minimum_live_readiness_score": 80.0,
    "minimum_execution_clearance_score": 77.0,
    "minimum_broker_readiness_score": 68.0,
    "minimum_strategy_capacity_score": 74.0,
    "maximum_slippage_risk_score": 26.0,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _activation():
    from backend.app import qnt30660_post_close_activation_router as activation
    return activation


def _strategic():
    from backend.app import qnt30650_strategic_decision_router as strategic
    return strategic


def _execution():
    from backend.app import qnt30629_strategy_execution_router as execution
    return execution


def _broker():
    from backend.app import qnt30631_broker_integration_router as broker
    return broker


def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]


def _path(email: str) -> Path:
    DEPLOY_DIR.mkdir(parents=True, exist_ok=True)
    return DEPLOY_DIR / f"{_safe(email)}.json"


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


def _deployment_book(dependencies: dict, policy: dict) -> list[dict]:
    activation = dependencies["activation"]
    strategic = dependencies["strategic"]
    execution = dependencies["execution"]
    broker = dependencies["broker"]
    grid = activation.get("activation_grid") or []
    lanes = activation.get("deployment_lanes") or []
    releases = activation.get("capital_release_matrix") or []
    directives = strategic.get("capital_directives") or []
    positions = broker.get("positions") or []
    summary = broker.get("summary") or {}
    deploy_notional = float(execution.get("total_deployed_notional") or execution.get("summary", {}).get("total_deployed_notional") or 0.0)
    base_count = max(int(policy.get("priority_deployment_count") or 8), 4)
    base_len = max(len(grid), 1)
    out = []
    for idx in range(min(base_count, max(base_len, base_count))):
        row = grid[idx % base_len] if grid else {}
        lane = lanes[idx % max(len(lanes), 1)] if lanes else {}
        release = releases[idx % max(len(releases), 1)] if releases else {}
        directive = directives[idx % max(len(directives), 1)] if directives else {}
        position = positions[idx % max(len(positions), 1)] if positions else {}
        live_readiness = min(100.0,
            float(row.get("activation_readiness_score") or 0.0) * 0.30 +
            float(row.get("deployment_readiness_score") or 0.0) * 0.24 +
            float(release.get("capital_release_score") or 72.0) * 0.18 +
            (float(directive.get("confidence") or 0.76) * 100.0) * 0.16 +
            (72.0 if summary.get("kill_switch") is False else 52.0) * 0.12
        )
        execution_clearance = min(100.0,
            float(row.get("capital_release_score") or 0.0) * 0.28 +
            float(lane.get("deployment_readiness_score") or 0.0) * 0.24 +
            (78.0 if release.get("release_status") == "release" else 58.0) * 0.22 +
            (70.0 if summary.get("mode") == "paper" else 82.0) * 0.14 +
            6.0
        )
        broker_ready = min(100.0,
            (72.0 if not summary.get("kill_switch") else 35.0) * 0.42 +
            min(float(summary.get("position_count") or 0.0) * 6.0, 18.0) +
            min(float(summary.get("fill_count") or 0.0) * 0.8, 14.0) +
            min(float(summary.get("strategy_positions") or 0.0) * 3.0, 12.0) +
            (10.0 if summary.get("mode") in {"paper", "live"} else 0.0)
        )
        strategy_capacity = min(100.0,
            float(row.get("strategy_alignment_score") or 0.0) * 0.42 +
            float(row.get("deployment_readiness_score") or 0.0) * 0.22 +
            min(deploy_notional / 50000.0, 18.0) +
            (float(position.get("market_value") or 0.0) / 20000.0)
        )
        slippage = max(4.0,
            39.0 - live_readiness * 0.15 - execution_clearance * 0.08 - broker_ready * 0.05 + idx * 0.7
        )
        out.append({
            "deployment_id": f"ldo_{idx+1:02d}",
            "allocator_name": row.get("allocator_name") or f"Allocator {idx+1}",
            "product_id": row.get("product_id") or f"QNT_DEPLOY_{idx+1:02d}",
            "strategy_id": row.get("strategy_id") or directive.get("strategy_id") or f"STRAT_{idx+1:02d}",
            "vehicle": row.get("vehicle") or "Institutional sleeve",
            "capital_target_millions": _round_money(row.get("planned_activation_millions") or 0.0),
            "live_readiness_score": _round_pct(live_readiness),
            "execution_clearance_score": _round_pct(execution_clearance),
            "broker_readiness_score": _round_pct(broker_ready),
            "strategy_capacity_score": _round_pct(strategy_capacity),
            "slippage_risk_score": _round_pct(slippage),
            "deployment_status": "deploy" if live_readiness >= float(policy.get("minimum_live_readiness_score") or 80.0) and execution_clearance >= float(policy.get("minimum_execution_clearance_score") or 77.0) and slippage <= float(policy.get("maximum_slippage_risk_score") or 26.0) else "stage",
        })
    return out


def _execution_lanes(dependencies: dict, book: list[dict], policy: dict) -> list[dict]:
    broker = dependencies["broker"]
    positions = broker.get("positions") or []
    out = []
    for idx, row in enumerate(book):
        position = positions[idx % max(len(positions), 1)] if positions else {}
        routing = min(100.0,
            float(row.get("execution_clearance_score") or 0.0) * 0.36 +
            float(row.get("broker_readiness_score") or 0.0) * 0.28 +
            float(row.get("strategy_capacity_score") or 0.0) * 0.18 +
            9.0
        )
        out.append({
            "lane_id": f"exec_{idx+1:02d}",
            "strategy_id": row.get("strategy_id"),
            "allocator_name": row.get("allocator_name"),
            "broker_route": position.get("symbol") or row.get("strategy_id") or "QNT-ROUTE",
            "routing_readiness_score": _round_pct(routing),
            "execution_window": "T+0 committee-governed live deployment",
            "lane_status": "greenlight" if routing >= float(policy.get("minimum_execution_clearance_score") or 77.0) else "hold",
        })
    return out


def _release_matrix(book: list[dict], lanes: list[dict], policy: dict) -> list[dict]:
    out = []
    for idx, row in enumerate(book):
        lane = lanes[idx % max(len(lanes), 1)] if lanes else {}
        release = min(100.0,
            float(row.get("live_readiness_score") or 0.0) * 0.34 +
            float(row.get("execution_clearance_score") or 0.0) * 0.24 +
            float(row.get("broker_readiness_score") or 0.0) * 0.16 +
            float(lane.get("routing_readiness_score") or 0.0) * 0.16 +
            7.0
        )
        out.append({
            "release_id": f"ldr_{idx+1:02d}",
            "allocator_name": row.get("allocator_name"),
            "strategy_id": row.get("strategy_id"),
            "product_id": row.get("product_id"),
            "live_release_score": _round_pct(release),
            "release_status": "release" if release >= float(policy.get("minimum_execution_clearance_score") or 77.0) and lane.get("lane_status") == "greenlight" else "hold",
        })
    return out


def _deployment_queue(book: list[dict], lanes: list[dict], releases: list[dict], policy: dict) -> list[dict]:
    out = []
    for idx, row in enumerate(book):
        lane = lanes[idx % max(len(lanes), 1)] if lanes else {}
        release = releases[idx % max(len(releases), 1)] if releases else {}
        status = "launch"
        if lane.get("lane_status") != "greenlight" or release.get("release_status") != "release":
            status = "prepare"
        if float(row.get("strategy_capacity_score") or 0.0) < float(policy.get("minimum_strategy_capacity_score") or 74.0) or float(row.get("broker_readiness_score") or 0.0) < float(policy.get("minimum_broker_readiness_score") or 68.0):
            status = "hold"
        out.append({
            "queue_id": f"ldq_{idx+1:02d}",
            "allocator_name": row.get("allocator_name"),
            "strategy_id": row.get("strategy_id"),
            "product_id": row.get("product_id"),
            "next_action": "release live capital and hand off to execution + broker layer" if status == "launch" else ("raise broker or capacity blockers before sending live capital" if status == "hold" else "complete execution routing package and confirm live release window"),
            "owner": "Live Capital Deployment Committee",
            "queue_status": status,
        })
    return out


def _overview(dependencies: dict, book: list[dict], lanes: list[dict], releases: list[dict], queue: list[dict]) -> dict:
    activation_overview = dependencies["activation"].get("post_close_activation_overview") or {}
    exec_summary = dependencies["execution"]
    broker_summary = dependencies["broker"].get("summary") or {}
    total_capital = sum(float(x.get("capital_target_millions") or 0.0) for x in book)
    deploy_count = len([x for x in book if x.get("deployment_status") == "deploy"])
    release_count = len([x for x in releases if x.get("release_status") == "release"])
    green_count = len([x for x in lanes if x.get("lane_status") == "greenlight"])
    launch_count = len([x for x in queue if x.get("queue_status") == "launch"])
    avg_live = sum(float(x.get("live_readiness_score") or 0.0) for x in book) / max(len(book), 1)
    avg_clearance = sum(float(x.get("execution_clearance_score") or 0.0) for x in book) / max(len(book), 1)
    avg_broker = sum(float(x.get("broker_readiness_score") or 0.0) for x in book) / max(len(book), 1)
    avg_slippage = sum(float(x.get("slippage_risk_score") or 0.0) for x in book) / max(len(book), 1)
    exec_return = float(exec_summary.get("portfolio_return_pct") or exec_summary.get("summary", {}).get("portfolio_return_pct") or 0.0)
    score = min(100.0,
        avg_live * 0.30 + avg_clearance * 0.22 + avg_broker * 0.18 + (100.0 - avg_slippage) * 0.10 + float(activation_overview.get("post_close_activation_score") or 72.0) * 0.12 + min(max(exec_return, 0.0), 10.0) * 0.8
    )
    posture = "live-capital-deployment-ready"
    if launch_count < max(2, len(queue) // 2):
        posture = "live-capital-deployment-building"
    if avg_slippage > float(DEFAULT_POLICY["maximum_slippage_risk_score"]):
        posture = "live-capital-deployment-constrained"
    return {
        "capital_deployment_target_millions": _round_money(total_capital),
        "deployment_ready_count": deploy_count,
        "release_ready_count": release_count,
        "greenlight_lane_count": green_count,
        "launch_ready_count": launch_count,
        "average_live_readiness": _round_pct(avg_live),
        "average_execution_clearance": _round_pct(avg_clearance),
        "average_broker_readiness": _round_pct(avg_broker),
        "average_slippage_risk": _round_pct(avg_slippage),
        "live_capital_deployment_score": _round_pct(score),
        "live_capital_deployment_posture": posture,
        "activation_posture": activation_overview.get("post_close_activation_posture"),
        "broker_mode": broker_summary.get("mode"),
    }


def _actions(overview: dict, queue: list[dict], releases: list[dict]) -> list[str]:
    actions = []
    if overview.get("live_capital_deployment_posture") != "live-capital-deployment-ready":
        actions.append("Tighten live routing, broker readiness, and release discipline before widening deployment velocity.")
    launches = [x for x in queue if x.get("queue_status") == "launch"][:3]
    if launches:
        actions.append("Deploy live capital for " + ", ".join(x.get("allocator_name") for x in launches) + ".")
    holds = [x for x in releases if x.get("release_status") != "release"]
    if holds:
        actions.append("Resolve live release blockers for " + ", ".join(x.get("allocator_name") for x in holds[:2]) + " before broker dispatch.")
    staged = [x for x in queue if x.get("queue_status") == "prepare"]
    if staged:
        actions.append(f"Stage {len(staged)} live deployment packets for committee release and broker routing.")
    return actions


def _build_summary(email: str):
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    activation = _safe_summary(_activation()._build_summary, email, fallback={
        "post_close_activation_overview": {"post_close_activation_score": 72.0, "post_close_activation_posture": "post-close-activation-building"},
        "activation_grid": [],
        "deployment_lanes": [],
        "capital_release_matrix": [],
    })
    strategic = _safe_summary(_strategic()._build_summary, email, fallback={
        "confidence_score": 76.0,
        "capital_directives": [],
        "product_decisions": [],
        "operating_posture": "strategic-building",
    })
    execution = _safe_summary(_execution()._summary, email, None, fallback={
        "strategy_count": 0,
        "trade_count": 0,
        "total_deployed_notional": 0.0,
        "portfolio_return_pct": 0.0,
        "total_pnl": 0.0,
    })
    broker_summary = _safe_summary(_broker()._summary, email, fallback={
        "mode": "paper", "kill_switch": False, "position_count": 0, "fill_count": 0, "strategy_positions": 0,
    })
    broker_positions = _safe_summary(_broker()._current_positions, email, fallback=[])
    broker = {
        "summary": broker_summary,
        "positions": broker_positions,
        "orders": [],
        "fills": [],
    }
    dependencies = {"activation": activation, "strategic": strategic, "execution": execution, "broker": broker}
    book = _deployment_book(dependencies, policy)
    lanes = _execution_lanes(dependencies, book, policy)
    releases = _release_matrix(book, lanes, policy)
    queue = _deployment_queue(book, lanes, releases, policy)
    overview = _overview(dependencies, book, lanes, releases, queue)
    return {
        "mission": "QNT30661",
        "generated_at": _now_iso(),
        "policy": policy,
        "live_capital_deployment_overview": overview,
        "deployment_book": book,
        "execution_lanes": lanes,
        "live_release_matrix": releases,
        "deployment_queue": queue,
        "deployment_dependencies": {
            "activation_posture": (activation.get("post_close_activation_overview") or {}).get("post_close_activation_posture"),
            "activation_score": (activation.get("post_close_activation_overview") or {}).get("post_close_activation_score"),
            "strategic_posture": strategic.get("operating_posture"),
            "strategic_score": strategic.get("confidence_score"),
            "execution_trade_count": execution.get("trade_count"),
            "execution_total_pnl": execution.get("total_pnl"),
            "broker_mode": (broker.get("summary") or {}).get("mode"),
            "broker_kill_switch": (broker.get("summary") or {}).get("kill_switch"),
            "broker_position_count": (broker.get("summary") or {}).get("position_count"),
        },
        "deployment_actions": _actions(overview, queue, releases),
    }


@router.get("/api/live-capital-deployment-orchestrator/summary")
def live_capital_deployment_summary():
    session = _require_user()
    return _build_summary(session.get("email"))


@router.post("/api/live-capital-deployment-orchestrator/run")
def live_capital_deployment_run(payload: dict = Body(default=None)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    summary = _build_summary(email)
    overview = summary.get("live_capital_deployment_overview") or {}
    run = {
        "run_id": f"ldo_{time.time_ns()}",
        "mission": "QNT30661",
        "trigger": (payload or {}).get("trigger") or "manual",
        "timestamp": _now_ts(),
        "generated_at": summary.get("generated_at"),
        "live_capital_deployment_posture": overview.get("live_capital_deployment_posture"),
        "live_capital_deployment_score": overview.get("live_capital_deployment_score"),
        "launch_ready_count": overview.get("launch_ready_count"),
        "release_ready_count": overview.get("release_ready_count"),
        "capital_deployment_target_millions": overview.get("capital_deployment_target_millions"),
    }
    store.setdefault("runs", []).insert(0, run)
    store["runs"] = store.get("runs", [])[:120]
    _save(email, store)
    return {"status": "ok", "summary": summary, "run": run}


@router.get("/api/live-capital-deployment-orchestrator/audit")
def live_capital_deployment_audit():
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    runs = store.get("runs") or []
    return {
        "mission": "QNT30661",
        "run_count": len(runs),
        "latest_run": runs[0] if runs else None,
        "runs": runs[:20],
        "policy": store.get("policy") or dict(DEFAULT_POLICY),
    }


@router.post("/api/live-capital-deployment-orchestrator/policy")
def live_capital_deployment_policy(payload: dict = Body(...)):
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
