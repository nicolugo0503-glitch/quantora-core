from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["multi-fund-orchestration"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ORCH_DIR = ARTIFACTS_DIR / "multi_fund_orchestration"

DEFAULT_POLICY = {
    "minimum_orchestration_score": 84.0,
    "minimum_brain_score": 78.0,
    "minimum_selection_score": 78.0,
    "minimum_regime_score": 78.0,
    "minimum_governance_score": 78.0,
    "minimum_compliance_score": 78.0,
    "maximum_concentration_pct": 45.0,
    "maximum_drawdown_pct": 14.0,
    "maximum_exception_pressure": 22.0,
    "maximum_break_pressure": 18.0,
    "maximum_fund_load_pct": 55.0,
}

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _artifact_file(folder: str, email: str) -> Path:
    return ARTIFACTS_DIR / folder / f"{_safe(email)}.json"

def _path(email: str) -> Path:
    ORCH_DIR.mkdir(parents=True, exist_ok=True)
    return ORCH_DIR / f"{_safe(email)}.json"

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
        "brain": _read_json(_artifact_file("portfolio_intelligence_brain", email), {"policy": {}, "runs": []}),
        "selection": _read_json(_artifact_file("strategy_selection_ai", email), {"policy": {}, "runs": []}),
        "regime": _read_json(_artifact_file("regime_detection_engine", email), {"policy": {}, "runs": []}),
        "deployment": _read_json(_artifact_file("idle_capital_deployment", email), {"policy": {}, "runs": []}),
        "reallocation": _read_json(_artifact_file("strategy_reallocation_intelligence", email), {"policy": {}, "runs": []}),
        "governance": _read_json(_artifact_file("execution_governance_command", email), {"policy": {}, "runs": []}),
        "committee": _read_json(_artifact_file("capital_committee_oversight_mesh", email), {"policy": {}, "runs": []}),
        "compliance": _read_json(_artifact_file("institutional_compliance_layer", email), {"policy": {}, "runs": []}),
        "execution": _read_json(_artifact_file("strategy_execution_engine", email), {"strategy_allocations": [], "trades": [], "history": []}),
        "pnl": _read_json(_artifact_file("investor_pnl_ledger", email), {"positions": [], "ledger": []}),
        "ledger": _read_json(_artifact_file("investor_capital_ledger", email), {"accounts": [], "entries": [], "allocations": []}),
        "multi_fund": _read_json(_artifact_file("multi_fund_architecture", email), {"policy": {}, "runs": []}),
    }

def _rows(inputs: dict, policy: dict) -> list[dict]:
    brain_run = _latest_run(inputs["brain"])
    selection_run = _latest_run(inputs["selection"])
    regime_run = _latest_run(inputs["regime"])
    deployment_run = _latest_run(inputs["deployment"])
    reallocation_run = _latest_run(inputs["reallocation"])
    governance_run = _latest_run(inputs["governance"])
    committee_run = _latest_run(inputs["committee"])
    compliance_run = _latest_run(inputs["compliance"])
    multi_fund_run = _latest_run(inputs["multi_fund"])

    allocations = inputs["execution"].get("strategy_allocations") or []
    positions = inputs["pnl"].get("positions") or []
    ledger_allocs = inputs["ledger"].get("allocations") or []

    total_capital = sum(float(a.get("allocated_amount") or a.get("allocation_amount") or a.get("capital") or 0.0) for a in allocations)
    total_mv = sum(float(p.get("market_value") or p.get("notional") or p.get("value") or 0.0) for p in positions)
    ledger_capital = sum(float(a.get("amount") or a.get("capital") or a.get("allocated_amount") or 0.0) for a in ledger_allocs)
    governed_capital = max(total_capital, total_mv, ledger_capital)

    fund_buckets = {
        "master_fund": 0.45,
        "alpha_fund": 0.25,
        "income_fund": 0.18,
        "opportunity_fund": 0.12,
    }
    if multi_fund_run:
        # slight boost to multi-fund readiness if previous architecture exists
        fund_buckets["master_fund"] = 0.40
        fund_buckets["alpha_fund"] = 0.28
        fund_buckets["income_fund"] = 0.18
        fund_buckets["opportunity_fund"] = 0.14

    fund_rows = []
    brain_score = float(brain_run.get("brain_score") or 0.0)
    selection_score = float(selection_run.get("selection_score") or 0.0)
    regime_score = float(regime_run.get("regime_score") or 0.0)
    deployment_score = float(deployment_run.get("deployment_score") or 0.0)
    reallocation_score = float(reallocation_run.get("reallocation_score") or 0.0)
    governance_score = float(governance_run.get("governance_score") or governance_run.get("supervisory_score") or 0.0)
    compliance_score = float(compliance_run.get("release_score") or compliance_run.get("compliance_score") or 0.0)

    exposures = [abs(float(p.get("market_value") or p.get("notional") or p.get("value") or 0.0)) for p in positions]
    volatility_pct = 0.0
    if exposures:
        avg_exp = sum(exposures) / max(len(exposures), 1)
        if avg_exp > 0:
            dispersion = sum(abs(x - avg_exp) for x in exposures) / max(len(exposures), 1)
            volatility_pct = min(100.0, (dispersion / avg_exp) * 100.0)

    alloc_values = [float(a.get("allocated_amount") or a.get("allocation_amount") or a.get("capital") or 0.0) for a in allocations if float(a.get("allocated_amount") or a.get("allocation_amount") or a.get("capital") or 0.0) > 0]
    concentration_pct = 0.0
    if alloc_values and governed_capital > 0:
        concentration_pct = max(alloc_values) / governed_capital * 100.0

    drawdown_pct = 0.0
    pnl_ledger = inputs["pnl"].get("ledger") or []
    realized = sum(float(x.get("realized_pnl") or x.get("pnl") or 0.0) for x in pnl_ledger)
    unrealized = sum(float(p.get("unrealized_pnl") or 0.0) for p in positions)
    pnl_total = realized + unrealized
    drawdown_pct = abs(min(pnl_total, 0.0)) / max(governed_capital, 1.0) * 100.0

    exception_pressure = min(
        float(brain_run.get("escalate_count") or 0.0) * 5.0 +
        float(selection_run.get("escalate_count") or 0.0) * 4.0 +
        float(committee_run.get("escalate_count") or committee_run.get("review_count") or 0.0) * 2.0,
        30.0
    )

    common_break_pressure = 0.0
    if concentration_pct > policy["maximum_concentration_pct"]:
        common_break_pressure += min(6.0, (concentration_pct - policy["maximum_concentration_pct"]) * 0.25)
    if drawdown_pct > policy["maximum_drawdown_pct"]:
        common_break_pressure += min(6.0, (drawdown_pct - policy["maximum_drawdown_pct"]) * 0.35)
    if volatility_pct > 35.0:
        common_break_pressure += min(6.0, (volatility_pct - 35.0) * 0.20)

    for fund_name, weight in fund_buckets.items():
        allocated_capital = governed_capital * weight
        fund_load_pct = weight * 100.0
        break_pressure = common_break_pressure
        if fund_load_pct > policy["maximum_fund_load_pct"]:
            break_pressure += min(6.0, (fund_load_pct - policy["maximum_fund_load_pct"]) * 0.25)

        orchestration_raw = (
            brain_score * 0.26 +
            selection_score * 0.18 +
            regime_score * 0.14 +
            deployment_score * 0.12 +
            reallocation_score * 0.10 +
            governance_score * 0.10 +
            compliance_score * 0.10
        )
        orchestration_score = max(0.0, min(100.0, orchestration_raw - exception_pressure - break_pressure))

        fund_rows.append({
            "fund_id": fund_name.upper(),
            "fund_name": fund_name,
            "allocated_capital_millions": _round_money(allocated_capital / 1_000_000.0),
            "fund_load_pct": _round_pct(fund_load_pct),
            "brain_score": _round_pct(brain_score),
            "selection_score": _round_pct(selection_score),
            "regime_score": _round_pct(regime_score),
            "deployment_score": _round_pct(deployment_score),
            "reallocation_score": _round_pct(reallocation_score),
            "governance_score": _round_pct(governance_score),
            "compliance_score": _round_pct(compliance_score),
            "concentration_pct": _round_pct(concentration_pct),
            "drawdown_pct": _round_pct(drawdown_pct),
            "volatility_pct": _round_pct(volatility_pct),
            "exception_pressure": _round_pct(exception_pressure),
            "break_pressure": _round_pct(break_pressure),
            "orchestration_score": _round_pct(orchestration_score),
        })
    return fund_rows

def _decisions(rows: list[dict], policy: dict) -> list[dict]:
    decisions = []
    for row in rows:
        score = float(row.get("orchestration_score") or 0.0)
        load_pct = float(row.get("fund_load_pct") or 0.0)
        exception_pressure = float(row.get("exception_pressure") or 0.0)
        break_pressure = float(row.get("break_pressure") or 0.0)

        action = "ORCHESTRATE"
        reasons = []

        if score < policy["minimum_orchestration_score"]:
            action = "REBALANCE"
            reasons.append("orchestration score below threshold")
        if load_pct > policy["maximum_fund_load_pct"] and action in {"ORCHESTRATE", "REBALANCE"}:
            action = "REDISTRIBUTE"
            reasons.append("fund load exceeds governance tolerance")
        if exception_pressure > policy["maximum_exception_pressure"]:
            action = "HOLD"
            reasons.append("exception pressure above threshold")
        if break_pressure > policy["maximum_break_pressure"]:
            action = "ESCALATE"
            reasons.append("break pressure above threshold")
        if not reasons:
            reasons.append("multi-fund posture inside governed band")

        confidence = max(0.5, min(0.99, 0.99 - (exception_pressure + break_pressure) / 200.0))
        decisions.append({
            "fund_id": row.get("fund_id"),
            "action": action,
            "confidence": _round_pct(confidence),
            "reason": "; ".join(reasons),
            "allocated_capital_millions": row.get("allocated_capital_millions"),
            "orchestration_score": row.get("orchestration_score"),
        })
    return decisions

def _overview(rows: list[dict], decisions: list[dict]) -> dict:
    if not rows:
        return {
            "multi_fund_posture": "EMPTY",
            "orchestration_score": 0.0,
            "orchestrate_count": 0,
            "rebalance_count": 0,
            "redistribute_count": 0,
            "hold_count": 0,
            "escalate_count": 0,
            "governed_capital_millions": 0.0,
            "fund_count": 0,
        }
    score = sum(float(r.get("orchestration_score") or 0.0) for r in rows) / len(rows)
    cap = sum(float(r.get("allocated_capital_millions") or 0.0) for r in rows)
    counts = {"ORCHESTRATE": 0, "REBALANCE": 0, "REDISTRIBUTE": 0, "HOLD": 0, "ESCALATE": 0}
    for d in decisions:
        counts[d.get("action")] = counts.get(d.get("action"), 0) + 1
    posture = "ORCHESTRATING"
    if counts["ESCALATE"] > 0:
        posture = "ESCALATED"
    elif counts["HOLD"] > 0:
        posture = "CONSTRAINED"
    elif counts["REDISTRIBUTE"] > 0:
        posture = "REDISTRIBUTING"
    elif counts["REBALANCE"] > 0:
        posture = "REBALANCING"
    return {
        "multi_fund_posture": posture,
        "orchestration_score": _round_pct(score),
        "orchestrate_count": counts["ORCHESTRATE"],
        "rebalance_count": counts["REBALANCE"],
        "redistribute_count": counts["REDISTRIBUTE"],
        "hold_count": counts["HOLD"],
        "escalate_count": counts["ESCALATE"],
        "governed_capital_millions": _round_money(cap),
        "fund_count": len(rows),
    }

def _agenda(decisions: list[dict]) -> list[dict]:
    agenda = []
    for idx, d in enumerate(decisions, start=1):
        agenda.append({
            "sequence": idx,
            "fund_id": d.get("fund_id"),
            "action": d.get("action"),
            "reason": d.get("reason"),
            "allocated_capital_millions": d.get("allocated_capital_millions"),
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
        "mission": "QNT30689",
        "generated_at": _now_iso(),
        "policy": policy,
        "multi_fund_orchestration_overview": overview,
        "multi_fund_book": book,
        "multi_fund_decisions": decisions,
        "multi_fund_dependencies": {
            "brain_latest_run": _latest_run(inputs["brain"]),
            "selection_latest_run": _latest_run(inputs["selection"]),
            "regime_latest_run": _latest_run(inputs["regime"]),
            "deployment_latest_run": _latest_run(inputs["deployment"]),
            "reallocation_latest_run": _latest_run(inputs["reallocation"]),
            "governance_latest_run": _latest_run(inputs["governance"]),
            "committee_latest_run": _latest_run(inputs["committee"]),
            "compliance_latest_run": _latest_run(inputs["compliance"]),
            "architecture_latest_run": _latest_run(inputs["multi_fund"]),
        },
        "multi_fund_agenda": _agenda(decisions),
    }

@router.get("/api/multi-fund-orchestration/summary")
def multi_fund_orchestration_summary():
    session = _require_user()
    return _build_summary(session.get("email"))

@router.post("/api/multi-fund-orchestration/run")
def multi_fund_orchestration_run(payload: dict = Body(default=None)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    summary = _build_summary(email)
    overview = summary.get("multi_fund_orchestration_overview") or {}
    run = {
        "run_id": f"mfo_{time.time_ns()}",
        "mission": "QNT30689",
        "trigger": (payload or {}).get("trigger") or "manual",
        "timestamp": _now_ts(),
        "generated_at": summary.get("generated_at"),
        "multi_fund_posture": overview.get("multi_fund_posture"),
        "orchestration_score": overview.get("orchestration_score"),
        "orchestrate_count": overview.get("orchestrate_count"),
        "rebalance_count": overview.get("rebalance_count"),
        "redistribute_count": overview.get("redistribute_count"),
        "hold_count": overview.get("hold_count"),
        "escalate_count": overview.get("escalate_count"),
        "governed_capital_millions": overview.get("governed_capital_millions"),
        "fund_count": overview.get("fund_count"),
    }
    store.setdefault("runs", []).insert(0, run)
    store["runs"] = store.get("runs", [])[:120]
    _save(email, store)
    return {"status": "ok", "summary": summary, "run": run}

@router.get("/api/multi-fund-orchestration/audit")
def multi_fund_orchestration_audit():
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    runs = store.get("runs") or []
    return {
        "mission": "QNT30689",
        "run_count": len(runs),
        "latest_run": runs[0] if runs else None,
        "runs": runs[:20],
        "policy": store.get("policy") or dict(DEFAULT_POLICY),
    }

@router.post("/api/multi-fund-orchestration/policy")
def multi_fund_orchestration_policy(payload: dict = Body(...)):
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
