from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["execution-governance-command"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
GOVERN_DIR = ARTIFACTS_DIR / "execution_governance_command"

DEFAULT_POLICY = {
    "priority_command_count": 8,
    "minimum_governance_score": 82.0,
    "minimum_supervisory_score": 78.0,
    "minimum_venue_quality_score": 70.0,
    "maximum_execution_stress_score": 28.0,
    "maximum_drift_score": 24.0,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _deployment():
    from backend.app import qnt30661_live_capital_deployment_router as deployment
    return deployment


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
    GOVERN_DIR.mkdir(parents=True, exist_ok=True)
    return GOVERN_DIR / f"{_safe(email)}.json"


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


def _governance_book(dependencies: dict, policy: dict) -> list[dict]:
    deployment = dependencies["deployment"]
    broker = dependencies["broker"]
    execution = dependencies["execution"]
    strategic = dependencies["strategic"]
    book = deployment.get("deployment_book") or []
    lanes = deployment.get("execution_lanes") or []
    releases = deployment.get("live_release_matrix") or []
    directives = strategic.get("capital_directives") or []
    positions = broker.get("positions") or []
    broker_summary = broker.get("summary") or {}
    execution_rows = execution.get("rows") or []
    base_count = max(int(policy.get("priority_command_count") or 8), 4)
    base_len = max(len(book), 1)
    out = []
    for idx in range(min(base_count, max(base_len, base_count))):
        row = book[idx % base_len] if book else {}
        lane = lanes[idx % max(len(lanes), 1)] if lanes else {}
        release = releases[idx % max(len(releases), 1)] if releases else {}
        directive = directives[idx % max(len(directives), 1)] if directives else {}
        position = positions[idx % max(len(positions), 1)] if positions else {}
        exec_row = execution_rows[idx % max(len(execution_rows), 1)] if execution_rows else {}
        governance_score = min(100.0,
            float(row.get("live_readiness_score") or 0.0) * 0.26 +
            float(row.get("execution_clearance_score") or 0.0) * 0.22 +
            float(release.get("live_release_score") or 0.0) * 0.18 +
            float(lane.get("routing_readiness_score") or 0.0) * 0.14 +
            (float(directive.get("confidence") or 0.76) * 100.0) * 0.10 +
            (8.0 if broker_summary.get("kill_switch") is False else -12.0)
        )
        supervisory_score = min(100.0,
            governance_score * 0.42 +
            (72.0 if broker_summary.get("mode") == "live" else 64.0) * 0.18 +
            float(exec_row.get("win_rate_pct") or 55.0) * 0.12 +
            float(exec_row.get("return_pct") or 0.0) * 1.5 +
            10.0
        )
        venue_quality = min(100.0,
            float(lane.get("routing_readiness_score") or 0.0) * 0.38 +
            float(row.get("broker_readiness_score") or 0.0) * 0.28 +
            min(float(broker_summary.get("fill_count") or 0.0) * 0.9, 16.0) +
            min(float(broker_summary.get("position_count") or 0.0) * 3.0, 12.0) +
            (8.0 if broker_summary.get("mode") in {"paper", "live"} else 0.0)
        )
        execution_stress = max(4.0,
            41.0 - governance_score * 0.16 - supervisory_score * 0.08 - venue_quality * 0.05 + idx * 0.8
        )
        drift_score = max(3.0,
            34.0 - float(row.get("strategy_capacity_score") or 0.0) * 0.10 - float(exec_row.get("win_rate_pct") or 50.0) * 0.06 + idx * 0.7
        )
        status = "approve"
        if supervisory_score < float(policy.get("minimum_supervisory_score") or 78.0) or venue_quality < float(policy.get("minimum_venue_quality_score") or 70.0):
            status = "supervise"
        if execution_stress > float(policy.get("maximum_execution_stress_score") or 28.0) or drift_score > float(policy.get("maximum_drift_score") or 24.0) or broker_summary.get("kill_switch"):
            status = "halt"
        out.append({
            "governance_id": f"egc_{idx+1:02d}",
            "allocator_name": row.get("allocator_name") or f"Allocator {idx+1}",
            "product_id": row.get("product_id") or f"QNT_EXEC_{idx+1:02d}",
            "strategy_id": row.get("strategy_id") or directive.get("strategy_id") or f"STRAT_{idx+1:02d}",
            "broker_route": lane.get("broker_route") or position.get("symbol") or "QNT-ROUTE",
            "governance_score": _round_pct(governance_score),
            "supervisory_score": _round_pct(supervisory_score),
            "venue_quality_score": _round_pct(venue_quality),
            "execution_stress_score": _round_pct(execution_stress),
            "drift_score": _round_pct(drift_score),
            "command_status": status,
        })
    return out


def _supervisory_lanes(dependencies: dict, book: list[dict], policy: dict) -> list[dict]:
    broker_summary = dependencies["broker"].get("summary") or {}
    out = []
    for idx, row in enumerate(book):
        lane_score = min(100.0,
            float(row.get("governance_score") or 0.0) * 0.34 +
            float(row.get("supervisory_score") or 0.0) * 0.24 +
            float(row.get("venue_quality_score") or 0.0) * 0.18 +
            (76.0 if broker_summary.get("mode") == "live" else 68.0) * 0.12 +
            6.0
        )
        out.append({
            "lane_id": f"egl_{idx+1:02d}",
            "allocator_name": row.get("allocator_name"),
            "strategy_id": row.get("strategy_id"),
            "oversight_window": "live execution governance cycle",
            "governance_lane_score": _round_pct(lane_score),
            "lane_status": "greenlight" if lane_score >= float(policy.get("minimum_supervisory_score") or 78.0) and row.get("command_status") != "halt" else ("hold" if row.get("command_status") == "halt" else "monitor"),
        })
    return out


def _command_matrix(book: list[dict], lanes: list[dict], policy: dict) -> list[dict]:
    out = []
    for idx, row in enumerate(book):
        lane = lanes[idx % max(len(lanes), 1)] if lanes else {}
        release = min(100.0,
            float(row.get("governance_score") or 0.0) * 0.36 +
            float(row.get("supervisory_score") or 0.0) * 0.24 +
            float(row.get("venue_quality_score") or 0.0) * 0.16 +
            float(lane.get("governance_lane_score") or 0.0) * 0.14 +
            6.0
        )
        status = "release" if release >= float(policy.get("minimum_governance_score") or 82.0) and lane.get("lane_status") == "greenlight" and row.get("command_status") == "approve" else ("hold" if row.get("command_status") == "halt" else "monitor")
        out.append({
            "matrix_id": f"egm_{idx+1:02d}",
            "allocator_name": row.get("allocator_name"),
            "strategy_id": row.get("strategy_id"),
            "product_id": row.get("product_id"),
            "command_release_score": _round_pct(release),
            "release_status": status,
        })
    return out


def _command_queue(book: list[dict], lanes: list[dict], matrix: list[dict], policy: dict) -> list[dict]:
    out = []
    for idx, row in enumerate(book):
        lane = lanes[idx % max(len(lanes), 1)] if lanes else {}
        release = matrix[idx % max(len(matrix), 1)] if matrix else {}
        status = "approve"
        if release.get("release_status") == "monitor" or lane.get("lane_status") == "monitor" or row.get("command_status") == "supervise":
            status = "supervise"
        if release.get("release_status") == "hold" or row.get("command_status") == "halt":
            status = "halt"
        next_action = "approve live execution with supervised routing and fairness oversight"
        if status == "supervise":
            next_action = "increase execution sampling, venue review, and slippage watch before widening risk"
        if status == "halt":
            next_action = "halt deployment expansion, invoke kill-switch review, and escalate to execution governance committee"
        out.append({
            "queue_id": f"egq_{idx+1:02d}",
            "allocator_name": row.get("allocator_name"),
            "strategy_id": row.get("strategy_id"),
            "product_id": row.get("product_id"),
            "next_action": next_action,
            "owner": "Execution Governance Committee",
            "queue_status": status,
        })
    return out


def _overview(dependencies: dict, book: list[dict], lanes: list[dict], matrix: list[dict], queue: list[dict]) -> dict:
    deployment_overview = dependencies["deployment"].get("live_capital_deployment_overview") or {}
    broker_summary = dependencies["broker"].get("summary") or {}
    total_capital = sum(float(x.get("capital_target_millions") or 0.0) for x in dependencies["deployment"].get("deployment_book") or [])
    approve_count = len([x for x in queue if x.get("queue_status") == "approve"])
    supervise_count = len([x for x in queue if x.get("queue_status") == "supervise"])
    halt_count = len([x for x in queue if x.get("queue_status") == "halt"])
    release_count = len([x for x in matrix if x.get("release_status") == "release"])
    avg_governance = sum(float(x.get("governance_score") or 0.0) for x in book) / max(len(book), 1)
    avg_supervisory = sum(float(x.get("supervisory_score") or 0.0) for x in book) / max(len(book), 1)
    avg_venue = sum(float(x.get("venue_quality_score") or 0.0) for x in book) / max(len(book), 1)
    avg_stress = sum(float(x.get("execution_stress_score") or 0.0) for x in book) / max(len(book), 1)
    avg_drift = sum(float(x.get("drift_score") or 0.0) for x in book) / max(len(book), 1)
    score = min(100.0,
        avg_governance * 0.28 + avg_supervisory * 0.22 + avg_venue * 0.16 + (100.0 - avg_stress) * 0.10 + (100.0 - avg_drift) * 0.08 + float(deployment_overview.get("live_capital_deployment_score") or 72.0) * 0.10
    )
    posture = "execution-governance-command-ready"
    if halt_count:
        posture = "execution-governance-command-constrained"
    elif supervise_count > approve_count:
        posture = "execution-governance-command-monitoring"
    return {
        "governed_capital_millions": _round_money(total_capital),
        "approve_count": approve_count,
        "supervise_count": supervise_count,
        "halt_count": halt_count,
        "release_ready_count": release_count,
        "average_governance_score": _round_pct(avg_governance),
        "average_supervisory_score": _round_pct(avg_supervisory),
        "average_venue_quality": _round_pct(avg_venue),
        "average_execution_stress": _round_pct(avg_stress),
        "average_drift_score": _round_pct(avg_drift),
        "execution_governance_score": _round_pct(score),
        "execution_governance_posture": posture,
        "deployment_posture": deployment_overview.get("live_capital_deployment_posture"),
        "broker_mode": broker_summary.get("mode"),
        "kill_switch": broker_summary.get("kill_switch"),
    }


def _actions(overview: dict, queue: list[dict], matrix: list[dict]) -> list[str]:
    actions = []
    if overview.get("execution_governance_posture") != "execution-governance-command-ready":
        actions.append("Tighten execution supervision, venue review, and stress controls before widening live routing authority.")
    approvals = [x for x in queue if x.get("queue_status") == "approve"][:3]
    if approvals:
        actions.append("Approve governed live execution for " + ", ".join(x.get("allocator_name") for x in approvals) + ".")
    monitored = [x for x in queue if x.get("queue_status") == "supervise"]
    if monitored:
        actions.append(f"Supervise {len(monitored)} execution lanes with enhanced slippage, fairness, and venue review.")
    holds = [x for x in matrix if x.get("release_status") == "hold"]
    if holds:
        actions.append("Escalate execution halt review for " + ", ".join(x.get("allocator_name") for x in holds[:2]) + ".")
    return actions


def _build_summary(email: str):
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    deployment = _safe_summary(_deployment()._build_summary, email, fallback={
        "live_capital_deployment_overview": {"live_capital_deployment_score": 74.0, "live_capital_deployment_posture": "live-capital-deployment-building"},
        "deployment_book": [],
        "execution_lanes": [],
        "live_release_matrix": [],
    })
    strategic = _safe_summary(_strategic()._build_summary, email, fallback={
        "confidence_score": 76.0,
        "capital_directives": [],
        "product_decisions": [],
        "operating_posture": "strategic-building",
    })
    execution = _safe_summary(_execution()._summary, email, None, fallback={
        "rows": [],
        "trade_count": 0,
        "strategy_count": 0,
        "total_deployed_notional": 0.0,
        "total_pnl": 0.0,
    })
    broker_summary = _safe_summary(_broker()._summary, email, fallback={
        "mode": "paper", "kill_switch": False, "position_count": 0, "fill_count": 0, "strategy_positions": 0,
    })
    broker_positions = _safe_summary(_broker()._current_positions, email, fallback=[])
    broker = {
        "summary": broker_summary,
        "positions": broker_positions,
    }
    dependencies = {"deployment": deployment, "strategic": strategic, "execution": execution, "broker": broker}
    book = _governance_book(dependencies, policy)
    lanes = _supervisory_lanes(dependencies, book, policy)
    matrix = _command_matrix(book, lanes, policy)
    queue = _command_queue(book, lanes, matrix, policy)
    overview = _overview(dependencies, book, lanes, matrix, queue)
    return {
        "mission": "QNT30662",
        "generated_at": _now_iso(),
        "policy": policy,
        "execution_governance_overview": overview,
        "governance_book": book,
        "supervisory_lanes": lanes,
        "command_matrix": matrix,
        "command_queue": queue,
        "governance_dependencies": {
            "deployment_posture": (deployment.get("live_capital_deployment_overview") or {}).get("live_capital_deployment_posture"),
            "deployment_score": (deployment.get("live_capital_deployment_overview") or {}).get("live_capital_deployment_score"),
            "strategic_posture": strategic.get("operating_posture"),
            "strategic_score": strategic.get("confidence_score"),
            "execution_trade_count": execution.get("trade_count"),
            "execution_total_pnl": execution.get("total_pnl"),
            "broker_mode": broker_summary.get("mode"),
            "broker_kill_switch": broker_summary.get("kill_switch"),
            "broker_position_count": broker_summary.get("position_count"),
            "broker_fill_count": broker_summary.get("fill_count"),
        },
        "governance_actions": _actions(overview, queue, matrix),
    }


@router.get("/api/execution-governance-command/summary")
def execution_governance_summary():
    session = _require_user()
    return _build_summary(session.get("email"))


@router.post("/api/execution-governance-command/run")
def execution_governance_run(payload: dict = Body(default=None)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    summary = _build_summary(email)
    overview = summary.get("execution_governance_overview") or {}
    run = {
        "run_id": f"egc_{time.time_ns()}",
        "mission": "QNT30662",
        "trigger": (payload or {}).get("trigger") or "manual",
        "timestamp": _now_ts(),
        "generated_at": summary.get("generated_at"),
        "execution_governance_posture": overview.get("execution_governance_posture"),
        "execution_governance_score": overview.get("execution_governance_score"),
        "approve_count": overview.get("approve_count"),
        "halt_count": overview.get("halt_count"),
        "governed_capital_millions": overview.get("governed_capital_millions"),
    }
    store.setdefault("runs", []).insert(0, run)
    store["runs"] = store.get("runs", [])[:120]
    _save(email, store)
    return {"status": "ok", "summary": summary, "run": run}


@router.get("/api/execution-governance-command/audit")
def execution_governance_audit():
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    runs = store.get("runs") or []
    return {
        "mission": "QNT30662",
        "run_count": len(runs),
        "latest_run": runs[0] if runs else None,
        "runs": runs[:20],
        "policy": store.get("policy") or dict(DEFAULT_POLICY),
    }


@router.post("/api/execution-governance-command/policy")
def execution_governance_policy(payload: dict = Body(...)):
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
