from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["global-capital-routing"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ROUTING_DIR = ARTIFACTS_DIR / "global_capital_routing"

DEFAULT_POLICY = {
    "minimum_routing_score": 84.0,
    "minimum_allocation_score": 78.0,
    "minimum_orchestration_score": 78.0,
    "minimum_brain_score": 78.0,
    "minimum_governance_score": 78.0,
    "minimum_compliance_score": 78.0,
    "maximum_region_load_pct": 45.0,
    "maximum_exception_pressure": 22.0,
    "maximum_break_pressure": 18.0,
    "maximum_drawdown_pct": 14.0,
}

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _artifact_file(folder: str, email: str) -> Path:
    return ARTIFACTS_DIR / folder / f"{_safe(email)}.json"

def _path(email: str) -> Path:
    ROUTING_DIR.mkdir(parents=True, exist_ok=True)
    return ROUTING_DIR / f"{_safe(email)}.json"

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

def _read_json(path: Path, fallback):
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback

def _latest_run(store: dict) -> dict:
    runs = store.get("runs") or []
    return runs[0] if runs else {}

def _artifact_inputs(email: str) -> dict:
    return {
        "cross_fund": _read_json(_artifact_file("cross_fund_allocation", email), {"policy": {}, "runs": []}),
        "orchestration": _read_json(_artifact_file("multi_fund_orchestration", email), {"policy": {}, "runs": []}),
        "brain": _read_json(_artifact_file("portfolio_intelligence_brain", email), {"policy": {}, "runs": []}),
        "selection": _read_json(_artifact_file("strategy_selection_ai", email), {"policy": {}, "runs": []}),
        "regime": _read_json(_artifact_file("regime_detection_engine", email), {"policy": {}, "runs": []}),
        "governance": _read_json(_artifact_file("execution_governance_command", email), {"policy": {}, "runs": []}),
        "committee": _read_json(_artifact_file("capital_committee_oversight_mesh", email), {"policy": {}, "runs": []}),
        "compliance": _read_json(_artifact_file("institutional_compliance_layer", email), {"policy": {}, "runs": []}),
        "treasury": _read_json(_artifact_file("sovereign_treasury_command", email), {"policy": {}, "runs": []}),
        "mobility": _read_json(_artifact_file("capital_mobility_control_plane", email), {"policy": {}, "runs": []}),
        "execution": _read_json(_artifact_file("strategy_execution_engine", email), {"strategy_allocations": [], "trades": [], "history": []}),
        "pnl": _read_json(_artifact_file("investor_pnl_ledger", email), {"positions": [], "ledger": []}),
        "ledger": _read_json(_artifact_file("investor_capital_ledger", email), {"accounts": [], "entries": [], "allocations": []}),
    }

def _region_buckets():
    return [
        {"region_id": "NA", "region_name": "North America", "base_weight": 0.34},
        {"region_id": "LATAM", "region_name": "Latin America", "base_weight": 0.16},
        {"region_id": "EU", "region_name": "Europe", "base_weight": 0.22},
        {"region_id": "MENA", "region_name": "Middle East & Africa", "base_weight": 0.12},
        {"region_id": "APAC", "region_name": "Asia Pacific", "base_weight": 0.16},
    ]

def _rows(inputs: dict, policy: dict) -> list[dict]:
    xfa_run = _latest_run(inputs["cross_fund"])
    orch_run = _latest_run(inputs["orchestration"])
    brain_run = _latest_run(inputs["brain"])
    selection_run = _latest_run(inputs["selection"])
    regime_run = _latest_run(inputs["regime"])
    governance_run = _latest_run(inputs["governance"])
    committee_run = _latest_run(inputs["committee"])
    compliance_run = _latest_run(inputs["compliance"])
    treasury_run = _latest_run(inputs["treasury"])
    mobility_run = _latest_run(inputs["mobility"])

    allocations = inputs["execution"].get("strategy_allocations") or []
    positions = inputs["pnl"].get("positions") or []
    ledger_allocs = inputs["ledger"].get("allocations") or []

    total_capital = sum(float(a.get("allocated_amount") or a.get("allocation_amount") or a.get("capital") or 0.0) for a in allocations)
    total_mv = sum(float(p.get("market_value") or p.get("notional") or p.get("value") or 0.0) for p in positions)
    ledger_capital = sum(float(a.get("amount") or a.get("capital") or a.get("allocated_amount") or 0.0) for a in ledger_allocs)
    governed_capital = max(total_capital, total_mv, ledger_capital)

    pnl_ledger = inputs["pnl"].get("ledger") or []
    realized = sum(float(x.get("realized_pnl") or x.get("pnl") or 0.0) for x in pnl_ledger)
    unrealized = sum(float(p.get("unrealized_pnl") or 0.0) for p in positions)
    pnl_total = realized + unrealized
    drawdown_pct = abs(min(pnl_total, 0.0)) / max(governed_capital, 1.0) * 100.0

    xfa_score = float(xfa_run.get("allocation_score") or 0.0)
    orch_score = float(orch_run.get("orchestration_score") or 0.0)
    brain_score = float(brain_run.get("brain_score") or 0.0)
    selection_score = float(selection_run.get("selection_score") or 0.0)
    regime_score = float(regime_run.get("regime_score") or 0.0)
    governance_score = float(governance_run.get("governance_score") or governance_run.get("supervisory_score") or 0.0)
    compliance_score = float(compliance_run.get("release_score") or compliance_run.get("compliance_score") or 0.0)
    treasury_score = float(treasury_run.get("treasury_score") or treasury_run.get("readiness_score") or 0.0)
    mobility_score = float(mobility_run.get("mobility_score") or mobility_run.get("readiness_score") or 0.0)

    exception_pressure = min(
        float(xfa_run.get("escalate_count") or 0.0) * 5.0 +
        float(orch_run.get("escalate_count") or 0.0) * 4.0 +
        float(committee_run.get("escalate_count") or committee_run.get("review_count") or 0.0) * 2.0,
        30.0
    )

    rows = []
    for region in _region_buckets():
        weight = float(region.get("base_weight") or 0.0)
        routed_capital = governed_capital * weight
        region_load_pct = weight * 100.0

        break_pressure = 0.0
        if region_load_pct > policy["maximum_region_load_pct"]:
            break_pressure += min(6.0, (region_load_pct - policy["maximum_region_load_pct"]) * 0.25)
        if drawdown_pct > policy["maximum_drawdown_pct"]:
            break_pressure += min(6.0, (drawdown_pct - policy["maximum_drawdown_pct"]) * 0.35)
        if xfa_score < policy["minimum_allocation_score"]:
            break_pressure += min(5.0, (policy["minimum_allocation_score"] - xfa_score) * 0.30)
        if orch_score < policy["minimum_orchestration_score"]:
            break_pressure += min(5.0, (policy["minimum_orchestration_score"] - orch_score) * 0.30)
        if brain_score < policy["minimum_brain_score"]:
            break_pressure += min(5.0, (policy["minimum_brain_score"] - brain_score) * 0.30)

        routing_raw = (
            xfa_score * 0.20 +
            orch_score * 0.16 +
            brain_score * 0.14 +
            selection_score * 0.10 +
            regime_score * 0.10 +
            governance_score * 0.10 +
            compliance_score * 0.08 +
            treasury_score * 0.06 +
            mobility_score * 0.06
        )
        routing_score = max(0.0, min(100.0, routing_raw - exception_pressure - break_pressure))

        rows.append({
            "region_id": region.get("region_id"),
            "region_name": region.get("region_name"),
            "routed_capital_millions": _round_money(routed_capital / 1_000_000.0),
            "region_load_pct": _round_pct(region_load_pct),
            "allocation_score": _round_pct(xfa_score),
            "orchestration_score": _round_pct(orch_score),
            "brain_score": _round_pct(brain_score),
            "selection_score": _round_pct(selection_score),
            "regime_score": _round_pct(regime_score),
            "governance_score": _round_pct(governance_score),
            "compliance_score": _round_pct(compliance_score),
            "treasury_score": _round_pct(treasury_score),
            "mobility_score": _round_pct(mobility_score),
            "drawdown_pct": _round_pct(drawdown_pct),
            "exception_pressure": _round_pct(exception_pressure),
            "break_pressure": _round_pct(break_pressure),
            "routing_score": _round_pct(routing_score),
        })
    return rows

def _decisions(rows: list[dict], policy: dict) -> list[dict]:
    decisions = []
    for row in rows:
        score = float(row.get("routing_score") or 0.0)
        region_load_pct = float(row.get("region_load_pct") or 0.0)
        exception_pressure = float(row.get("exception_pressure") or 0.0)
        break_pressure = float(row.get("break_pressure") or 0.0)

        action = "ROUTE"
        reasons = []

        if score < policy["minimum_routing_score"]:
            action = "REBALANCE"
            reasons.append("routing score below threshold")
        if region_load_pct > policy["maximum_region_load_pct"] and action in {"ROUTE", "REBALANCE"}:
            action = "REDISTRIBUTE"
            reasons.append("regional load exceeds routing tolerance")
        if exception_pressure > policy["maximum_exception_pressure"]:
            action = "HOLD"
            reasons.append("exception pressure above threshold")
        if break_pressure > policy["maximum_break_pressure"]:
            action = "ESCALATE"
            reasons.append("break pressure above threshold")
        if not reasons:
            reasons.append("global routing posture inside governed band")

        confidence = max(0.5, min(0.99, 0.99 - (exception_pressure + break_pressure) / 200.0))
        decisions.append({
            "region_id": row.get("region_id"),
            "action": action,
            "confidence": _round_pct(confidence),
            "reason": "; ".join(reasons),
            "routed_capital_millions": row.get("routed_capital_millions"),
            "routing_score": row.get("routing_score"),
        })
    return decisions

def _overview(rows: list[dict], decisions: list[dict]) -> dict:
    if not rows:
        return {
            "global_routing_posture": "EMPTY",
            "routing_score": 0.0,
            "route_count": 0,
            "rebalance_count": 0,
            "redistribute_count": 0,
            "hold_count": 0,
            "escalate_count": 0,
            "routed_capital_millions": 0.0,
            "region_count": 0,
        }
    score = sum(float(r.get("routing_score") or 0.0) for r in rows) / len(rows)
    cap = sum(float(r.get("routed_capital_millions") or 0.0) for r in rows)
    counts = {"ROUTE": 0, "REBALANCE": 0, "REDISTRIBUTE": 0, "HOLD": 0, "ESCALATE": 0}
    for d in decisions:
        counts[d.get("action")] = counts.get(d.get("action"), 0) + 1
    posture = "ROUTING"
    if counts["ESCALATE"] > 0:
        posture = "ESCALATED"
    elif counts["HOLD"] > 0:
        posture = "CONSTRAINED"
    elif counts["REDISTRIBUTE"] > 0:
        posture = "REDISTRIBUTING"
    elif counts["REBALANCE"] > 0:
        posture = "REBALANCING"
    return {
        "global_routing_posture": posture,
        "routing_score": _round_pct(score),
        "route_count": counts["ROUTE"],
        "rebalance_count": counts["REBALANCE"],
        "redistribute_count": counts["REDISTRIBUTE"],
        "hold_count": counts["HOLD"],
        "escalate_count": counts["ESCALATE"],
        "routed_capital_millions": _round_money(cap),
        "region_count": len(rows),
    }

def _agenda(decisions: list[dict]) -> list[dict]:
    agenda = []
    for idx, d in enumerate(decisions, start=1):
        agenda.append({
            "sequence": idx,
            "region_id": d.get("region_id"),
            "action": d.get("action"),
            "reason": d.get("reason"),
            "routed_capital_millions": d.get("routed_capital_millions"),
        })
    return agenda

def _build_summary(email: str):
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    inputs = _artifact_inputs(email)
    book = _rows(inputs, policy)
    decisions = _decisions(book, policy)
    overview = _overview(book, decisions)
    return {
        "mission": "QNT30691",
        "generated_at": _now_iso(),
        "policy": policy,
        "global_routing_overview": overview,
        "global_routing_book": book,
        "global_routing_decisions": decisions,
        "global_routing_dependencies": {
            "cross_fund_latest_run": _latest_run(inputs["cross_fund"]),
            "orchestration_latest_run": _latest_run(inputs["orchestration"]),
            "brain_latest_run": _latest_run(inputs["brain"]),
            "selection_latest_run": _latest_run(inputs["selection"]),
            "regime_latest_run": _latest_run(inputs["regime"]),
            "governance_latest_run": _latest_run(inputs["governance"]),
            "committee_latest_run": _latest_run(inputs["committee"]),
            "compliance_latest_run": _latest_run(inputs["compliance"]),
            "treasury_latest_run": _latest_run(inputs["treasury"]),
            "mobility_latest_run": _latest_run(inputs["mobility"]),
        },
        "global_routing_agenda": _agenda(decisions),
    }

@router.get("/api/global-capital-routing/summary")
def global_capital_routing_summary():
    session = _require_user()
    return _build_summary(session.get("email"))

@router.post("/api/global-capital-routing/run")
def global_capital_routing_run(payload: dict = Body(default=None)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    summary = _build_summary(email)
    overview = summary.get("global_routing_overview") or {}
    run = {
        "run_id": f"gcr_{time.time_ns()}",
        "mission": "QNT30691",
        "trigger": (payload or {}).get("trigger") or "manual",
        "timestamp": _now_ts(),
        "generated_at": summary.get("generated_at"),
        "global_routing_posture": overview.get("global_routing_posture"),
        "routing_score": overview.get("routing_score"),
        "route_count": overview.get("route_count"),
        "rebalance_count": overview.get("rebalance_count"),
        "redistribute_count": overview.get("redistribute_count"),
        "hold_count": overview.get("hold_count"),
        "escalate_count": overview.get("escalate_count"),
        "routed_capital_millions": overview.get("routed_capital_millions"),
        "region_count": overview.get("region_count"),
    }
    store.setdefault("runs", []).insert(0, run)
    store["runs"] = store.get("runs", [])[:120]
    _save(email, store)
    return {"status": "ok", "summary": summary, "run": run}

@router.get("/api/global-capital-routing/audit")
def global_capital_routing_audit():
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    runs = store.get("runs") or []
    return {
        "mission": "QNT30691",
        "run_count": len(runs),
        "latest_run": runs[0] if runs else None,
        "runs": runs[:20],
        "policy": store.get("policy") or dict(DEFAULT_POLICY),
    }

@router.post("/api/global-capital-routing/policy")
def global_capital_routing_policy(payload: dict = Body(...)):
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
