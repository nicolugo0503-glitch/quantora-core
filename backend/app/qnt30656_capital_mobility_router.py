from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["capital-mobility-control-plane"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
MOBILITY_DIR = ARTIFACTS_DIR / "capital_mobility_control_plane"

DEFAULT_POLICY = {
    "minimum_mobility_score": 74.0,
    "maximum_transfer_friction": 32.0,
    "maximum_jurisdiction_constraint": 38.0,
    "minimum_reserve_release_score": 70.0,
    "priority_queue_count": 6,
    "mobility_passport_floor": 72.0,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _strategic():
    from backend.app import qnt30650_strategic_decision_router as strategic
    return strategic


def _compliance():
    from backend.app import qnt30652_institutional_compliance_router as compliance
    return compliance


def _multi_fund():
    from backend.app import qnt30653_multi_fund_architecture_router as multi_fund
    return multi_fund


def _network():
    from backend.app import qnt30654_global_capital_network_router as network
    return network


def _treasury():
    from backend.app import qnt30655_sovereign_treasury_router as treasury
    return treasury


def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]


def _path(email: str) -> Path:
    MOBILITY_DIR.mkdir(parents=True, exist_ok=True)
    return MOBILITY_DIR / f"{_safe(email)}.json"


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


def _passport_templates():
    return [
        {"name": "US Master Treasury Passport", "jurisdiction": "US", "entity_type": "master_fund"},
        {"name": "Cayman Feeder Mobility Passport", "jurisdiction": "Cayman", "entity_type": "feeder_fund"},
        {"name": "Luxembourg Access Passport", "jurisdiction": "Luxembourg", "entity_type": "ucits_wrapper"},
        {"name": "Singapore Distribution Passport", "jurisdiction": "Singapore", "entity_type": "distribution_hub"},
        {"name": "UAE Capital Route Passport", "jurisdiction": "UAE", "entity_type": "regional_vehicle"},
        {"name": "UK Allocator Access Passport", "jurisdiction": "UK", "entity_type": "marketing_entity"},
    ]


def _entity_passports(dependencies: dict, policy: dict):
    network = dependencies["network"]
    compliance = dependencies["compliance"]
    treasury = dependencies["treasury"]
    corridors = network.get("capital_corridors") or []
    fx_books = treasury.get("fx_books") or []
    base = _passport_templates()
    out = []
    for idx, tpl in enumerate(base[: max(int(policy.get("priority_queue_count") or 6), 3)]):
        corridor = corridors[idx % max(len(corridors), 1)] if corridors else {}
        fx = fx_books[idx % max(len(fx_books), 1)] if fx_books else {}
        readiness = float(corridor.get("readiness_score") or 68.0)
        release = float(compliance.get("readiness_score") or 70.0)
        hedge = float(fx.get("hedge_ratio") or 55.0)
        passport_score = min(100.0, readiness * 0.42 + release * 0.33 + hedge * 0.18 + 8.0)
        constraint = max(6.0, 54.0 - readiness * 0.22 - release * 0.15 + idx * 2.8)
        out.append({
            "passport_id": f"cmp_{idx+1:02d}",
            "passport_name": tpl["name"],
            "jurisdiction": tpl["jurisdiction"],
            "entity_type": tpl["entity_type"],
            "paired_corridor": corridor.get("corridor_name") or tpl["jurisdiction"],
            "funding_pair": fx.get("pair") or "USD/USD",
            "passport_score": _round_pct(passport_score),
            "constraint_score": _round_pct(constraint),
            "status": "cleared" if passport_score >= float(policy.get("mobility_passport_floor") or 72.0) else "review",
        })
    return out


def _mobility_corridors(dependencies: dict, passports: list[dict], policy: dict):
    network = dependencies["network"]
    treasury = dependencies["treasury"]
    settlement = treasury.get("settlement_grid") or []
    corridors = network.get("capital_corridors") or []
    out = []
    for idx, corridor in enumerate(corridors[: max(int(policy.get("priority_queue_count") or 6), 1)]):
        passport = passports[idx % max(len(passports), 1)] if passports else {}
        settlement_row = settlement[idx % max(len(settlement), 1)] if settlement else {}
        readiness = float(corridor.get("readiness_score") or 0.0)
        reserve = float(corridor.get("reserve_mobility_score") or 0.0)
        stress = float(settlement_row.get("settlement_stress_score") or 28.0)
        friction = max(4.0, 52.0 - readiness * 0.25 - reserve * 0.18 + stress * 0.22)
        mobility_score = min(100.0, readiness * 0.37 + reserve * 0.29 + float(passport.get("passport_score") or 0.0) * 0.22 + (100.0 - friction) * 0.12)
        out.append({
            "mobility_id": f"mob_{idx+1:02d}",
            "corridor_name": corridor.get("corridor_name"),
            "launch_vehicle": corridor.get("launch_vehicle"),
            "allocator_segment": corridor.get("allocator_segment"),
            "mobility_score": _round_pct(mobility_score),
            "transfer_friction_score": _round_pct(friction),
            "jurisdiction_constraint_score": passport.get("constraint_score") or 0.0,
            "release_status": "release" if mobility_score >= float(policy.get("minimum_mobility_score") or 74.0) and friction <= float(policy.get("maximum_transfer_friction") or 32.0) else "stage",
        })
    return out


def _transfer_queues(dependencies: dict, mobility_corridors: list[dict], policy: dict):
    treasury = dependencies["treasury"]
    ladder = treasury.get("liquidity_ladder") or []
    routes = treasury.get("funding_routes") or []
    out = []
    for idx, corridor in enumerate(mobility_corridors[: max(int(policy.get("priority_queue_count") or 6), 1)]):
        ladder_bucket = ladder[idx % max(len(ladder), 1)] if ladder else {}
        route = routes[idx % max(len(routes), 1)] if routes else {}
        amount = float(route.get("target_capital") or 0.0) * (0.86 if corridor.get("release_status") == "release" else 0.42)
        out.append({
            "queue_id": f"queue_{idx+1:02d}",
            "corridor_name": corridor.get("corridor_name"),
            "liquidity_bucket": ladder_bucket.get("bucket") or "T1 Reserve Buffer",
            "planned_transfer_capital": _round_money(amount),
            "execution_window_hours": 12 + idx * 4,
            "priority": "HIGH" if corridor.get("release_status") == "release" else "WATCH",
            "status": "dispatch" if corridor.get("release_status") == "release" else "hold",
        })
    return out


def _reserve_release_matrix(dependencies: dict, mobility_corridors: list[dict], passports: list[dict], policy: dict):
    treasury = dependencies["treasury"]
    compliance = dependencies["compliance"]
    overview = treasury.get("treasury_overview") or {}
    compliance_score = float(compliance.get("readiness_score") or 70.0)
    treasury_readiness = float(overview.get("treasury_readiness_score") or 70.0)
    rows = []
    for idx, corridor in enumerate(mobility_corridors):
        passport = passports[idx % max(len(passports), 1)] if passports else {}
        release_score = min(100.0, float(corridor.get("mobility_score") or 0.0) * 0.36 + compliance_score * 0.28 + treasury_readiness * 0.22 + float(passport.get("passport_score") or 0.0) * 0.14)
        rows.append({
            "release_id": f"rel_{idx+1:02d}",
            "corridor_name": corridor.get("corridor_name"),
            "passport_name": passport.get("passport_name") or "mobility passport",
            "release_score": _round_pct(release_score),
            "reserve_release_status": "approve" if release_score >= float(policy.get("minimum_reserve_release_score") or 70.0) else "defer",
        })
    return rows


def _mobility_overview(dependencies: dict, mobility_corridors: list[dict], transfer_queues: list[dict], reserve_matrix: list[dict]):
    treasury = dependencies["treasury"]
    network = dependencies["network"]
    deployable = float((treasury.get("treasury_overview") or {}).get("deployable_capital") or 0.0)
    queued_capital = sum(float(x.get("planned_transfer_capital") or 0.0) for x in transfer_queues)
    avg_mobility = sum(float(x.get("mobility_score") or 0.0) for x in mobility_corridors) / max(len(mobility_corridors), 1)
    avg_friction = sum(float(x.get("transfer_friction_score") or 0.0) for x in mobility_corridors) / max(len(mobility_corridors), 1)
    avg_release = sum(float(x.get("release_score") or 0.0) for x in reserve_matrix) / max(len(reserve_matrix), 1)
    activated = sum(1 for x in mobility_corridors if x.get("release_status") == "release")
    capital_map = network.get("capital_map") or {}
    control_plane_score = min(100.0, avg_mobility * 0.34 + avg_release * 0.28 + (100.0 - avg_friction) * 0.18 + float(capital_map.get("network_utilization_score") or 0.0) * 0.20)
    posture = "mobility-open"
    if activated < max(2, len(mobility_corridors) // 2):
        posture = "mobility-governed"
    if avg_friction > 32.0:
        posture = "mobility-constrained"
    return {
        "deployable_capital": _round_money(deployable),
        "queued_transfer_capital": _round_money(queued_capital),
        "queue_coverage_ratio": _round_pct((queued_capital / max(deployable, 1.0)) * 100.0),
        "average_mobility_score": _round_pct(avg_mobility),
        "average_transfer_friction": _round_pct(avg_friction),
        "average_reserve_release_score": _round_pct(avg_release),
        "released_corridor_count": activated,
        "corridor_count": len(mobility_corridors),
        "control_plane_score": _round_pct(control_plane_score),
        "mobility_posture": posture,
    }


def _mobility_actions(overview: dict, queues: list[dict], reserve_matrix: list[dict], corridors: list[dict]):
    actions = []
    if overview.get("mobility_posture") != "mobility-open":
        actions.append("Tighten routing governance before expanding cross-border transfer velocity.")
    released = [x for x in queues if x.get("status") == "dispatch"][:3]
    if released:
        actions.append("Dispatch highest-priority queues first: " + ", ".join(x.get("corridor_name") for x in released) + ".")
    deferred = [x for x in reserve_matrix if x.get("reserve_release_status") != "approve"]
    if deferred:
        actions.append(f"Defer {len(deferred)} reserve releases until passport and compliance constraints clear.")
    constrained = [x for x in corridors if float(x.get("transfer_friction_score") or 0.0) > 30.0]
    if constrained:
        actions.append("Reduce transfer friction on " + ", ".join(x.get("corridor_name") for x in constrained[:2]) + " through treasury pre-staging.")
    return actions


def _build_summary(email: str):
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    strategic = _safe_summary(_strategic()._build_summary, email, {
        "operating_posture": "capital-preservation",
        "capital_overview": {"deployable_capital": 2000000.0},
    })
    compliance = _safe_summary(_compliance()._build_summary, email, {
        "release_status": "conditional",
        "readiness_score": 69.0,
    })
    multi_fund = _safe_summary(_multi_fund()._build_summary, email, {
        "operating_model": "seed-stack",
        "vehicle_stack": [],
    })
    network = _safe_summary(_network()._build_summary, email, {
        "network_posture": "controlled-expansion",
        "capital_corridors": [],
        "capital_map": {"network_utilization_score": 58.0},
    })
    treasury = _safe_summary(_treasury()._build_summary, email, {
        "treasury_overview": {
            "deployable_capital": 2000000.0,
            "treasury_readiness_score": 71.0,
            "treasury_posture": "treasury-guarded",
        },
        "liquidity_ladder": [],
        "fx_books": [],
        "funding_routes": [],
        "settlement_grid": [],
    })
    dependencies = {
        "strategic": strategic,
        "compliance": compliance,
        "multi_fund": multi_fund,
        "network": network,
        "treasury": treasury,
    }
    passports = _entity_passports(dependencies, policy)
    mobility_corridors = _mobility_corridors(dependencies, passports, policy)
    transfer_queues = _transfer_queues(dependencies, mobility_corridors, policy)
    reserve_matrix = _reserve_release_matrix(dependencies, mobility_corridors, passports, policy)
    overview = _mobility_overview(dependencies, mobility_corridors, transfer_queues, reserve_matrix)
    return {
        "mission": "QNT30656",
        "generated_at": _now_iso(),
        "policy": policy,
        "mobility_overview": overview,
        "entity_passports": passports,
        "mobility_corridors": mobility_corridors,
        "transfer_queues": transfer_queues,
        "reserve_release_matrix": reserve_matrix,
        "mobility_dependencies": {
            "strategic_posture": strategic.get("operating_posture"),
            "compliance_release_status": compliance.get("release_status"),
            "network_posture": network.get("network_posture"),
            "treasury_posture": (treasury.get("treasury_overview") or {}).get("treasury_posture"),
            "multi_fund_model": multi_fund.get("operating_model"),
        },
        "mobility_actions": _mobility_actions(overview, transfer_queues, reserve_matrix, mobility_corridors),
    }


@router.get("/api/capital-mobility-control-plane/summary")
def capital_mobility_summary():
    session = _require_user()
    return _build_summary(session.get("email"))


@router.post("/api/capital-mobility-control-plane/run")
def capital_mobility_run(payload: dict = Body(default=None)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    summary = _build_summary(email)
    overview = summary.get("mobility_overview") or {}
    run = {
        "run_id": f"cmc_{time.time_ns()}",
        "mission": "QNT30656",
        "trigger": (payload or {}).get("trigger") or "manual",
        "timestamp": _now_ts(),
        "generated_at": summary.get("generated_at"),
        "mobility_posture": overview.get("mobility_posture"),
        "control_plane_score": overview.get("control_plane_score"),
        "average_mobility_score": overview.get("average_mobility_score"),
        "average_transfer_friction": overview.get("average_transfer_friction"),
    }
    store.setdefault("runs", []).insert(0, run)
    store["runs"] = store.get("runs", [])[:120]
    _save(email, store)
    return {"status": "ok", "summary": summary, "run": run}


@router.get("/api/capital-mobility-control-plane/audit")
def capital_mobility_audit():
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    runs = store.get("runs") or []
    return {
        "mission": "QNT30656",
        "run_count": len(runs),
        "latest_run": runs[0] if runs else None,
        "runs": runs[:20],
        "policy": store.get("policy") or dict(DEFAULT_POLICY),
    }


@router.post("/api/capital-mobility-control-plane/policy")
def capital_mobility_policy(payload: dict = Body(...)):
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
