from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["multi-fund-architecture"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
MULTI_FUND_DIR = ARTIFACTS_DIR / "multi_fund_architecture"

DEFAULT_POLICY = {
    "max_fund_count": 6,
    "min_seed_nav": 250000.0,
    "cross_fund_rebalance_floor": 65.0,
    "max_strategy_overlap_pct": 42.0,
    "target_cash_buffer_pct": 12.0,
    "jurisdiction_diversification_floor": 2,
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


def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]


def _path(email: str) -> Path:
    MULTI_FUND_DIR.mkdir(parents=True, exist_ok=True)
    return MULTI_FUND_DIR / f"{_safe(email)}.json"


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
            "funds": [],
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


def _fund_type_from_action(action: str, idx: int) -> str:
    a = str(action or "").upper()
    if a == "SCALE":
        return "flagship"
    if a == "INCUBATE":
        return "opportunistic"
    if idx == 0:
        return "master"
    return "satellite"


def _fund_status_from_action(action: str) -> str:
    a = str(action or "").upper()
    if a == "RETIRE":
        return "review"
    if a == "INCUBATE":
        return "staging"
    return "active"


def _seed_funds(email: str, store: dict, strategic: dict, growth: dict, compliance: dict):
    if store.get("funds"):
        return store.get("funds") or []

    products = strategic.get("product_decisions") or []
    directives = strategic.get("capital_directives") or []
    policy = store.get("policy") or {}
    deployable = float((strategic.get("capital_overview") or {}).get("deployable_capital") or 0.0)
    seed_floor = float(policy.get("min_seed_nav") or 250000.0)
    jurisdictions = ["US", "Cayman", "Luxembourg", "Singapore", "UAE", "UK"]

    funds = []
    for idx, product in enumerate(products[: int(policy.get("max_fund_count") or 6)]):
        strategy_name = str(product.get("strategy_name") or f"Sleeve {idx+1}")
        strategy_key = str(product.get("strategy_id") or strategy_name.lower().replace(" ", "_"))
        action = str(product.get("action") or "OBSERVE").upper()
        target_nav = max(seed_floor, deployable * max(float(product.get("recommended_seed_pct") or 0.0) / 100.0, 0.18))
        fund_name = f"Quantora {strategy_name.replace('_', ' ').title()} Fund {idx+1}"
        sleeves = [
            {
                "sleeve_id": f"{strategy_key}_core",
                "name": "core sleeve",
                "strategy_id": strategy_key,
                "target_weight_pct": _round_pct(max(float(product.get("recommended_seed_pct") or 0.0), 35.0)),
                "risk_budget_pct": _round_pct(max(18.0, min(42.0, float(product.get("product_score") or 0.0) * 0.35))),
            },
            {
                "sleeve_id": f"{strategy_key}_liquidity",
                "name": "liquidity reserve",
                "strategy_id": "cash_reserve",
                "target_weight_pct": _round_pct(float(policy.get("target_cash_buffer_pct") or 12.0)),
                "risk_budget_pct": 5.0,
            },
        ]
        directives_for_strategy = [d for d in directives if d.get("strategy_id") == strategy_key]
        funds.append({
            "fund_id": f"fund_{idx+1:02d}",
            "fund_name": fund_name,
            "fund_type": _fund_type_from_action(action, idx),
            "status": _fund_status_from_action(action),
            "jurisdiction": jurisdictions[idx % len(jurisdictions)],
            "base_currency": "USD",
            "target_nav": _round_money(target_nav),
            "allocated_nav": _round_money(target_nav * 0.82),
            "available_capacity": _round_money(target_nav * 0.18),
            "strategy_focus": strategy_name,
            "launch_priority": idx + 1,
            "product_score": _round_pct(product.get("product_score") or 0.0),
            "distribution_priority": product.get("distribution_priority") or "MODERATE",
            "seed_source": "strategic_product_decision",
            "cross_fund_role": "capital_receiver" if action in {"SCALE", "INCUBATE"} else "stability_anchor",
            "directives": directives_for_strategy,
            "sleeves": sleeves,
        })

    if not funds:
        confidence = float(strategic.get("confidence_score") or 0.0)
        posture = str(growth.get("autonomy_posture") or "sequenced-growth")
        release_status = str(compliance.get("release_status") or "governed")
        funds = [
            {
                "fund_id": "fund_01",
                "fund_name": "Quantora Master Allocation Fund",
                "fund_type": "master",
                "status": "active",
                "jurisdiction": "US",
                "base_currency": "USD",
                "target_nav": _round_money(max(seed_floor, deployable * 0.6 or seed_floor)),
                "allocated_nav": _round_money(max(seed_floor * 0.8, deployable * 0.48)),
                "available_capacity": _round_money(max(seed_floor * 0.2, deployable * 0.12)),
                "strategy_focus": posture,
                "launch_priority": 1,
                "product_score": _round_pct(confidence),
                "distribution_priority": "HIGH" if release_status != "blocked" else "CONTROLLED",
                "seed_source": "institutional_fallback",
                "cross_fund_role": "capital_receiver",
                "directives": [],
                "sleeves": [
                    {"sleeve_id": "master_core", "name": "core allocation", "strategy_id": "firm_core", "target_weight_pct": 68.0, "risk_budget_pct": 28.0},
                    {"sleeve_id": "master_liquidity", "name": "liquidity reserve", "strategy_id": "cash_reserve", "target_weight_pct": 12.0, "risk_budget_pct": 5.0},
                ],
            },
            {
                "fund_id": "fund_02",
                "fund_name": "Quantora Tactical Opportunities Fund",
                "fund_type": "satellite",
                "status": "staging",
                "jurisdiction": "Cayman",
                "base_currency": "USD",
                "target_nav": _round_money(max(seed_floor, deployable * 0.4 or seed_floor)),
                "allocated_nav": _round_money(max(seed_floor * 0.7, deployable * 0.3)),
                "available_capacity": _round_money(max(seed_floor * 0.3, deployable * 0.1)),
                "strategy_focus": "adaptive expansion",
                "launch_priority": 2,
                "product_score": _round_pct(max(confidence - 6.0, 0.0)),
                "distribution_priority": "MODERATE",
                "seed_source": "institutional_fallback",
                "cross_fund_role": "capital_receiver",
                "directives": [],
                "sleeves": [
                    {"sleeve_id": "tactical_core", "name": "tactical sleeve", "strategy_id": "adaptive_alpha", "target_weight_pct": 58.0, "risk_budget_pct": 34.0},
                    {"sleeve_id": "tactical_liquidity", "name": "liquidity reserve", "strategy_id": "cash_reserve", "target_weight_pct": 14.0, "risk_budget_pct": 5.0},
                ],
            },
        ]

    store["funds"] = funds
    _save(email, store)
    return funds


def _architecture_matrix(funds: list[dict], policy: dict):
    total_nav = sum(float(f.get("target_nav") or 0.0) for f in funds)
    rows = []
    for fund in funds:
        target_nav = float(fund.get("target_nav") or 0.0)
        overlap = 0.0
        if fund.get("fund_type") in {"satellite", "opportunistic"}:
            overlap += 18.0
        if str(fund.get("distribution_priority") or "").upper() == "HIGH":
            overlap += 11.0
        if fund.get("jurisdiction") in {"Cayman", "Luxembourg", "Singapore"}:
            overlap += 7.0
        overlap = min(overlap, 65.0)
        rows.append({
            "fund_id": fund.get("fund_id"),
            "fund_name": fund.get("fund_name"),
            "fund_type": fund.get("fund_type"),
            "jurisdiction": fund.get("jurisdiction"),
            "status": fund.get("status"),
            "target_nav": _round_money(target_nav),
            "target_weight_pct": _round_pct((target_nav / max(total_nav, 1.0)) * 100.0),
            "strategy_overlap_pct": _round_pct(overlap),
            "cash_buffer_pct": _round_pct(min(max(float(policy.get("target_cash_buffer_pct") or 12.0), 5.0), 25.0)),
            "distribution_priority": fund.get("distribution_priority"),
            "cross_fund_role": fund.get("cross_fund_role"),
        })
    return rows, _round_money(total_nav)


def _cross_fund_flows(funds: list[dict], strategic: dict, policy: dict):
    directives = strategic.get("capital_directives") or []
    receivers = [f for f in funds if str(f.get("cross_fund_role") or "") == "capital_receiver"] or funds
    anchors = [f for f in funds if str(f.get("cross_fund_role") or "") != "capital_receiver"] or funds
    flows = []
    floor = float(policy.get("cross_fund_rebalance_floor") or 65.0)
    for idx, directive in enumerate(directives[: min(len(directives), 6)]):
        confidence = float(directive.get("confidence") or 0.0) * 100.0
        if confidence < floor:
            continue
        source = anchors[idx % len(anchors)]
        target = receivers[idx % len(receivers)]
        if source.get("fund_id") == target.get("fund_id") and len(receivers) > 1:
            target = receivers[(idx + 1) % len(receivers)]
        amount = max(abs(float(directive.get("allocation_delta") or 0.0)) * 0.4, 50000.0)
        flows.append({
            "source_fund_id": source.get("fund_id"),
            "source_fund_name": source.get("fund_name"),
            "target_fund_id": target.get("fund_id"),
            "target_fund_name": target.get("fund_name"),
            "amount": _round_money(amount),
            "driver": directive.get("strategy_name") or directive.get("strategy_id"),
            "action": directive.get("action") or "HOLD",
            "confidence_score": _round_pct(confidence),
        })
    return flows


def _vehicle_stack(funds: list[dict], compliance: dict):
    release_status = str(compliance.get("release_status") or "governed")
    stack = []
    for idx, fund in enumerate(funds):
        stack.append({
            "fund_id": fund.get("fund_id"),
            "vehicle_name": fund.get("fund_name"),
            "entity_type": "master-feeder" if idx == 0 else ("feeder" if idx % 2 else "sleeve vehicle"),
            "jurisdiction": fund.get("jurisdiction"),
            "launch_readiness": "ready" if release_status != "blocked" and str(fund.get("status")) == "active" else "staged",
            "reporting_mode": "institutional" if idx == 0 else "look-through",
        })
    return stack


def _capital_network_score(funds: list[dict], growth: dict, compliance: dict, policy: dict):
    diversified = len({f.get("jurisdiction") for f in funds})
    release = str(compliance.get("release_status") or "governed")
    growth_capacity = float(growth.get("growth_capacity_score") or 0.0)
    base = growth_capacity * 0.55
    base += min(diversified * 8.0, 24.0)
    if release == "approved":
        base += 18.0
    elif release == "conditional":
        base += 8.0
    base -= max(float(policy.get("jurisdiction_diversification_floor") or 2) - diversified, 0.0) * 10.0
    return _round_pct(min(max(base, 0.0), 100.0))


def _operating_model(funds: list[dict], flows: list[dict], compliance: dict, score: float):
    if str(compliance.get("release_status") or "") == "blocked":
        return "governed-ring-fence"
    if len(funds) >= 3 and len(flows) >= 2 and score >= 78.0:
        return "institutional-multi-vehicle"
    if score >= 60.0:
        return "sequenced-multi-fund-expansion"
    return "foundation-buildout"


def _build_summary(email: str):
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    strategic = _strategic()._build_summary(email)
    growth = _growth()._build_summary(email)
    compliance = _compliance()._build_summary(email)
    funds = _seed_funds(email, store, strategic, growth, compliance)
    matrix, total_target_nav = _architecture_matrix(funds, policy)
    flows = _cross_fund_flows(funds, strategic, policy)
    vehicles = _vehicle_stack(funds, compliance)
    network_score = _capital_network_score(funds, growth, compliance, policy)
    model = _operating_model(funds, flows, compliance, network_score)
    overlap_breaches = [r for r in matrix if float(r.get("strategy_overlap_pct") or 0.0) > float(policy.get("max_strategy_overlap_pct") or 42.0)]

    return {
        "mission": "QNT30653",
        "generated_at": _now_iso(),
        "operating_model": model,
        "capital_network_score": network_score,
        "fund_count": len(funds),
        "jurisdiction_count": len({f.get("jurisdiction") for f in funds}),
        "total_target_nav": _round_money(total_target_nav),
        "policy": policy,
        "fund_matrix": matrix,
        "cross_fund_flows": flows,
        "vehicle_stack": vehicles,
        "allocation_dependencies": {
            "strategic_posture": strategic.get("operating_posture"),
            "strategic_confidence_score": strategic.get("confidence_score"),
            "growth_posture": growth.get("autonomy_posture"),
            "growth_capacity_score": growth.get("growth_capacity_score"),
            "compliance_release_status": compliance.get("release_status"),
            "compliance_readiness_score": compliance.get("readiness_score"),
        },
        "risk_constraints": {
            "overlap_breach_count": len(overlap_breaches),
            "overlap_breaches": overlap_breaches,
            "target_cash_buffer_pct": _round_pct(policy.get("target_cash_buffer_pct") or 12.0),
        },
        "execution_agenda": [
            "Stand up governed master-feeder structure with explicit sleeve ownership.",
            "Route strategic directives into cross-fund transfer plans instead of single-vehicle reallocations.",
            "Attach jurisdiction controls and investor transparency packets per vehicle.",
            "Enforce overlap limits before scaling any feeder or satellite sleeve.",
        ],
    }


@router.get("/api/multi-fund-architecture/summary")
def multi_fund_architecture_summary():
    session = _require_user()
    return _build_summary(session.get("email"))


@router.post("/api/multi-fund-architecture/run")
def multi_fund_architecture_run(payload: dict = Body(default=None)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    summary = _build_summary(email)
    run = {
        "run_id": f"mfa_{time.time_ns()}",
        "mission": "QNT30653",
        "trigger": (payload or {}).get("trigger") or "manual",
        "timestamp": _now_ts(),
        "generated_at": summary.get("generated_at"),
        "operating_model": summary.get("operating_model"),
        "capital_network_score": summary.get("capital_network_score"),
        "fund_count": summary.get("fund_count"),
        "jurisdiction_count": summary.get("jurisdiction_count"),
        "total_target_nav": summary.get("total_target_nav"),
        "cross_fund_flows": summary.get("cross_fund_flows"),
        "risk_constraints": summary.get("risk_constraints"),
    }
    store.setdefault("runs", []).insert(0, run)
    store["runs"] = store.get("runs", [])[:120]
    _save(email, store)
    return {"status": "ok", "summary": summary, "run": run}


@router.get("/api/multi-fund-architecture/audit")
def multi_fund_architecture_audit():
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    runs = store.get("runs") or []
    return {
        "mission": "QNT30653",
        "run_count": len(runs),
        "latest_run": runs[0] if runs else None,
        "runs": runs[:20],
        "policy": store.get("policy") or dict(DEFAULT_POLICY),
    }


@router.post("/api/multi-fund-architecture/policy")
def multi_fund_architecture_policy(payload: dict = Body(...)):
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
