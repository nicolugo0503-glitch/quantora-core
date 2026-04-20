from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["sovereign-treasury-command"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
TREASURY_DIR = ARTIFACTS_DIR / "sovereign_treasury_command"

DEFAULT_POLICY = {
    "minimum_liquidity_coverage_days": 90,
    "target_reserve_ratio": 18.0,
    "max_settlement_stress": 35.0,
    "max_fx_slippage_budget_bps": 28.0,
    "minimum_treasury_readiness": 72.0,
    "capital_mobility_floor": 65.0,
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


def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]


def _path(email: str) -> Path:
    TREASURY_DIR.mkdir(parents=True, exist_ok=True)
    return TREASURY_DIR / f"{_safe(email)}.json"


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


def _currency_templates():
    return {
        "US": "USD",
        "UAE": "AED",
        "Singapore": "SGD",
        "Luxembourg": "EUR",
        "UK": "GBP",
        "Mexico": "MXN",
        "Hong Kong": "HKD",
        "Cayman": "USD",
    }


def _liquidity_ladder(dependencies: dict, policy: dict):
    strategic = dependencies["strategic"]
    network = dependencies["network"]
    multi = dependencies["multi_fund"]
    deployable = float((strategic.get("capital_overview") or {}).get("deployable_capital") or 0.0)
    activated_capacity = float((network.get("capital_map") or {}).get("activated_corridor_capacity") or 0.0)
    reserve_ratio = float(policy.get("target_reserve_ratio") or 18.0) / 100.0
    reserve_capital = deployable * reserve_ratio
    operating_capital = max(deployable - reserve_capital, 0.0)
    vehicle_stack = multi.get("vehicle_stack") or []
    ladder = [
        {
            "bucket": "T0 Operating Cash",
            "days": 7,
            "target_capital": _round_money(operating_capital * 0.14),
            "role": "margin coverage, subscriptions, urgent settlements",
        },
        {
            "bucket": "T1 Reserve Buffer",
            "days": 30,
            "target_capital": _round_money(reserve_capital * 0.55),
            "role": "redemption defense, governance reserve, break handling",
        },
        {
            "bucket": "T2 Mobility Buffer",
            "days": int(policy.get("minimum_liquidity_coverage_days") or 90),
            "target_capital": _round_money(reserve_capital * 0.45 + activated_capacity * 0.08),
            "role": "cross-border staging and feeder support",
        },
        {
            "bucket": "T3 Strategic Deployment",
            "days": 180,
            "target_capital": _round_money(max(operating_capital * 0.86 - activated_capacity * 0.08, 0.0)),
            "role": f"longer-dated product seeding across {max(len(vehicle_stack), 1)} vehicles",
        },
    ]
    return ladder


def _fx_books(dependencies: dict, policy: dict):
    network = dependencies["network"]
    compliance = dependencies["compliance"]
    currency_map = _currency_templates()
    fx_books = []
    for corridor in network.get("capital_corridors") or []:
        origin = corridor.get("origin_jurisdiction") or "US"
        target = corridor.get("target_market") or "US"
        origin_ccy = currency_map.get(origin, "USD")
        target_ccy = currency_map.get(target, "USD")
        readiness = float(corridor.get("readiness_score") or 0.0)
        risk = float(corridor.get("jurisdiction_risk_score") or 0.0)
        slip = max(4.0, min(float(policy.get("max_fx_slippage_budget_bps") or 28.0), 8.0 + risk * 0.35 - readiness * 0.06))
        hedge_ratio = min(100.0, 42.0 + readiness * 0.48 + (8.0 if compliance.get("release_status") == "approved" else 0.0))
        fx_books.append({
            "corridor_id": corridor.get("corridor_id"),
            "pair": f"{origin_ccy}/{target_ccy}",
            "origin_currency": origin_ccy,
            "target_currency": target_ccy,
            "hedge_ratio": _round_pct(hedge_ratio),
            "slippage_budget_bps": _round_pct(slip),
            "funding_status": "funded" if corridor.get("activation_status") == "activate" else "watched",
        })
    return fx_books


def _settlement_grid(dependencies: dict, fx_books: list[dict], policy: dict):
    network = dependencies["network"]
    multi = dependencies["multi_fund"]
    corridors = network.get("capital_corridors") or []
    vehicles = multi.get("vehicle_stack") or []
    rows = []
    for idx, corridor in enumerate(corridors):
        fx = fx_books[idx % max(len(fx_books), 1)] if fx_books else {}
        vehicle = vehicles[idx % max(len(vehicles), 1)] if vehicles else {}
        readiness = float(corridor.get("readiness_score") or 0.0)
        mobility = float(corridor.get("reserve_mobility_score") or 0.0)
        stress = max(6.0, 68.0 - readiness * 0.38 - mobility * 0.24 + idx * 1.9)
        rows.append({
            "settlement_id": f"stl_{idx+1:02d}",
            "corridor_name": corridor.get("corridor_name"),
            "vehicle": vehicle.get("vehicle_name") or corridor.get("launch_vehicle") or "Quantora Treasury Vehicle",
            "settlement_window_days": 2 + (idx % 4),
            "settlement_stress_score": _round_pct(stress),
            "slippage_budget_bps": fx.get("slippage_budget_bps", 0.0),
            "liquidity_route": "prime-broker + feeder + treasury reserve" if corridor.get("activation_status") == "activate" else "reserve watchlist",
            "status": "ready" if stress <= float(policy.get("max_settlement_stress") or 35.0) else "monitor",
        })
    return rows


def _treasury_overview(dependencies: dict, ladder: list[dict], settlement: list[dict], fx_books: list[dict], policy: dict):
    strategic = dependencies["strategic"]
    network = dependencies["network"]
    compliance = dependencies["compliance"]
    deployable = float((strategic.get("capital_overview") or {}).get("deployable_capital") or 0.0)
    reserve = sum(float(x.get("target_capital") or 0.0) for x in ladder if "Reserve" in str(x.get("bucket")) or "Mobility" in str(x.get("bucket")))
    avg_stress = sum(float(x.get("settlement_stress_score") or 0.0) for x in settlement) / max(len(settlement), 1)
    avg_slip = sum(float(x.get("slippage_budget_bps") or 0.0) for x in fx_books) / max(len(fx_books), 1)
    mobility = float((network.get("readiness_matrix") or {}).get("reserve_mobility_score") or 0.0)
    readiness_score = min(100.0, 0.34 * mobility + 0.26 * float(compliance.get("readiness_score") or 0.0) + 0.22 * (100.0 - avg_stress) + 0.18 * (100.0 - avg_slip))
    posture = "treasury-active"
    if readiness_score < float(policy.get("minimum_treasury_readiness") or 72.0):
        posture = "treasury-guarded"
    if avg_stress > float(policy.get("max_settlement_stress") or 35.0):
        posture = "settlement-watch"
    return {
        "deployable_capital": _round_money(deployable),
        "reserve_capital": _round_money(reserve),
        "reserve_ratio": _round_pct((reserve / max(deployable, 1.0)) * 100.0),
        "average_settlement_stress": _round_pct(avg_stress),
        "average_fx_slippage_budget_bps": _round_pct(avg_slip),
        "capital_mobility_score": _round_pct(mobility),
        "treasury_readiness_score": _round_pct(readiness_score),
        "treasury_posture": posture,
    }


def _funding_routes(dependencies: dict, settlement: list[dict], ladder: list[dict]):
    network = dependencies["network"]
    segments = network.get("allocator_segments") or []
    routes = []
    for idx, row in enumerate(settlement[:6]):
        segment = segments[idx % max(len(segments), 1)] if segments else {}
        ladder_bucket = ladder[idx % max(len(ladder), 1)] if ladder else {}
        routes.append({
            "route_id": f"fund_{idx+1:02d}",
            "corridor_name": row.get("corridor_name"),
            "source_segment": segment.get("segment") or "institutional_allocator",
            "liquidity_bucket": ladder_bucket.get("bucket") or "T1 Reserve Buffer",
            "target_capital": _round_money((segment.get("expected_capacity") or 0.0) * 0.32 + (ladder_bucket.get("target_capital") or 0.0) * 0.18),
            "status": "release" if row.get("status") == "ready" else "hold",
        })
    return routes


def _treasury_actions(overview: dict, routes: list[dict], fx_books: list[dict], settlement: list[dict]):
    actions = []
    if overview.get("treasury_posture") == "treasury-active":
        actions.append("Release treasury staging across the highest-readiness corridors and reserve buckets.")
    else:
        actions.append("Hold discretionary treasury releases until settlement stress and readiness return inside policy.")
    largest_routes = sorted(routes, key=lambda x: float(x.get("target_capital") or 0.0), reverse=True)[:3]
    if largest_routes:
        actions.append("Fund priority routes first: " + ", ".join(r.get("corridor_name") for r in largest_routes) + ".")
    highest_hedges = sorted(fx_books, key=lambda x: float(x.get("hedge_ratio") or 0.0), reverse=True)[:2]
    if highest_hedges:
        actions.append("Pre-stage FX hedges for " + ", ".join(f.get("pair") for f in highest_hedges) + " before cross-border release.")
    monitored = [x for x in settlement if x.get("status") != "ready"]
    if monitored:
        actions.append(f"Escalate {len(monitored)} settlement routes for treasury supervision and operational readiness review.")
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
        "allocator_segments": [],
        "capital_map": {"activated_corridor_capacity": 0.0},
        "readiness_matrix": {"reserve_mobility_score": 58.0},
    })
    dependencies = {
        "strategic": strategic,
        "compliance": compliance,
        "multi_fund": multi_fund,
        "network": network,
    }
    ladder = _liquidity_ladder(dependencies, policy)
    fx_books = _fx_books(dependencies, policy)
    settlement = _settlement_grid(dependencies, fx_books, policy)
    funding_routes = _funding_routes(dependencies, settlement, ladder)
    overview = _treasury_overview(dependencies, ladder, settlement, fx_books, policy)
    return {
        "mission": "QNT30655",
        "generated_at": _now_iso(),
        "policy": policy,
        "treasury_overview": overview,
        "liquidity_ladder": ladder,
        "fx_books": fx_books,
        "settlement_grid": settlement,
        "funding_routes": funding_routes,
        "treasury_dependencies": {
            "strategic_posture": strategic.get("operating_posture"),
            "network_posture": network.get("network_posture"),
            "compliance_release_status": compliance.get("release_status"),
            "multi_fund_model": multi_fund.get("operating_model"),
        },
        "treasury_actions": _treasury_actions(overview, funding_routes, fx_books, settlement),
    }


@router.get("/api/sovereign-treasury-command/summary")
def sovereign_treasury_summary():
    session = _require_user()
    return _build_summary(session.get("email"))


@router.post("/api/sovereign-treasury-command/run")
def sovereign_treasury_run(payload: dict = Body(default=None)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    summary = _build_summary(email)
    run = {
        "run_id": f"stc_{time.time_ns()}",
        "mission": "QNT30655",
        "trigger": (payload or {}).get("trigger") or "manual",
        "timestamp": _now_ts(),
        "generated_at": summary.get("generated_at"),
        "treasury_posture": (summary.get("treasury_overview") or {}).get("treasury_posture"),
        "treasury_readiness_score": (summary.get("treasury_overview") or {}).get("treasury_readiness_score"),
        "average_settlement_stress": (summary.get("treasury_overview") or {}).get("average_settlement_stress"),
        "capital_mobility_score": (summary.get("treasury_overview") or {}).get("capital_mobility_score"),
    }
    store.setdefault("runs", []).insert(0, run)
    store["runs"] = store.get("runs", [])[:120]
    _save(email, store)
    return {"status": "ok", "summary": summary, "run": run}


@router.get("/api/sovereign-treasury-command/audit")
def sovereign_treasury_audit():
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    runs = store.get("runs") or []
    return {
        "mission": "QNT30655",
        "run_count": len(runs),
        "latest_run": runs[0] if runs else None,
        "runs": runs[:20],
        "policy": store.get("policy") or dict(DEFAULT_POLICY),
    }


@router.post("/api/sovereign-treasury-command/policy")
def sovereign_treasury_policy(payload: dict = Body(...)):
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
