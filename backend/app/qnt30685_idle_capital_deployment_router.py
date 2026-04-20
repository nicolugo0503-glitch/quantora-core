from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["idle-capital-deployment"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
DEPLOY_DIR = ARTIFACTS_DIR / "idle_capital_deployment"

DEFAULT_POLICY = {
    "minimum_deployment_score": 84.0,
    "minimum_reallocation_score": 80.0,
    "minimum_rotation_score": 78.0,
    "minimum_defense_score": 78.0,
    "minimum_restoration_score": 76.0,
    "minimum_continuity_score": 76.0,
    "minimum_governance_score": 78.0,
    "minimum_compliance_score": 78.0,
    "minimum_target_quality_score": 62.0,
    "maximum_idle_ratio_pct": 18.0,
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
        "reallocation": _read_json(_artifact_file("strategy_reallocation_intelligence", email), {"policy": {}, "runs": []}),
        "rotation": _read_json(_artifact_file("capital_rotation_engine", email), {"policy": {}, "runs": []}),
        "defense": _read_json(_artifact_file("drawdown_defense_system", email), {"policy": {}, "runs": []}),
        "restoration": _read_json(_artifact_file("capital_restoration_engine", email), {"policy": {}, "runs": []}),
        "continuity": _read_json(_artifact_file("live_allocation_continuity_command", email), {"policy": {}, "runs": []}),
        "governance": _read_json(_artifact_file("execution_governance_command", email), {"policy": {}, "runs": []}),
        "committee": _read_json(_artifact_file("capital_committee_oversight_mesh", email), {"policy": {}, "runs": []}),
        "compliance": _read_json(_artifact_file("institutional_compliance_layer", email), {"policy": {}, "runs": []}),
        "execution": _read_json(_artifact_file("strategy_execution_engine", email), {"strategy_allocations": [], "trades": [], "history": []}),
        "pnl": _read_json(_artifact_file("investor_pnl_ledger", email), {"positions": [], "ledger": []}),
        "ledger": _read_json(_artifact_file("investor_capital_ledger", email), {"accounts": [], "entries": [], "allocations": []}),
    }

def _rows(inputs: dict, policy: dict) -> list[dict]:
    realloc_run = _latest_run(inputs["reallocation"])
    rotation_run = _latest_run(inputs["rotation"])
    defense_run = _latest_run(inputs["defense"])
    restoration_run = _latest_run(inputs["restoration"])
    continuity_run = _latest_run(inputs["continuity"])
    governance_run = _latest_run(inputs["governance"])
    committee_run = _latest_run(inputs["committee"])
    compliance_run = _latest_run(inputs["compliance"])

    allocations = inputs["execution"].get("strategy_allocations") or []
    positions = inputs["pnl"].get("positions") or []
    ledger_allocs = inputs["ledger"].get("allocations") or []

    total_capital = sum(float(a.get("allocated_amount") or a.get("allocation_amount") or a.get("capital") or 0.0) for a in allocations)
    total_mv = sum(float(p.get("market_value") or p.get("notional") or p.get("value") or 0.0) for p in positions)
    ledger_capital = sum(float(a.get("amount") or a.get("capital") or a.get("allocated_amount") or 0.0) for a in ledger_allocs)
    governed_capital = max(total_capital, total_mv, ledger_capital)

    deployed_capital = total_capital if total_capital > 0 else total_mv
    idle_capital = max(governed_capital - deployed_capital, 0.0)
    idle_ratio_pct = (idle_capital / max(governed_capital, 1.0)) * 100.0

    active_allocations = len(allocations)
    active_positions = len([p for p in positions if float(p.get("market_value") or p.get("notional") or p.get("value") or 0.0) != 0.0])

    reallocation_score = float(realloc_run.get("reallocation_score") or 0.0)
    rotation_score = float(rotation_run.get("rotation_score") or 0.0)
    defense_score = float(defense_run.get("defense_score") or 0.0)
    restoration_score = float(restoration_run.get("restoration_score") or 0.0)
    continuity_score = float(continuity_run.get("continuity_score") or 0.0)
    governance_score = float(governance_run.get("governance_score") or governance_run.get("supervisory_score") or 0.0)
    compliance_score = float(compliance_run.get("release_score") or compliance_run.get("compliance_score") or 0.0)

    target_quality_score = max(0.0, min(100.0,
        reallocation_score * 0.24 +
        rotation_score * 0.18 +
        defense_score * 0.14 +
        restoration_score * 0.12 +
        continuity_score * 0.10 +
        governance_score * 0.12 +
        compliance_score * 0.10
    ))

    exception_pressure = 0.0
    exception_pressure += float(realloc_run.get("escalate_count") or 0.0) * 5.0
    exception_pressure += float(rotation_run.get("escalate_count") or 0.0) * 4.0
    exception_pressure += float(committee_run.get("escalate_count") or committee_run.get("review_count") or 0.0) * 2.0
    exception_pressure = min(exception_pressure, 30.0)

    break_pressure = 0.0
    if idle_ratio_pct > policy["maximum_idle_ratio_pct"]:
        break_pressure += min(8.0, (idle_ratio_pct - policy["maximum_idle_ratio_pct"]) * 0.35)
    if reallocation_score < policy["minimum_reallocation_score"]:
        break_pressure += min(5.0, (policy["minimum_reallocation_score"] - reallocation_score) * 0.30)
    if rotation_score < policy["minimum_rotation_score"]:
        break_pressure += min(5.0, (policy["minimum_rotation_score"] - rotation_score) * 0.30)
    if defense_score < policy["minimum_defense_score"]:
        break_pressure += min(5.0, (policy["minimum_defense_score"] - defense_score) * 0.30)
    if restoration_score < policy["minimum_restoration_score"]:
        break_pressure += min(5.0, (policy["minimum_restoration_score"] - restoration_score) * 0.30)
    if target_quality_score < policy["minimum_target_quality_score"]:
        break_pressure += min(5.0, (policy["minimum_target_quality_score"] - target_quality_score) * 0.20)

    deployment_raw = (
        reallocation_score * 0.24 +
        rotation_score * 0.18 +
        defense_score * 0.12 +
        restoration_score * 0.12 +
        continuity_score * 0.10 +
        governance_score * 0.10 +
        compliance_score * 0.08 +
        max(0.0, 100.0 - min(idle_ratio_pct * 1.8, 30.0)) * 0.06
    )
    deployment_score = max(0.0, min(100.0, deployment_raw - exception_pressure - break_pressure))

    return [{
        "portfolio_id": "IDLE_CAPITAL_DEPLOYMENT_BOOK",
        "governed_capital_millions": _round_money(governed_capital / 1_000_000.0),
        "deployed_capital_millions": _round_money(deployed_capital / 1_000_000.0),
        "idle_capital_millions": _round_money(idle_capital / 1_000_000.0),
        "idle_ratio_pct": _round_pct(idle_ratio_pct),
        "active_allocations": active_allocations,
        "active_positions": active_positions,
        "target_quality_score": _round_pct(target_quality_score),
        "reallocation_score": _round_pct(reallocation_score),
        "rotation_score": _round_pct(rotation_score),
        "defense_score": _round_pct(defense_score),
        "restoration_score": _round_pct(restoration_score),
        "continuity_score": _round_pct(continuity_score),
        "governance_score": _round_pct(governance_score),
        "compliance_score": _round_pct(compliance_score),
        "exception_pressure": _round_pct(exception_pressure),
        "break_pressure": _round_pct(break_pressure),
        "deployment_score": _round_pct(deployment_score),
        "latest_reallocation_action": realloc_run.get("reallocation_posture") or realloc_run.get("action"),
        "latest_rotation_action": rotation_run.get("rotation_posture") or rotation_run.get("action"),
        "latest_defense_action": defense_run.get("defense_posture") or defense_run.get("action"),
    }]

def _decisions(rows: list[dict], policy: dict) -> list[dict]:
    decisions = []
    for row in rows:
        score = float(row.get("deployment_score") or 0.0)
        idle_ratio_pct = float(row.get("idle_ratio_pct") or 0.0)
        target_quality_score = float(row.get("target_quality_score") or 0.0)
        exception_pressure = float(row.get("exception_pressure") or 0.0)
        break_pressure = float(row.get("break_pressure") or 0.0)

        action = "DEPLOY"
        reasons = []

        if score < policy["minimum_deployment_score"]:
            action = "REBALANCE"
            reasons.append("deployment score below threshold")
        if idle_ratio_pct > policy["maximum_idle_ratio_pct"] * 1.3 and action in {"DEPLOY", "REBALANCE"}:
            action = "ACCELERATE"
            reasons.append("idle capital ratio materially above tolerance")
        if target_quality_score < policy["minimum_target_quality_score"] and action in {"DEPLOY", "ACCELERATE"}:
            action = "HOLD"
            reasons.append("target quality below threshold")
        if exception_pressure > policy["maximum_exception_pressure"]:
            action = "HOLD"
            reasons.append("exception pressure above threshold")
        if break_pressure > policy["maximum_break_pressure"]:
            action = "ESCALATE"
            reasons.append("break pressure above threshold")
        if not reasons:
            reasons.append("idle deployment posture inside governed band")

        confidence = max(0.5, min(0.99, 0.99 - (exception_pressure + break_pressure) / 200.0))
        decisions.append({
            "portfolio_id": row.get("portfolio_id"),
            "action": action,
            "confidence": _round_pct(confidence),
            "reason": "; ".join(reasons),
            "idle_capital_millions": row.get("idle_capital_millions"),
            "deployment_score": row.get("deployment_score"),
        })
    return decisions

def _overview(rows: list[dict], decisions: list[dict]) -> dict:
    if not rows:
        return {
            "deployment_posture": "EMPTY",
            "deployment_score": 0.0,
            "deploy_count": 0,
            "accelerate_count": 0,
            "rebalance_count": 0,
            "hold_count": 0,
            "escalate_count": 0,
            "idle_capital_millions": 0.0,
        }
    score = sum(float(r.get("deployment_score") or 0.0) for r in rows) / len(rows)
    idle = sum(float(r.get("idle_capital_millions") or 0.0) for r in rows)
    counts = {"DEPLOY": 0, "ACCELERATE": 0, "REBALANCE": 0, "HOLD": 0, "ESCALATE": 0}
    for d in decisions:
        counts[d.get("action")] = counts.get(d.get("action"), 0) + 1
    posture = "ACTIVE_DEPLOYMENT"
    if counts["ESCALATE"] > 0:
        posture = "ESCALATED"
    elif counts["HOLD"] > 0:
        posture = "CONSTRAINED"
    elif counts["ACCELERATE"] > 0:
        posture = "ACCELERATED"
    elif counts["REBALANCE"] > 0:
        posture = "REBALANCING"
    return {
        "deployment_posture": posture,
        "deployment_score": _round_pct(score),
        "deploy_count": counts["DEPLOY"],
        "accelerate_count": counts["ACCELERATE"],
        "rebalance_count": counts["REBALANCE"],
        "hold_count": counts["HOLD"],
        "escalate_count": counts["ESCALATE"],
        "idle_capital_millions": _round_money(idle),
    }

def _agenda(decisions: list[dict]) -> list[dict]:
    agenda = []
    for idx, d in enumerate(decisions, start=1):
        agenda.append({
            "sequence": idx,
            "portfolio_id": d.get("portfolio_id"),
            "action": d.get("action"),
            "reason": d.get("reason"),
            "idle_capital_millions": d.get("idle_capital_millions"),
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
        "mission": "QNT30685",
        "generated_at": _now_iso(),
        "policy": policy,
        "idle_capital_deployment_overview": overview,
        "deployment_book": book,
        "deployment_decisions": decisions,
        "deployment_dependencies": {
            "reallocation_latest_run": _latest_run(inputs["reallocation"]),
            "rotation_latest_run": _latest_run(inputs["rotation"]),
            "defense_latest_run": _latest_run(inputs["defense"]),
            "restoration_latest_run": _latest_run(inputs["restoration"]),
            "continuity_latest_run": _latest_run(inputs["continuity"]),
            "governance_latest_run": _latest_run(inputs["governance"]),
            "committee_latest_run": _latest_run(inputs["committee"]),
            "compliance_latest_run": _latest_run(inputs["compliance"]),
        },
        "deployment_agenda": _agenda(decisions),
    }

@router.get("/api/idle-capital-deployment/summary")
def idle_capital_deployment_summary():
    session = _require_user()
    return _build_summary(session.get("email"))

@router.post("/api/idle-capital-deployment/run")
def idle_capital_deployment_run(payload: dict = Body(default=None)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    summary = _build_summary(email)
    overview = summary.get("idle_capital_deployment_overview") or {}
    run = {
        "run_id": f"icd_{time.time_ns()}",
        "mission": "QNT30685",
        "trigger": (payload or {}).get("trigger") or "manual",
        "timestamp": _now_ts(),
        "generated_at": summary.get("generated_at"),
        "deployment_posture": overview.get("deployment_posture"),
        "deployment_score": overview.get("deployment_score"),
        "deploy_count": overview.get("deploy_count"),
        "accelerate_count": overview.get("accelerate_count"),
        "rebalance_count": overview.get("rebalance_count"),
        "hold_count": overview.get("hold_count"),
        "escalate_count": overview.get("escalate_count"),
        "idle_capital_millions": overview.get("idle_capital_millions"),
    }
    store.setdefault("runs", []).insert(0, run)
    store["runs"] = store.get("runs", [])[:120]
    _save(email, store)
    return {"status": "ok", "summary": summary, "run": run}

@router.get("/api/idle-capital-deployment/audit")
def idle_capital_deployment_audit():
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    runs = store.get("runs") or []
    return {
        "mission": "QNT30685",
        "run_count": len(runs),
        "latest_run": runs[0] if runs else None,
        "runs": runs[:20],
        "policy": store.get("policy") or dict(DEFAULT_POLICY),
    }

@router.post("/api/idle-capital-deployment/policy")
def idle_capital_deployment_policy(payload: dict = Body(...)):
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
