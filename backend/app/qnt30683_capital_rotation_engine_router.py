from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["capital-rotation-engine"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ROTATION_DIR = ARTIFACTS_DIR / "capital_rotation_engine"

DEFAULT_POLICY = {
    "minimum_rotation_score": 84.0,
    "minimum_defense_score": 80.0,
    "minimum_restoration_score": 80.0,
    "minimum_recovery_score": 78.0,
    "minimum_continuity_score": 76.0,
    "minimum_governance_score": 78.0,
    "minimum_compliance_score": 78.0,
    "maximum_drawdown_pct": 14.0,
    "maximum_exception_pressure": 22.0,
    "maximum_break_pressure": 18.0,
    "minimum_target_quality_score": 60.0,
}

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _artifact_file(folder: str, email: str) -> Path:
    return ARTIFACTS_DIR / folder / f"{_safe(email)}.json"

def _path(email: str) -> Path:
    ROTATION_DIR.mkdir(parents=True, exist_ok=True)
    return ROTATION_DIR / f"{_safe(email)}.json"

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
        "defense": _read_json(_artifact_file("drawdown_defense_system", email), {"policy": {}, "runs": []}),
        "restoration": _read_json(_artifact_file("capital_restoration_engine", email), {"policy": {}, "runs": []}),
        "recovery": _read_json(_artifact_file("live_allocation_recovery_authority", email), {"policy": {}, "runs": []}),
        "remediation": _read_json(_artifact_file("live_allocation_remediation_command", email), {"policy": {}, "runs": []}),
        "continuity": _read_json(_artifact_file("live_allocation_continuity_command", email), {"policy": {}, "runs": []}),
        "governance": _read_json(_artifact_file("execution_governance_command", email), {"policy": {}, "runs": []}),
        "committee": _read_json(_artifact_file("capital_committee_oversight_mesh", email), {"policy": {}, "runs": []}),
        "compliance": _read_json(_artifact_file("institutional_compliance_layer", email), {"policy": {}, "runs": []}),
        "ledger": _read_json(_artifact_file("investor_capital_ledger", email), {"accounts": [], "entries": [], "allocations": []}),
        "pnl": _read_json(_artifact_file("investor_pnl_ledger", email), {"positions": [], "ledger": []}),
        "execution": _read_json(_artifact_file("strategy_execution_engine", email), {"strategy_allocations": [], "trades": [], "history": []}),
    }

def _rotation_rows(inputs: dict, policy: dict) -> list[dict]:
    defense_run = _latest_run(inputs["defense"])
    restoration_run = _latest_run(inputs["restoration"])
    recovery_run = _latest_run(inputs["recovery"])
    remediation_run = _latest_run(inputs["remediation"])
    continuity_run = _latest_run(inputs["continuity"])
    governance_run = _latest_run(inputs["governance"])
    committee_run = _latest_run(inputs["committee"])
    compliance_run = _latest_run(inputs["compliance"])

    allocations = inputs["execution"].get("strategy_allocations") or []
    positions = inputs["pnl"].get("positions") or []
    pnl_ledger = inputs["pnl"].get("ledger") or []

    total_capital = sum(float(a.get("allocated_amount") or a.get("allocation_amount") or a.get("capital") or 0.0) for a in allocations)
    total_mv = sum(float(p.get("market_value") or p.get("notional") or p.get("value") or 0.0) for p in positions)
    governed_capital = max(total_capital, total_mv)

    realized = sum(float(x.get("realized_pnl") or x.get("pnl") or 0.0) for x in pnl_ledger)
    unrealized = sum(float(p.get("unrealized_pnl") or 0.0) for p in positions)
    pnl_total = realized + unrealized
    drawdown_pct = abs(min(pnl_total, 0.0)) / max(governed_capital, 1.0) * 100.0

    active_allocations = len(allocations)
    active_positions = len([p for p in positions if float(p.get("market_value") or p.get("notional") or p.get("value") or 0.0) != 0.0])

    defense_score = float(defense_run.get("defense_score") or 0.0)
    restoration_score = float(restoration_run.get("restoration_score") or 0.0)
    recovery_score = float(recovery_run.get("recovery_score") or 0.0)
    continuity_score = float(continuity_run.get("continuity_score") or 0.0)
    governance_score = float(governance_run.get("governance_score") or governance_run.get("supervisory_score") or 0.0)
    compliance_score = float(compliance_run.get("release_score") or compliance_run.get("compliance_score") or 0.0)

    positive_allocs = [float(a.get("allocated_amount") or a.get("allocation_amount") or a.get("capital") or 0.0) for a in allocations if float(a.get("allocated_amount") or a.get("allocation_amount") or a.get("capital") or 0.0) > 0]
    concentration_pct = 0.0
    if positive_allocs and governed_capital > 0:
        concentration_pct = max(positive_allocs) / governed_capital * 100.0

    target_quality_score = max(0.0, min(100.0,
        restoration_score * 0.30 +
        continuity_score * 0.20 +
        governance_score * 0.18 +
        compliance_score * 0.18 +
        max(0.0, 100.0 - min(drawdown_pct * 2.0, 30.0)) * 0.14
    ))

    exception_pressure = 0.0
    exception_pressure += float(defense_run.get("escalate_count") or 0.0) * 5.0
    exception_pressure += float(remediation_run.get("escalate_count") or 0.0) * 4.0
    exception_pressure += float(committee_run.get("escalate_count") or committee_run.get("review_count") or 0.0) * 2.0
    exception_pressure = min(exception_pressure, 30.0)

    break_pressure = 0.0
    if drawdown_pct > policy["maximum_drawdown_pct"]:
        break_pressure += min(7.0, (drawdown_pct - policy["maximum_drawdown_pct"]) * 0.40)
    if defense_score < policy["minimum_defense_score"]:
        break_pressure += min(5.0, (policy["minimum_defense_score"] - defense_score) * 0.30)
    if restoration_score < policy["minimum_restoration_score"]:
        break_pressure += min(5.0, (policy["minimum_restoration_score"] - restoration_score) * 0.30)
    if recovery_score < policy["minimum_recovery_score"]:
        break_pressure += min(5.0, (policy["minimum_recovery_score"] - recovery_score) * 0.30)
    if target_quality_score < policy["minimum_target_quality_score"]:
        break_pressure += min(5.0, (policy["minimum_target_quality_score"] - target_quality_score) * 0.20)

    rotation_raw = (
        defense_score * 0.22 +
        restoration_score * 0.20 +
        recovery_score * 0.14 +
        continuity_score * 0.12 +
        governance_score * 0.12 +
        compliance_score * 0.10 +
        max(0.0, 100.0 - min(concentration_pct * 0.8, 20.0)) * 0.10
    )
    rotation_score = max(0.0, min(100.0, rotation_raw - exception_pressure - break_pressure))

    return [{
        "portfolio_id": "CAPITAL_ROTATION_BOOK",
        "governed_capital_millions": _round_money(governed_capital / 1_000_000.0),
        "active_allocations": active_allocations,
        "active_positions": active_positions,
        "pnl_total": _round_money(pnl_total),
        "drawdown_pct": _round_pct(drawdown_pct),
        "concentration_pct": _round_pct(concentration_pct),
        "target_quality_score": _round_pct(target_quality_score),
        "defense_score": _round_pct(defense_score),
        "restoration_score": _round_pct(restoration_score),
        "recovery_score": _round_pct(recovery_score),
        "continuity_score": _round_pct(continuity_score),
        "governance_score": _round_pct(governance_score),
        "compliance_score": _round_pct(compliance_score),
        "exception_pressure": _round_pct(exception_pressure),
        "break_pressure": _round_pct(break_pressure),
        "rotation_score": _round_pct(rotation_score),
        "latest_defense_action": defense_run.get("defense_posture") or defense_run.get("action"),
        "latest_restoration_action": restoration_run.get("restoration_posture") or restoration_run.get("action"),
        "latest_recovery_action": recovery_run.get("recovery_posture") or recovery_run.get("action"),
    }]

def _decisions(rows: list[dict], policy: dict) -> list[dict]:
    decisions = []
    for row in rows:
        score = float(row.get("rotation_score") or 0.0)
        exception_pressure = float(row.get("exception_pressure") or 0.0)
        break_pressure = float(row.get("break_pressure") or 0.0)
        drawdown_pct = float(row.get("drawdown_pct") or 0.0)
        concentration_pct = float(row.get("concentration_pct") or 0.0)
        target_quality_score = float(row.get("target_quality_score") or 0.0)

        action = "ROTATE"
        reasons = []

        if score < policy["minimum_rotation_score"]:
            action = "REBALANCE"
            reasons.append("rotation score below threshold")
        if concentration_pct > 45.0 and action in {"ROTATE", "REBALANCE"}:
            action = "REDUCE"
            reasons.append("concentration too high for safe rotation")
        if exception_pressure > policy["maximum_exception_pressure"]:
            action = "HOLD"
            reasons.append("exception pressure above threshold")
        if break_pressure > policy["maximum_break_pressure"]:
            action = "ESCALATE"
            reasons.append("break pressure above threshold")
        if drawdown_pct > policy["maximum_drawdown_pct"] * 1.2:
            action = "ESCALATE"
            reasons.append("drawdown exceeds rotation tolerance")
        elif target_quality_score < policy["minimum_target_quality_score"] and action == "ROTATE":
            action = "REBALANCE"
            reasons.append("target quality below threshold")
        if not reasons:
            reasons.append("rotation posture inside governed band")

        confidence = max(0.5, min(0.99, 0.99 - (exception_pressure + break_pressure) / 200.0))
        decisions.append({
            "portfolio_id": row.get("portfolio_id"),
            "action": action,
            "confidence": _round_pct(confidence),
            "reason": "; ".join(reasons),
            "governed_capital_millions": row.get("governed_capital_millions"),
            "rotation_score": row.get("rotation_score"),
        })
    return decisions

def _overview(rows: list[dict], decisions: list[dict]) -> dict:
    if not rows:
        return {
            "rotation_posture": "EMPTY",
            "rotation_score": 0.0,
            "rotate_count": 0,
            "rebalance_count": 0,
            "reduce_count": 0,
            "hold_count": 0,
            "escalate_count": 0,
            "rotatable_capital_millions": 0.0,
        }
    score = sum(float(r.get("rotation_score") or 0.0) for r in rows) / len(rows)
    cap = sum(float(r.get("governed_capital_millions") or 0.0) for r in rows)
    counts = {"ROTATE": 0, "REBALANCE": 0, "REDUCE": 0, "HOLD": 0, "ESCALATE": 0}
    for d in decisions:
        counts[d.get("action")] = counts.get(d.get("action"), 0) + 1
    posture = "ACTIVE_ROTATION"
    if counts["ESCALATE"] > 0:
        posture = "ESCALATED"
    elif counts["HOLD"] > 0:
        posture = "CONSTRAINED"
    elif counts["REDUCE"] > 0:
        posture = "REDUCED"
    elif counts["REBALANCE"] > 0:
        posture = "REBALANCING"
    return {
        "rotation_posture": posture,
        "rotation_score": _round_pct(score),
        "rotate_count": counts["ROTATE"],
        "rebalance_count": counts["REBALANCE"],
        "reduce_count": counts["REDUCE"],
        "hold_count": counts["HOLD"],
        "escalate_count": counts["ESCALATE"],
        "rotatable_capital_millions": _round_money(cap),
    }

def _agenda(decisions: list[dict]) -> list[dict]:
    agenda = []
    for idx, d in enumerate(decisions, start=1):
        agenda.append({
            "sequence": idx,
            "portfolio_id": d.get("portfolio_id"),
            "action": d.get("action"),
            "reason": d.get("reason"),
            "governed_capital_millions": d.get("governed_capital_millions"),
        })
    return agenda

def _build_summary(email: str):
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    inputs = _artifact_inputs(email)
    rotation_book = _rotation_rows(inputs, policy)
    rotation_decisions = _decisions(rotation_book, policy)
    overview = _overview(rotation_book, rotation_decisions)
    return {
        "mission": "QNT30683",
        "generated_at": _now_iso(),
        "policy": policy,
        "capital_rotation_overview": overview,
        "rotation_book": rotation_book,
        "rotation_decisions": rotation_decisions,
        "rotation_dependencies": {
            "defense_latest_run": _latest_run(inputs["defense"]),
            "restoration_latest_run": _latest_run(inputs["restoration"]),
            "recovery_latest_run": _latest_run(inputs["recovery"]),
            "remediation_latest_run": _latest_run(inputs["remediation"]),
            "continuity_latest_run": _latest_run(inputs["continuity"]),
            "governance_latest_run": _latest_run(inputs["governance"]),
            "committee_latest_run": _latest_run(inputs["committee"]),
            "compliance_latest_run": _latest_run(inputs["compliance"]),
        },
        "rotation_agenda": _agenda(rotation_decisions),
    }

@router.get("/api/capital-rotation-engine/summary")
def capital_rotation_engine_summary():
    session = _require_user()
    return _build_summary(session.get("email"))

@router.post("/api/capital-rotation-engine/run")
def capital_rotation_engine_run(payload: dict = Body(default=None)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    summary = _build_summary(email)
    overview = summary.get("capital_rotation_overview") or {}
    run = {
        "run_id": f"creg_{time.time_ns()}",
        "mission": "QNT30683",
        "trigger": (payload or {}).get("trigger") or "manual",
        "timestamp": _now_ts(),
        "generated_at": summary.get("generated_at"),
        "rotation_posture": overview.get("rotation_posture"),
        "rotation_score": overview.get("rotation_score"),
        "rotate_count": overview.get("rotate_count"),
        "rebalance_count": overview.get("rebalance_count"),
        "reduce_count": overview.get("reduce_count"),
        "hold_count": overview.get("hold_count"),
        "escalate_count": overview.get("escalate_count"),
        "rotatable_capital_millions": overview.get("rotatable_capital_millions"),
    }
    store.setdefault("runs", []).insert(0, run)
    store["runs"] = store.get("runs", [])[:120]
    _save(email, store)
    return {"status": "ok", "summary": summary, "run": run}

@router.get("/api/capital-rotation-engine/audit")
def capital_rotation_engine_audit():
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    runs = store.get("runs") or []
    return {
        "mission": "QNT30683",
        "run_count": len(runs),
        "latest_run": runs[0] if runs else None,
        "runs": runs[:20],
        "policy": store.get("policy") or dict(DEFAULT_POLICY),
    }

@router.post("/api/capital-rotation-engine/policy")
def capital_rotation_engine_policy(payload: dict = Body(...)):
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
