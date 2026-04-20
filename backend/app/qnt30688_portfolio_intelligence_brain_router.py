from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["portfolio-intelligence-brain"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
BRAIN_DIR = ARTIFACTS_DIR / "portfolio_intelligence_brain"

DEFAULT_POLICY = {
    "minimum_brain_score": 84.0,
    "minimum_selection_score": 78.0,
    "minimum_regime_score": 78.0,
    "minimum_deployment_score": 78.0,
    "minimum_reallocation_score": 76.0,
    "minimum_rotation_score": 76.0,
    "minimum_governance_score": 78.0,
    "minimum_compliance_score": 78.0,
    "maximum_drawdown_pct": 14.0,
    "maximum_volatility_pct": 35.0,
    "maximum_concentration_pct": 45.0,
    "maximum_exception_pressure": 22.0,
    "maximum_break_pressure": 18.0,
}

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _artifact_file(folder: str, email: str) -> Path:
    return ARTIFACTS_DIR / folder / f"{_safe(email)}.json"

def _path(email: str) -> Path:
    BRAIN_DIR.mkdir(parents=True, exist_ok=True)
    return BRAIN_DIR / f"{_safe(email)}.json"

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
        "selection": _read_json(_artifact_file("strategy_selection_ai", email), {"policy": {}, "runs": []}),
        "regime": _read_json(_artifact_file("regime_detection_engine", email), {"policy": {}, "runs": []}),
        "deployment": _read_json(_artifact_file("idle_capital_deployment", email), {"policy": {}, "runs": []}),
        "reallocation": _read_json(_artifact_file("strategy_reallocation_intelligence", email), {"policy": {}, "runs": []}),
        "rotation": _read_json(_artifact_file("capital_rotation_engine", email), {"policy": {}, "runs": []}),
        "defense": _read_json(_artifact_file("drawdown_defense_system", email), {"policy": {}, "runs": []}),
        "governance": _read_json(_artifact_file("execution_governance_command", email), {"policy": {}, "runs": []}),
        "committee": _read_json(_artifact_file("capital_committee_oversight_mesh", email), {"policy": {}, "runs": []}),
        "compliance": _read_json(_artifact_file("institutional_compliance_layer", email), {"policy": {}, "runs": []}),
        "execution": _read_json(_artifact_file("strategy_execution_engine", email), {"strategy_allocations": [], "trades": [], "history": []}),
        "pnl": _read_json(_artifact_file("investor_pnl_ledger", email), {"positions": [], "ledger": []}),
        "ledger": _read_json(_artifact_file("investor_capital_ledger", email), {"accounts": [], "entries": [], "allocations": []}),
    }

def _rows(inputs: dict, policy: dict) -> list[dict]:
    selection_run = _latest_run(inputs["selection"])
    regime_run = _latest_run(inputs["regime"])
    deployment_run = _latest_run(inputs["deployment"])
    realloc_run = _latest_run(inputs["reallocation"])
    rotation_run = _latest_run(inputs["rotation"])
    defense_run = _latest_run(inputs["defense"])
    governance_run = _latest_run(inputs["governance"])
    committee_run = _latest_run(inputs["committee"])
    compliance_run = _latest_run(inputs["compliance"])

    allocations = inputs["execution"].get("strategy_allocations") or []
    trades = inputs["execution"].get("trades") or []
    positions = inputs["pnl"].get("positions") or []
    pnl_ledger = inputs["pnl"].get("ledger") or []
    ledger_allocs = inputs["ledger"].get("allocations") or []

    total_capital = sum(float(a.get("allocated_amount") or a.get("allocation_amount") or a.get("capital") or 0.0) for a in allocations)
    total_mv = sum(float(p.get("market_value") or p.get("notional") or p.get("value") or 0.0) for p in positions)
    ledger_capital = sum(float(a.get("amount") or a.get("capital") or a.get("allocated_amount") or 0.0) for a in ledger_allocs)
    governed_capital = max(total_capital, total_mv, ledger_capital)

    realized = sum(float(x.get("realized_pnl") or x.get("pnl") or 0.0) for x in pnl_ledger)
    unrealized = sum(float(p.get("unrealized_pnl") or 0.0) for p in positions)
    pnl_total = realized + unrealized

    drawdown_pct = abs(min(pnl_total, 0.0)) / max(governed_capital, 1.0) * 100.0

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

    selection_score = float(selection_run.get("selection_score") or 0.0)
    regime_score = float(regime_run.get("regime_score") or 0.0)
    deployment_score = float(deployment_run.get("deployment_score") or 0.0)
    reallocation_score = float(realloc_run.get("reallocation_score") or 0.0)
    rotation_score = float(rotation_run.get("rotation_score") or 0.0)
    defense_score = float(defense_run.get("defense_score") or 0.0)
    governance_score = float(governance_run.get("governance_score") or governance_run.get("supervisory_score") or 0.0)
    compliance_score = float(compliance_run.get("release_score") or compliance_run.get("compliance_score") or 0.0)

    strategy_breadth_score = min(100.0, len(allocations) * 18.0)
    execution_density_score = min(100.0, len(trades) * 8.0)
    capital_efficiency_score = max(0.0, min(100.0, 100.0 - min(drawdown_pct * 2.2, 35.0)))

    exception_pressure = 0.0
    exception_pressure += float(selection_run.get("escalate_count") or 0.0) * 5.0
    exception_pressure += float(regime_run.get("escalate_count") or 0.0) * 4.0
    exception_pressure += float(committee_run.get("escalate_count") or committee_run.get("review_count") or 0.0) * 2.0
    exception_pressure = min(exception_pressure, 30.0)

    break_pressure = 0.0
    if drawdown_pct > policy["maximum_drawdown_pct"]:
        break_pressure += min(7.0, (drawdown_pct - policy["maximum_drawdown_pct"]) * 0.40)
    if volatility_pct > policy["maximum_volatility_pct"]:
        break_pressure += min(6.0, (volatility_pct - policy["maximum_volatility_pct"]) * 0.25)
    if concentration_pct > policy["maximum_concentration_pct"]:
        break_pressure += min(6.0, (concentration_pct - policy["maximum_concentration_pct"]) * 0.25)
    if selection_score < policy["minimum_selection_score"]:
        break_pressure += min(5.0, (policy["minimum_selection_score"] - selection_score) * 0.30)
    if regime_score < policy["minimum_regime_score"]:
        break_pressure += min(5.0, (policy["minimum_regime_score"] - regime_score) * 0.30)
    if deployment_score < policy["minimum_deployment_score"]:
        break_pressure += min(5.0, (policy["minimum_deployment_score"] - deployment_score) * 0.30)

    brain_raw = (
        selection_score * 0.20 +
        regime_score * 0.16 +
        deployment_score * 0.14 +
        reallocation_score * 0.12 +
        rotation_score * 0.08 +
        defense_score * 0.08 +
        governance_score * 0.08 +
        compliance_score * 0.06 +
        strategy_breadth_score * 0.04 +
        execution_density_score * 0.02 +
        capital_efficiency_score * 0.02
    )
    brain_score = max(0.0, min(100.0, brain_raw - exception_pressure - break_pressure))

    brain_posture = "ORCHESTRATE"
    if selection_run.get("selection_posture") == "SCALING":
        brain_posture = "SCALE"
    elif selection_run.get("selection_posture") == "DEFENSIVE":
        brain_posture = "DEFEND"
    elif regime_run.get("regime_posture") == "EXPANSION":
        brain_posture = "DEPLOY"
    elif regime_run.get("regime_posture") == "CONSTRAINED":
        brain_posture = "HOLD"

    return [{
        "portfolio_id": "PORTFOLIO_INTELLIGENCE_BOOK",
        "governed_capital_millions": _round_money(governed_capital / 1_000_000.0),
        "active_allocations": len(allocations),
        "active_positions": len([p for p in positions if float(p.get("market_value") or p.get("notional") or p.get("value") or 0.0) != 0.0]),
        "trade_count": len(trades),
        "pnl_total": _round_money(pnl_total),
        "drawdown_pct": _round_pct(drawdown_pct),
        "volatility_pct": _round_pct(volatility_pct),
        "concentration_pct": _round_pct(concentration_pct),
        "strategy_breadth_score": _round_pct(strategy_breadth_score),
        "execution_density_score": _round_pct(execution_density_score),
        "capital_efficiency_score": _round_pct(capital_efficiency_score),
        "selection_score": _round_pct(selection_score),
        "regime_score": _round_pct(regime_score),
        "deployment_score": _round_pct(deployment_score),
        "reallocation_score": _round_pct(reallocation_score),
        "rotation_score": _round_pct(rotation_score),
        "defense_score": _round_pct(defense_score),
        "governance_score": _round_pct(governance_score),
        "compliance_score": _round_pct(compliance_score),
        "exception_pressure": _round_pct(exception_pressure),
        "break_pressure": _round_pct(break_pressure),
        "brain_score": _round_pct(brain_score),
        "brain_posture": brain_posture,
        "latest_selection_action": selection_run.get("selection_posture") or selection_run.get("action"),
        "latest_regime_action": regime_run.get("regime_posture") or regime_run.get("action"),
    }]

def _decisions(rows: list[dict], policy: dict) -> list[dict]:
    decisions = []
    for row in rows:
        score = float(row.get("brain_score") or 0.0)
        exception_pressure = float(row.get("exception_pressure") or 0.0)
        break_pressure = float(row.get("break_pressure") or 0.0)
        posture = row.get("brain_posture")

        action = "ORCHESTRATE"
        reasons = []

        if posture == "SCALE":
            action = "SCALE"
            reasons.append("selection posture supports scale orchestration")
        elif posture == "DEFEND":
            action = "DEFEND"
            reasons.append("defensive posture supports protection orchestration")
        elif posture == "DEPLOY":
            action = "DEPLOY"
            reasons.append("expansion regime supports deployment orchestration")
        elif posture == "HOLD":
            action = "HOLD"
            reasons.append("constrained regime supports hold orchestration")

        if score < policy["minimum_brain_score"] and action in {"ORCHESTRATE", "SCALE", "DEPLOY"}:
            action = "REVIEW"
            reasons.append("brain score below threshold")
        if exception_pressure > policy["maximum_exception_pressure"]:
            action = "HOLD"
            reasons.append("exception pressure above threshold")
        if break_pressure > policy["maximum_break_pressure"]:
            action = "ESCALATE"
            reasons.append("break pressure above threshold")
        if not reasons:
            reasons.append("portfolio intelligence posture inside governed band")

        confidence = max(0.5, min(0.99, 0.99 - (exception_pressure + break_pressure) / 200.0))
        decisions.append({
            "portfolio_id": row.get("portfolio_id"),
            "action": action,
            "confidence": _round_pct(confidence),
            "reason": "; ".join(reasons),
            "governed_capital_millions": row.get("governed_capital_millions"),
            "brain_score": row.get("brain_score"),
            "brain_posture": row.get("brain_posture"),
        })
    return decisions

def _overview(rows: list[dict], decisions: list[dict]) -> dict:
    if not rows:
        return {
            "brain_overall_posture": "EMPTY",
            "brain_score": 0.0,
            "orchestrate_count": 0,
            "scale_count": 0,
            "deploy_count": 0,
            "defend_count": 0,
            "review_count": 0,
            "hold_count": 0,
            "escalate_count": 0,
            "governed_capital_millions": 0.0,
        }
    score = sum(float(r.get("brain_score") or 0.0) for r in rows) / len(rows)
    cap = sum(float(r.get("governed_capital_millions") or 0.0) for r in rows)
    counts = {"ORCHESTRATE": 0, "SCALE": 0, "DEPLOY": 0, "DEFEND": 0, "REVIEW": 0, "HOLD": 0, "ESCALATE": 0}
    for d in decisions:
        counts[d.get("action")] = counts.get(d.get("action"), 0) + 1
    posture = "ORCHESTRATING"
    if counts["ESCALATE"] > 0:
        posture = "ESCALATED"
    elif counts["HOLD"] > 0:
        posture = "CONSTRAINED"
    elif counts["DEFEND"] > 0:
        posture = "DEFENSIVE"
    elif counts["DEPLOY"] > 0:
        posture = "DEPLOYING"
    elif counts["SCALE"] > 0:
        posture = "SCALING"
    elif counts["REVIEW"] > 0:
        posture = "UNDER_REVIEW"
    return {
        "brain_overall_posture": posture,
        "brain_score": _round_pct(score),
        "orchestrate_count": counts["ORCHESTRATE"],
        "scale_count": counts["SCALE"],
        "deploy_count": counts["DEPLOY"],
        "defend_count": counts["DEFEND"],
        "review_count": counts["REVIEW"],
        "hold_count": counts["HOLD"],
        "escalate_count": counts["ESCALATE"],
        "governed_capital_millions": _round_money(cap),
    }

def _agenda(decisions: list[dict]) -> list[dict]:
    agenda = []
    for idx, d in enumerate(decisions, start=1):
        agenda.append({
            "sequence": idx,
            "portfolio_id": d.get("portfolio_id"),
            "action": d.get("action"),
            "reason": d.get("reason"),
            "brain_posture": d.get("brain_posture"),
            "governed_capital_millions": d.get("governed_capital_millions"),
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
        "mission": "QNT30688",
        "generated_at": _now_iso(),
        "policy": policy,
        "portfolio_intelligence_overview": overview,
        "portfolio_intelligence_book": book,
        "portfolio_intelligence_decisions": decisions,
        "portfolio_intelligence_dependencies": {
            "selection_latest_run": _latest_run(inputs["selection"]),
            "regime_latest_run": _latest_run(inputs["regime"]),
            "deployment_latest_run": _latest_run(inputs["deployment"]),
            "reallocation_latest_run": _latest_run(inputs["reallocation"]),
            "rotation_latest_run": _latest_run(inputs["rotation"]),
            "defense_latest_run": _latest_run(inputs["defense"]),
            "governance_latest_run": _latest_run(inputs["governance"]),
            "committee_latest_run": _latest_run(inputs["committee"]),
            "compliance_latest_run": _latest_run(inputs["compliance"]),
        },
        "portfolio_intelligence_agenda": _agenda(decisions),
    }

@router.get("/api/portfolio-intelligence-brain/summary")
def portfolio_intelligence_brain_summary():
    session = _require_user()
    return _build_summary(session.get("email"))

@router.post("/api/portfolio-intelligence-brain/run")
def portfolio_intelligence_brain_run(payload: dict = Body(default=None)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    summary = _build_summary(email)
    overview = summary.get("portfolio_intelligence_overview") or {}
    run = {
        "run_id": f"pib_{time.time_ns()}",
        "mission": "QNT30688",
        "trigger": (payload or {}).get("trigger") or "manual",
        "timestamp": _now_ts(),
        "generated_at": summary.get("generated_at"),
        "brain_overall_posture": overview.get("brain_overall_posture"),
        "brain_score": overview.get("brain_score"),
        "orchestrate_count": overview.get("orchestrate_count"),
        "scale_count": overview.get("scale_count"),
        "deploy_count": overview.get("deploy_count"),
        "defend_count": overview.get("defend_count"),
        "review_count": overview.get("review_count"),
        "hold_count": overview.get("hold_count"),
        "escalate_count": overview.get("escalate_count"),
        "governed_capital_millions": overview.get("governed_capital_millions"),
    }
    store.setdefault("runs", []).insert(0, run)
    store["runs"] = store.get("runs", [])[:120]
    _save(email, store)
    return {"status": "ok", "summary": summary, "run": run}

@router.get("/api/portfolio-intelligence-brain/audit")
def portfolio_intelligence_brain_audit():
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    runs = store.get("runs") or []
    return {
        "mission": "QNT30688",
        "run_count": len(runs),
        "latest_run": runs[0] if runs else None,
        "runs": runs[:20],
        "policy": store.get("policy") or dict(DEFAULT_POLICY),
    }

@router.post("/api/portfolio-intelligence-brain/policy")
def portfolio_intelligence_brain_policy(payload: dict = Body(...)):
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
