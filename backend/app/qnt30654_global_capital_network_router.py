from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["global-capital-network"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
NETWORK_DIR = ARTIFACTS_DIR / "global_capital_network"

DEFAULT_POLICY = {
    "target_allocator_count": 24,
    "min_cross_border_readiness": 72.0,
    "max_jurisdiction_risk": 38.0,
    "priority_corridor_count": 5,
    "reserve_mobility_floor": 58.0,
    "activation_score_floor": 70.0,
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


def _compliance():
    from backend.app import qnt30652_institutional_compliance_router as compliance
    return compliance


def _multi_fund():
    from backend.app import qnt30653_multi_fund_architecture_router as multi_fund
    return multi_fund


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

def _corridor_templates():
    return [
        {"name": "US → Gulf Sovereign Capital", "origin": "US", "target": "UAE", "segment": "sovereign", "channel": "institutional-private-placement", "base_readiness": 86.0, "jurisdiction_risk": 24.0},
        {"name": "US → Singapore Family Office Network", "origin": "US", "target": "Singapore", "segment": "family_office", "channel": "allocator-coverage", "base_readiness": 82.0, "jurisdiction_risk": 19.0},
        {"name": "Luxembourg → European Private Bank Platform", "origin": "Luxembourg", "target": "UK", "segment": "private_bank", "channel": "fund_platform_distribution", "base_readiness": 79.0, "jurisdiction_risk": 22.0},
        {"name": "Cayman → Global Macro Allocator Route", "origin": "Cayman", "target": "US", "segment": "institutional_allocator", "channel": "consultant-led-raise", "base_readiness": 77.0, "jurisdiction_risk": 27.0},
        {"name": "US → Latin American Wealth Network", "origin": "US", "target": "Mexico", "segment": "wealth_platform", "channel": "cross-border-advisor-network", "base_readiness": 73.0, "jurisdiction_risk": 31.0},
        {"name": "Singapore → APAC Strategic Partners", "origin": "Singapore", "target": "Hong Kong", "segment": "strategic_partner", "channel": "regional-distribution-partner", "base_readiness": 76.0, "jurisdiction_risk": 28.0},
    ]


def _allocator_segments(summary: dict, policy: dict):
    growth = summary["growth"]
    strategic = summary["strategic"]
    multi = summary["multi_fund"]
    deployable = float((strategic.get("capital_overview") or {}).get("deployable_capital") or 0.0)
    network_score = float(multi.get("capital_network_score") or 0.0)
    capacity = float(growth.get("growth_capacity_score") or 0.0)
    base_count = int(policy.get("target_allocator_count") or 24)
    segments = [
        ("sovereign", 0.16, 5.6, "ticket size first"),
        ("pension", 0.14, 4.8, "consultant-led diligence"),
        ("family_office", 0.22, 2.9, "relationship compounding"),
        ("private_bank", 0.18, 3.6, "platform wrapper access"),
        ("endowment_foundation", 0.12, 2.4, "research narrative"),
        ("ria_advisory", 0.18, 1.4, "feeder-ready distribution"),
    ]
    out = []
    for idx, (name, weight, avg_ticket_m, motion) in enumerate(segments, start=1):
        count = max(1, round(base_count * weight))
        activation = min(100.0, network_score * 0.52 + capacity * 0.28 + 18.0 - idx)
        expected = deployable * weight * max(activation, 45.0) / 100.0
        out.append({
            "segment": name,
            "target_allocator_count": count,
            "average_ticket_millions": _round_money(avg_ticket_m),
            "activation_score": _round_pct(activation),
            "expected_capacity": _round_money(expected),
            "go_to_market_motion": motion,
        })
    return out


def _network_corridors(summary: dict, policy: dict):
    strategic = summary["strategic"]
    growth = summary["growth"]
    compliance = summary["compliance"]
    multi = summary["multi_fund"]
    products = strategic.get("product_decisions") or []
    channels = growth.get("channel_sequence") or []
    release = str(compliance.get("release_status") or "governed")
    readiness_floor = float(policy.get("min_cross_border_readiness") or 72.0)
    corridors = []
    templates = _corridor_templates()[: int(policy.get("priority_corridor_count") or 5)]
    for idx, tpl in enumerate(templates):
        product = products[idx % len(products)] if products else {}
        channel = channels[idx % len(channels)] if channels else {}
        vehicle = (multi.get("vehicle_stack") or [{}])[idx % max(len(multi.get("vehicle_stack") or []), 1)]
        activation_bias = 8.0 if str(product.get("action") or "").upper() == "SCALE" else 0.0
        activation_bias += 5.0 if str(channel.get("activation_priority") or "").upper() == "HIGH" else 0.0
        activation_bias += 10.0 if release == "approved" else (4.0 if release == "conditional" else -12.0)
        readiness = min(100.0, tpl["base_readiness"] + activation_bias)
        reserve_mobility = min(100.0, 40.0 + float(multi.get("capital_network_score") or 0.0) * 0.45 + idx * 2.5)
        corridor = {
            "corridor_id": f"gcn_{idx+1:02d}",
            "corridor_name": tpl["name"],
            "origin_jurisdiction": tpl["origin"],
            "target_market": tpl["target"],
            "allocator_segment": tpl["segment"],
            "distribution_channel": tpl["channel"],
            "launch_vehicle": vehicle.get("vehicle_name") or "Quantora Global Access Vehicle",
            "paired_product": product.get("product_name") or product.get("strategy_name") or "flagship allocation sleeve",
            "readiness_score": _round_pct(readiness),
            "reserve_mobility_score": _round_pct(reserve_mobility),
            "jurisdiction_risk_score": _round_pct(tpl["jurisdiction_risk"]),
            "activation_status": "activate" if readiness >= readiness_floor and reserve_mobility >= float(policy.get("reserve_mobility_floor") or 58.0) else "stage",
        }
        corridors.append(corridor)
    return corridors


def _readiness_matrix(summary: dict, corridors: list[dict], policy: dict):
    compliance = summary["compliance"]
    release = str(compliance.get("release_status") or "governed")
    readiness_score = float(compliance.get("readiness_score") or 0.0)
    approved = sum(1 for c in corridors if c.get("activation_status") == "activate")
    corridor_readiness = sum(float(c.get("readiness_score") or 0.0) for c in corridors) / max(len(corridors), 1)
    mobility = sum(float(c.get("reserve_mobility_score") or 0.0) for c in corridors) / max(len(corridors), 1)
    jurisdiction_risk = sum(float(c.get("jurisdiction_risk_score") or 0.0) for c in corridors) / max(len(corridors), 1)
    activation_score = min(100.0, corridor_readiness * 0.4 + mobility * 0.24 + readiness_score * 0.26 + approved * 3.0)
    posture = "global-active"
    if release == "blocked" or activation_score < float(policy.get("activation_score_floor") or 70.0):
        posture = "governed-staging"
    elif approved < max(2, len(corridors) // 2):
        posture = "controlled-expansion"
    return {
        "release_status": release,
        "approved_corridor_count": approved,
        "corridor_count": len(corridors),
        "corridor_readiness_score": _round_pct(corridor_readiness),
        "reserve_mobility_score": _round_pct(mobility),
        "jurisdiction_risk_score": _round_pct(jurisdiction_risk),
        "activation_score": _round_pct(activation_score),
        "network_posture": posture,
    }


def _capital_map(summary: dict, segments: list[dict], corridors: list[dict]):
    strategic = summary["strategic"]
    deployable = float((strategic.get("capital_overview") or {}).get("deployable_capital") or 0.0)
    total_segment_capacity = sum(float(s.get("expected_capacity") or 0.0) for s in segments)
    total_activated_corridor_capacity = sum(
        float(s.get("expected_capacity") or 0.0)
        for s in segments[: max(1, len(corridors))]
    )
    return {
        "deployable_capital": _round_money(deployable),
        "target_external_capacity": _round_money(total_segment_capacity),
        "activated_corridor_capacity": _round_money(total_activated_corridor_capacity),
        "capacity_coverage_ratio": _round_pct((total_segment_capacity / max(deployable, 1.0)) * 100.0),
    }


def _network_actions(summary: dict, matrix: dict, corridors: list[dict], segments: list[dict]):
    actions = []
    if matrix.get("network_posture") == "governed-staging":
        actions.append("Hold full global activation; release only staged corridors above policy thresholds.")
    else:
        actions.append("Launch highest-readiness corridors with feeder-ready documentation and allocator routing.")
    actions.append("Map each live corridor to a specific vehicle and investor transparency packet before capital solicitation.")
    low_risk = [c for c in corridors if float(c.get("jurisdiction_risk_score") or 0.0) <= 25.0]
    if low_risk:
        actions.append(f"Prioritize low-friction jurisdictions first: {', '.join(c['target_market'] for c in low_risk[:3])}.")
    strongest_segments = sorted(segments, key=lambda x: float(x.get("activation_score") or 0.0), reverse=True)[:3]
    actions.append("Concentrate allocator coverage on " + ", ".join(s.get("segment") for s in strongest_segments) + ".")
    return actions


def _build_summary(email: str):
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    strategic = _safe_summary(_strategic()._build_summary, email, {
        'operating_posture': 'capital-preservation',
        'confidence_score': 58.0,
        'capital_overview': {'deployable_capital': 1500000.0},
        'product_decisions': [],
    })
    growth = _safe_summary(_growth()._build_summary, email, {
        'autonomy_posture': 'sequenced-growth',
        'growth_capacity_score': 61.0,
        'channel_sequence': [],
    })
    compliance = _safe_summary(_compliance()._build_summary, email, {
        'release_status': 'conditional',
        'readiness_score': 68.0,
    })
    multi = _safe_summary(_multi_fund()._build_summary, email, {
        'operating_model': 'foundation-buildout',
        'capital_network_score': 63.0,
        'vehicle_stack': [],
    })
    dependencies = {
        "strategic": strategic,
        "growth": growth,
        "compliance": compliance,
        "multi_fund": multi,
    }
    segments = _allocator_segments(dependencies, policy)
    corridors = _network_corridors(dependencies, policy)
    readiness = _readiness_matrix(dependencies, corridors, policy)
    capital_map = _capital_map(dependencies, segments, corridors)
    constrained = [c for c in corridors if float(c.get("jurisdiction_risk_score") or 0.0) > float(policy.get("max_jurisdiction_risk") or 38.0)]
    return {
        "mission": "QNT30654",
        "generated_at": _now_iso(),
        "policy": policy,
        "network_posture": readiness.get("network_posture"),
        "activation_score": readiness.get("activation_score"),
        "approved_corridor_count": readiness.get("approved_corridor_count"),
        "corridor_count": readiness.get("corridor_count"),
        "allocator_segments": segments,
        "capital_corridors": corridors,
        "capital_map": capital_map,
        "readiness_matrix": readiness,
        "network_dependencies": {
            "strategic_posture": strategic.get("operating_posture"),
            "strategic_confidence_score": strategic.get("confidence_score"),
            "growth_posture": growth.get("autonomy_posture"),
            "growth_capacity_score": growth.get("growth_capacity_score"),
            "compliance_release_status": compliance.get("release_status"),
            "compliance_readiness_score": compliance.get("readiness_score"),
            "multi_fund_model": multi.get("operating_model"),
            "multi_fund_network_score": multi.get("capital_network_score"),
        },
        "risk_constraints": {
            "constrained_corridor_count": len(constrained),
            "constrained_corridors": constrained,
            "max_jurisdiction_risk": _round_pct(policy.get("max_jurisdiction_risk") or 38.0),
            "min_cross_border_readiness": _round_pct(policy.get("min_cross_border_readiness") or 72.0),
        },
        "network_actions": _network_actions(dependencies, readiness, corridors, segments),
    }


@router.get("/api/global-capital-network/summary")
def global_capital_network_summary():
    session = _require_user()
    return _build_summary(session.get("email"))


@router.post("/api/global-capital-network/run")
def global_capital_network_run(payload: dict = Body(default=None)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    summary = _build_summary(email)
    run = {
        "run_id": f"gcn_{time.time_ns()}",
        "mission": "QNT30654",
        "trigger": (payload or {}).get("trigger") or "manual",
        "timestamp": _now_ts(),
        "generated_at": summary.get("generated_at"),
        "network_posture": summary.get("network_posture"),
        "activation_score": summary.get("activation_score"),
        "approved_corridor_count": summary.get("approved_corridor_count"),
        "corridor_count": summary.get("corridor_count"),
        "capital_map": summary.get("capital_map"),
        "risk_constraints": summary.get("risk_constraints"),
    }
    store.setdefault("runs", []).insert(0, run)
    store["runs"] = store.get("runs", [])[:120]
    _save(email, store)
    return {"status": "ok", "summary": summary, "run": run}


@router.get("/api/global-capital-network/audit")
def global_capital_network_audit():
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    runs = store.get("runs") or []
    return {
        "mission": "QNT30654",
        "run_count": len(runs),
        "latest_run": runs[0] if runs else None,
        "runs": runs[:20],
        "policy": store.get("policy") or dict(DEFAULT_POLICY),
    }


@router.post("/api/global-capital-network/policy")
def global_capital_network_policy(payload: dict = Body(...)):
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
