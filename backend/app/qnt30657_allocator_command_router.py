from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["allocator-command-network"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
NETWORK_DIR = ARTIFACTS_DIR / "allocator_command_network"

DEFAULT_POLICY = {
    "allocator_priority_count": 8,
    "minimum_allocator_conviction": 72.0,
    "maximum_relationship_gap": 34.0,
    "minimum_conversion_readiness": 68.0,
    "minimum_command_score": 74.0,
    "minimum_ticket_capture_ratio": 58.0,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _strategic():
    from backend.app import qnt30650_strategic_decision_router as strategic
    return strategic


def _growth():
    from backend.app import qnt30651_autonomous_growth_router as growth
    return growth


def _network():
    from backend.app import qnt30654_global_capital_network_router as network
    return network


def _treasury():
    from backend.app import qnt30655_sovereign_treasury_router as treasury
    return treasury


def _mobility():
    from backend.app import qnt30656_capital_mobility_router as mobility
    return mobility


def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]


def _path(email: str) -> Path:
    NETWORK_DIR.mkdir(parents=True, exist_ok=True)
    return NETWORK_DIR / f"{_safe(email)}.json"


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


def _allocator_templates():
    return [
        {"name": "North America Sovereign Desk", "segment": "sovereign", "region": "US", "coverage_mode": "direct-principal"},
        {"name": "Global Macro Consultant Desk", "segment": "institutional_allocator", "region": "US", "coverage_mode": "consultant-led"},
        {"name": "Family Office Compounding Desk", "segment": "family_office", "region": "Singapore", "coverage_mode": "relationship-compounding"},
        {"name": "Private Bank Platform Desk", "segment": "private_bank", "region": "UK", "coverage_mode": "platform-distribution"},
        {"name": "Endowment Foundation Research Desk", "segment": "endowment_foundation", "region": "US", "coverage_mode": "research-led"},
        {"name": "RIA Advisory Expansion Desk", "segment": "ria_advisory", "region": "US", "coverage_mode": "feeder-enabled"},
        {"name": "LatAm Wealth Corridor Desk", "segment": "wealth_platform", "region": "Mexico", "coverage_mode": "cross-border-advisor"},
        {"name": "Gulf Strategic Capital Desk", "segment": "strategic_partner", "region": "UAE", "coverage_mode": "capital-partnership"},
    ]


def _allocator_book(dependencies: dict, policy: dict):
    network = dependencies["network"]
    mobility = dependencies["mobility"]
    treasury = dependencies["treasury"]
    strategic = dependencies["strategic"]
    growth = dependencies["growth"]
    segments = network.get("allocator_segments") or []
    corridors = network.get("capital_corridors") or []
    transfer_queues = mobility.get("transfer_queues") or []
    routes = treasury.get("funding_routes") or []
    strategy_rankings = strategic.get("strategy_rankings") or []
    channel_sequence = growth.get("channel_sequence") or []
    priority_count = max(int(policy.get("allocator_priority_count") or 8), 3)
    templates = _allocator_templates()[:priority_count]
    out = []
    for idx, tpl in enumerate(templates):
        segment = segments[idx % max(len(segments), 1)] if segments else {}
        corridor = corridors[idx % max(len(corridors), 1)] if corridors else {}
        queue = transfer_queues[idx % max(len(transfer_queues), 1)] if transfer_queues else {}
        route = routes[idx % max(len(routes), 1)] if routes else {}
        strategy = strategy_rankings[idx % max(len(strategy_rankings), 1)] if strategy_rankings else {}
        channel = channel_sequence[idx % max(len(channel_sequence), 1)] if channel_sequence else {}
        conviction = min(100.0,
            float(segment.get("activation_score") or 66.0) * 0.28 +
            float(corridor.get("readiness_score") or 68.0) * 0.22 +
            float(route.get("route_score") or 62.0) * 0.16 +
            float(strategy.get("allocation_score") or strategy.get("score") or 64.0) * 0.18 +
            (12.0 if str(queue.get("status") or "").lower() == "dispatch" else 4.0)
        )
        relationship_gap = max(6.0,
            54.0 - float(segment.get("activation_score") or 60.0) * 0.18 - float(corridor.get("reserve_mobility_score") or 58.0) * 0.12 + idx * 2.4
        )
        expected_ticket = float(segment.get("average_ticket_millions") or 2.0) * (1.08 + idx * 0.03)
        conversion_readiness = min(100.0,
            conviction * 0.44 +
            (100.0 - relationship_gap) * 0.22 +
            float(corridor.get("reserve_mobility_score") or 58.0) * 0.18 +
            (10.0 if str(channel.get("activation_priority") or "").upper() == "HIGH" else 3.0)
        )
        out.append({
            "allocator_id": f"acn_{idx+1:02d}",
            "allocator_name": tpl["name"],
            "segment": segment.get("segment") or tpl["segment"],
            "coverage_region": tpl["region"],
            "coverage_mode": tpl["coverage_mode"],
            "priority_strategy": strategy.get("strategy_name") or strategy.get("strategy_id") or "flagship allocation sleeve",
            "linked_corridor": corridor.get("corridor_name") or tpl["region"],
            "funding_route": route.get("route_name") or route.get("source_segment") or "capital routing queue",
            "expected_ticket_millions": _round_money(expected_ticket),
            "allocator_conviction_score": _round_pct(conviction),
            "relationship_gap_score": _round_pct(relationship_gap),
            "conversion_readiness_score": _round_pct(conversion_readiness),
            "status": "engage" if conviction >= float(policy.get("minimum_allocator_conviction") or 72.0) and conversion_readiness >= float(policy.get("minimum_conversion_readiness") or 68.0) else "nurture",
        })
    return out


def _command_routes(dependencies: dict, allocator_book: list[dict], policy: dict):
    mobility = dependencies["mobility"]
    treasury = dependencies["treasury"]
    queues = mobility.get("transfer_queues") or []
    release_matrix = mobility.get("reserve_release_matrix") or []
    liquidity_ladder = treasury.get("liquidity_ladder") or []
    out = []
    for idx, row in enumerate(allocator_book):
        queue = queues[idx % max(len(queues), 1)] if queues else {}
        release = release_matrix[idx % max(len(release_matrix), 1)] if release_matrix else {}
        ladder = liquidity_ladder[idx % max(len(liquidity_ladder), 1)] if liquidity_ladder else {}
        ticket_capture = min(100.0,
            float(row.get("conversion_readiness_score") or 0.0) * 0.42 +
            float(release.get("release_score") or 66.0) * 0.24 +
            (18.0 if str(queue.get("status") or "").lower() == "dispatch" else 6.0)
        )
        command_score = min(100.0,
            float(row.get("allocator_conviction_score") or 0.0) * 0.33 +
            float(row.get("conversion_readiness_score") or 0.0) * 0.25 +
            float(release.get("release_score") or 0.0) * 0.18 +
            ticket_capture * 0.14 +
            (10.0 if str(ladder.get("release_status") or "").lower() in {"active", "deploy", "release"} else 4.0)
        )
        out.append({
            "command_id": f"cmd_{idx+1:02d}",
            "allocator_name": row.get("allocator_name"),
            "linked_corridor": row.get("linked_corridor"),
            "liquidity_bucket": ladder.get("bucket") or queue.get("liquidity_bucket") or "T1 Reserve Buffer",
            "planned_ticket_millions": row.get("expected_ticket_millions") or 0.0,
            "ticket_capture_ratio": _round_pct(ticket_capture),
            "command_score": _round_pct(command_score),
            "release_dependency": release.get("reserve_release_status") or "defer",
            "status": "command" if command_score >= float(policy.get("minimum_command_score") or 74.0) and ticket_capture >= float(policy.get("minimum_ticket_capture_ratio") or 58.0) else "monitor",
        })
    return out


def _engagement_queue(allocator_book: list[dict], command_routes: list[dict]):
    out = []
    for idx, row in enumerate(allocator_book):
        cmd = command_routes[idx % max(len(command_routes), 1)] if command_routes else {}
        out.append({
            "queue_id": f"eng_{idx+1:02d}",
            "allocator_name": row.get("allocator_name"),
            "segment": row.get("segment"),
            "engagement_motion": row.get("coverage_mode"),
            "planned_ticket_millions": row.get("expected_ticket_millions") or 0.0,
            "next_action": "open investment committee sequence" if cmd.get("status") == "command" else "continue diligence and narrative compounding",
            "status": "activate" if cmd.get("status") == "command" else "stage",
        })
    return out


def _coverage_matrix(allocator_book: list[dict], command_routes: list[dict], policy: dict):
    rows = []
    for idx, row in enumerate(allocator_book):
        cmd = command_routes[idx % max(len(command_routes), 1)] if command_routes else {}
        conversion = float(row.get("conversion_readiness_score") or 0.0)
        gap = float(row.get("relationship_gap_score") or 0.0)
        score = min(100.0, conversion * 0.38 + float(cmd.get("command_score") or 0.0) * 0.34 + (100.0 - gap) * 0.18 + 6.0)
        rows.append({
            "coverage_id": f"cov_{idx+1:02d}",
            "allocator_name": row.get("allocator_name"),
            "coverage_score": _round_pct(score),
            "relationship_gap_score": _round_pct(gap),
            "coverage_status": "ready" if gap <= float(policy.get("maximum_relationship_gap") or 34.0) and score >= float(policy.get("minimum_conversion_readiness") or 68.0) else "build",
        })
    return rows


def _command_overview(dependencies: dict, allocator_book: list[dict], command_routes: list[dict], engagement_queue: list[dict], coverage_matrix: list[dict]):
    network = dependencies["network"]
    mobility = dependencies["mobility"]
    treasury = dependencies["treasury"]
    capital_map = network.get("capital_map") or {}
    mobility_overview = mobility.get("mobility_overview") or {}
    treasury_overview = treasury.get("treasury_overview") or {}
    total_ticket = sum(float(x.get("expected_ticket_millions") or 0.0) for x in allocator_book)
    commanded = [x for x in command_routes if x.get("status") == "command"]
    activated = [x for x in engagement_queue if x.get("status") == "activate"]
    avg_command = sum(float(x.get("command_score") or 0.0) for x in command_routes) / max(len(command_routes), 1)
    avg_cov = sum(float(x.get("coverage_score") or 0.0) for x in coverage_matrix) / max(len(coverage_matrix), 1)
    avg_gap = sum(float(x.get("relationship_gap_score") or 0.0) for x in coverage_matrix) / max(len(coverage_matrix), 1)
    command_network_score = min(100.0,
        avg_command * 0.34 +
        avg_cov * 0.24 +
        (100.0 - avg_gap) * 0.14 +
        float(mobility_overview.get("control_plane_score") or 0.0) * 0.16 +
        float(treasury_overview.get("treasury_readiness_score") or 0.0) * 0.12
    )
    posture = "allocator-command-active"
    if len(commanded) < max(2, len(command_routes) // 2):
        posture = "allocator-command-building"
    if avg_gap > 34.0:
        posture = "allocator-command-constrained"
    return {
        "target_external_capacity": _round_money(float(capital_map.get("target_external_capacity") or 0.0)),
        "allocator_ticket_pipeline_millions": _round_money(total_ticket),
        "commanded_allocator_count": len(commanded),
        "activated_allocator_count": len(activated),
        "allocator_count": len(allocator_book),
        "average_command_score": _round_pct(avg_command),
        "average_coverage_score": _round_pct(avg_cov),
        "average_relationship_gap": _round_pct(avg_gap),
        "ticket_pipeline_coverage_ratio": _round_pct((total_ticket / max(float(capital_map.get("target_external_capacity") or 1.0), 1.0)) * 100.0),
        "command_network_score": _round_pct(command_network_score),
        "allocator_command_posture": posture,
    }


def _command_actions(overview: dict, command_routes: list[dict], engagement_queue: list[dict], coverage_matrix: list[dict]):
    actions = []
    if overview.get("allocator_command_posture") != "allocator-command-active":
        actions.append("Tighten allocator coverage and upgrade conviction before opening full institutional outreach velocity.")
    top_commands = [x for x in command_routes if x.get("status") == "command"][:3]
    if top_commands:
        actions.append("Prioritize allocator command routes for " + ", ".join(x.get("allocator_name") for x in top_commands) + ".")
    staged = [x for x in engagement_queue if x.get("status") != "activate"]
    if staged:
        actions.append(f"Continue diligence compounding for {len(staged)} allocator relationships before capital committee conversion.")
    gaps = [x for x in coverage_matrix if x.get("coverage_status") != "ready"]
    if gaps:
        actions.append("Reduce relationship gaps on " + ", ".join(x.get("allocator_name") for x in gaps[:2]) + " with targeted product and corridor evidence.")
    return actions


def _build_summary(email: str):
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    strategic = _safe_summary(_strategic()._build_summary, email, {
        "operating_posture": "capital-preservation",
        "strategy_rankings": [],
    })
    growth = _safe_summary(_growth()._build_summary, email, {
        "growth_capacity_score": 66.0,
        "channel_sequence": [],
    })
    network = _safe_summary(_network()._build_summary, email, {
        "network_posture": "controlled-expansion",
        "allocator_segments": [],
        "capital_corridors": [],
        "capital_map": {"target_external_capacity": 1.0},
    })
    treasury = _safe_summary(_treasury()._build_summary, email, {
        "treasury_overview": {"treasury_readiness_score": 70.0},
        "funding_routes": [],
        "liquidity_ladder": [],
    })
    mobility = _safe_summary(_mobility()._build_summary, email, {
        "mobility_overview": {"control_plane_score": 68.0},
        "transfer_queues": [],
        "reserve_release_matrix": [],
    })
    dependencies = {
        "strategic": strategic,
        "growth": growth,
        "network": network,
        "treasury": treasury,
        "mobility": mobility,
    }
    allocator_book = _allocator_book(dependencies, policy)
    command_routes = _command_routes(dependencies, allocator_book, policy)
    engagement_queue = _engagement_queue(allocator_book, command_routes)
    coverage_matrix = _coverage_matrix(allocator_book, command_routes, policy)
    overview = _command_overview(dependencies, allocator_book, command_routes, engagement_queue, coverage_matrix)
    return {
        "mission": "QNT30657",
        "generated_at": _now_iso(),
        "policy": policy,
        "allocator_command_overview": overview,
        "allocator_book": allocator_book,
        "command_routes": command_routes,
        "engagement_queue": engagement_queue,
        "coverage_matrix": coverage_matrix,
        "allocator_command_dependencies": {
            "strategic_posture": strategic.get("operating_posture"),
            "growth_capacity_score": growth.get("growth_capacity_score"),
            "network_posture": network.get("network_posture"),
            "treasury_posture": (treasury.get("treasury_overview") or {}).get("treasury_posture"),
            "mobility_posture": (mobility.get("mobility_overview") or {}).get("mobility_posture"),
        },
        "allocator_command_actions": _command_actions(overview, command_routes, engagement_queue, coverage_matrix),
    }


@router.get("/api/allocator-command-network/summary")
def allocator_command_summary():
    session = _require_user()
    return _build_summary(session.get("email"))


@router.post("/api/allocator-command-network/run")
def allocator_command_run(payload: dict = Body(default=None)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    summary = _build_summary(email)
    overview = summary.get("allocator_command_overview") or {}
    run = {
        "run_id": f"acn_{time.time_ns()}",
        "mission": "QNT30657",
        "trigger": (payload or {}).get("trigger") or "manual",
        "timestamp": _now_ts(),
        "generated_at": summary.get("generated_at"),
        "allocator_command_posture": overview.get("allocator_command_posture"),
        "command_network_score": overview.get("command_network_score"),
        "commanded_allocator_count": overview.get("commanded_allocator_count"),
        "average_relationship_gap": overview.get("average_relationship_gap"),
    }
    store.setdefault("runs", []).insert(0, run)
    store["runs"] = store.get("runs", [])[:120]
    _save(email, store)
    return {"status": "ok", "summary": summary, "run": run}


@router.get("/api/allocator-command-network/audit")
def allocator_command_audit():
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    runs = store.get("runs") or []
    return {
        "mission": "QNT30657",
        "run_count": len(runs),
        "latest_run": runs[0] if runs else None,
        "runs": runs[:20],
        "policy": store.get("policy") or dict(DEFAULT_POLICY),
    }


@router.post("/api/allocator-command-network/policy")
def allocator_command_policy(payload: dict = Body(...)):
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
