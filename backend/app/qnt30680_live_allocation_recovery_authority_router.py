from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["live-allocation-recovery-authority"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
RECOVERY_DIR = ARTIFACTS_DIR / "live_allocation_recovery_authority"

DEFAULT_POLICY = {
    "minimum_recovery_score": 82.0,
    "maximum_drawdown_pct": 16.0,
    "maximum_loss_persistence_pct": 10.0,
    "minimum_recovery_probability_pct": 58.0,
    "minimum_continuity_score": 76.0,
    "minimum_remediation_score": 80.0,
    "minimum_governance_score": 78.0,
    "minimum_compliance_score": 78.0,
    "maximum_exception_pressure": 24.0,
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
    RECOVERY_DIR.mkdir(parents=True, exist_ok=True)
    return RECOVERY_DIR / f"{_safe(email)}.json"


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
        "remediation": _read_json(_artifact_file("live_allocation_remediation_command", email), {"policy": {}, "runs": []}),
        "exception": _read_json(_artifact_file("live_allocation_exception_governance_layer", email), {"policy": {}, "runs": []}),
        "oversight": _read_json(_artifact_file("live_allocation_post_close_oversight_layer", email), {"policy": {}, "runs": []}),
        "close": _read_json(_artifact_file("live_allocation_close_authority", email), {"policy": {}, "runs": []}),
        "settlement": _read_json(_artifact_file("live_allocation_settlement_command", email), {"policy": {}, "runs": []}),
        "reconciliation": _read_json(_artifact_file("live_allocation_reconciliation_command", email), {"policy": {}, "runs": []}),
        "continuity": _read_json(_artifact_file("live_allocation_continuity_command", email), {"policy": {}, "runs": []}),
        "governance": _read_json(_artifact_file("execution_governance_command", email), {"policy": {}, "runs": []}),
        "compliance": _read_json(_artifact_file("institutional_compliance_layer", email), {"policy": {}, "runs": []}),
        "ledger": _read_json(_artifact_file("investor_capital_ledger", email), {"accounts": [], "entries": [], "allocations": []}),
        "pnl": _read_json(_artifact_file("investor_pnl_ledger", email), {"positions": [], "ledger": []}),
        "execution": _read_json(_artifact_file("strategy_execution_engine", email), {"strategy_allocations": [], "trades": [], "history": []}),
        "performance": _read_json(_artifact_file("performance_engine_v2", email), {"snapshots": [], "strategy_history": [], "investor_history": []}),
    }


def _recovery_rows(inputs: dict, policy: dict) -> list[dict]:
    remediation_run = _latest_run(inputs["remediation"])
    exception_run = _latest_run(inputs["exception"])
    oversight_run = _latest_run(inputs["oversight"])
    close_run = _latest_run(inputs["close"])
    settlement_run = _latest_run(inputs["settlement"])
    reconciliation_run = _latest_run(inputs["reconciliation"])
    continuity_run = _latest_run(inputs["continuity"])
    governance_run = _latest_run(inputs["governance"])
    compliance_run = _latest_run(inputs["compliance"])

    allocations = inputs["execution"].get("strategy_allocations") or []
    positions = inputs["pnl"].get("positions") or []
    pnl_ledger = inputs["pnl"].get("ledger") or []
    perf_snaps = inputs["performance"].get("snapshots") or []

    capital = sum(float(a.get("allocated_amount") or a.get("allocation_amount") or a.get("capital") or 0.0) for a in allocations)
    if capital <= 0:
        capital = sum(float(p.get("market_value") or p.get("notional") or p.get("value") or 0.0) for p in positions)

    realized = sum(float(x.get("realized_pnl") or x.get("pnl") or 0.0) for x in pnl_ledger)
    unrealized = sum(float(p.get("unrealized_pnl") or 0.0) for p in positions)
    total_pnl = realized + unrealized

    worst_unrealized = min([float(p.get("unrealized_pnl") or 0.0) for p in positions] + [0.0])
    drawdown_pct = abs(min(0.0, total_pnl)) / max(capital, 1.0) * 100.0
    loss_persistence_pct = abs(min(0.0, worst_unrealized)) / max(capital, 1.0) * 100.0

    continuity_score = float(continuity_run.get("continuity_score") or 0.0)
    remediation_score = float(remediation_run.get("remediation_score") or 0.0)
    governance_score = float(governance_run.get("governance_score") or governance_run.get("supervisory_score") or 0.0)
    compliance_score = float(compliance_run.get("release_score") or compliance_run.get("compliance_score") or 0.0)

    exception_pressure = 0.0
    if float(exception_run.get("exception_governance_score") or 0.0) < 80:
        exception_pressure += 8.0
    exception_pressure += float(exception_run.get("hold_count") or 0.0) * 4.0
    exception_pressure += float(exception_run.get("escalate_count") or 0.0) * 6.0
    exception_pressure += float(remediation_run.get("escalate_count") or 0.0) * 5.0

    break_pressure = 0.0
    for score, threshold, weight in [
        (continuity_score, policy["minimum_continuity_score"], 0.4),
        (remediation_score, policy["minimum_remediation_score"], 0.45),
        (governance_score, policy["minimum_governance_score"], 0.35),
        (compliance_score, policy["minimum_compliance_score"], 0.35),
    ]:
        if score < threshold:
            break_pressure += min(8.0, (threshold - score) * weight)

    viability_bonus = 0.0
    if continuity_score >= policy["minimum_continuity_score"]:
        viability_bonus += 6.0
    if remediation_score >= policy["minimum_remediation_score"]:
        viability_bonus += 6.0
    if governance_score >= policy["minimum_governance_score"]:
        viability_bonus += 4.0
    if compliance_score >= policy["minimum_compliance_score"]:
        viability_bonus += 4.0
    if perf_snaps:
        viability_bonus += 2.0

    recovery_probability_pct = max(
        0.0,
        min(
            100.0,
            52.0
            + viability_bonus
            - drawdown_pct * 1.15
            - loss_persistence_pct * 0.9
            - exception_pressure * 0.8
            - break_pressure * 0.75,
        ),
    )

    recovery_score = max(
        0.0,
        min(
            100.0,
            (
                recovery_probability_pct * 0.48
                + max(0.0, 100.0 - drawdown_pct * 3.0) * 0.16
                + max(0.0, 100.0 - loss_persistence_pct * 4.0) * 0.14
                + continuity_score * 0.08
                + remediation_score * 0.06
                + governance_score * 0.04
                + compliance_score * 0.04
            ) - exception_pressure - break_pressure
        ),
    )

    row = {
        "portfolio_id": "LIVE_ALLOCATION_RECOVERY_BOOK",
        "capital_millions": _round_money(capital / 1_000_000.0),
        "drawdown_pct": _round_pct(drawdown_pct),
        "loss_persistence_pct": _round_pct(loss_persistence_pct),
        "recovery_probability_pct": _round_pct(recovery_probability_pct),
        "recovery_score": _round_pct(recovery_score),
        "exception_pressure": _round_pct(exception_pressure),
        "break_pressure": _round_pct(break_pressure),
        "continuity_score": _round_pct(continuity_score),
        "remediation_score": _round_pct(remediation_score),
        "governance_score": _round_pct(governance_score),
        "compliance_score": _round_pct(compliance_score),
        "latest_remediation_posture": remediation_run.get("remediation_posture") or remediation_run.get("action"),
        "latest_exception_posture": exception_run.get("exception_governance_posture") or exception_run.get("action"),
        "latest_close_posture": close_run.get("close_posture") or close_run.get("action"),
        "latest_settlement_posture": settlement_run.get("settlement_posture") or settlement_run.get("action"),
        "latest_reconciliation_posture": reconciliation_run.get("reconciliation_posture") or reconciliation_run.get("action"),
        "latest_oversight_posture": oversight_run.get("oversight_posture") or oversight_run.get("action"),
        "latest_continuity_posture": continuity_run.get("continuity_posture") or continuity_run.get("action"),
    }
    return [row]


def _decisions(rows: list[dict], policy: dict) -> list[dict]:
    decisions = []
    for row in rows:
        action = "RECOVER"
        reasons = []
        drawdown = float(row.get("drawdown_pct") or 0.0)
        loss_persistence = float(row.get("loss_persistence_pct") or 0.0)
        probability = float(row.get("recovery_probability_pct") or 0.0)
        score = float(row.get("recovery_score") or 0.0)
        exception_pressure = float(row.get("exception_pressure") or 0.0)
        break_pressure = float(row.get("break_pressure") or 0.0)

        if score < policy["minimum_recovery_score"]:
            action = "REDUCE"
            reasons.append("recovery score below threshold")
        if probability < policy["minimum_recovery_probability_pct"]:
            action = "ROTATE"
            reasons.append("recovery probability below threshold")
        if drawdown > policy["maximum_drawdown_pct"]:
            action = "EXIT"
            reasons.append("drawdown severity above threshold")
        if loss_persistence > policy["maximum_loss_persistence_pct"]:
            action = "EXIT"
            reasons.append("loss persistence above threshold")
        if exception_pressure > policy["maximum_exception_pressure"] or break_pressure > policy["maximum_break_pressure"]:
            action = "ESCALATE"
            reasons.append("institutional pressure above governed band")
        if not reasons:
            reasons.append("recovery posture remains viable")

        confidence = max(0.5, min(0.99, 0.99 - (drawdown + loss_persistence + exception_pressure + break_pressure) / 250.0))
        decisions.append({
            "portfolio_id": row.get("portfolio_id"),
            "action": action,
            "confidence": _round_pct(confidence),
            "reason": "; ".join(reasons),
            "capital_millions": row.get("capital_millions"),
            "recovery_score": row.get("recovery_score"),
            "recovery_probability_pct": row.get("recovery_probability_pct"),
        })
    return decisions


def _overview(rows: list[dict], decisions: list[dict]) -> dict:
    if not rows:
        return {
            "recovery_posture": "EMPTY",
            "recovery_score": 0.0,
            "recover_count": 0,
            "rotate_count": 0,
            "reduce_count": 0,
            "exit_count": 0,
            "escalate_count": 0,
            "recovery_capital_millions": 0.0,
        }
    score = sum(float(r.get("recovery_score") or 0.0) for r in rows) / len(rows)
    capital = sum(float(r.get("capital_millions") or 0.0) for r in rows)
    counts = {"RECOVER": 0, "ROTATE": 0, "REDUCE": 0, "EXIT": 0, "ESCALATE": 0}
    for d in decisions:
        counts[d.get("action")] = counts.get(d.get("action"), 0) + 1
    posture = "RECOVERING"
    if counts["ESCALATE"] > 0:
        posture = "ESCALATED"
    elif counts["EXIT"] > 0:
        posture = "EXITING"
    elif counts["ROTATE"] > 0:
        posture = "ROTATING"
    elif counts["REDUCE"] > 0:
        posture = "REDUCING"
    return {
        "recovery_posture": posture,
        "recovery_score": _round_pct(score),
        "recover_count": counts["RECOVER"],
        "rotate_count": counts["ROTATE"],
        "reduce_count": counts["REDUCE"],
        "exit_count": counts["EXIT"],
        "escalate_count": counts["ESCALATE"],
        "recovery_capital_millions": _round_money(capital),
    }


def _agenda(decisions: list[dict]) -> list[dict]:
    agenda = []
    for idx, d in enumerate(decisions, start=1):
        agenda.append({
            "sequence": idx,
            "portfolio_id": d.get("portfolio_id"),
            "action": d.get("action"),
            "reason": d.get("reason"),
            "capital_millions": d.get("capital_millions"),
        })
    return agenda


def _build_summary(email: str):
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    inputs = _artifact_inputs(email)
    recovery_book = _recovery_rows(inputs, policy)
    recovery_decisions = _decisions(recovery_book, policy)
    overview = _overview(recovery_book, recovery_decisions)
    return {
        "mission": "QNT30680",
        "generated_at": _now_iso(),
        "policy": policy,
        "live_allocation_recovery_overview": overview,
        "recovery_book": recovery_book,
        "recovery_decisions": recovery_decisions,
        "recovery_dependencies": {
            "remediation_latest_run": _latest_run(inputs["remediation"]),
            "exception_latest_run": _latest_run(inputs["exception"]),
            "oversight_latest_run": _latest_run(inputs["oversight"]),
            "close_latest_run": _latest_run(inputs["close"]),
            "settlement_latest_run": _latest_run(inputs["settlement"]),
            "reconciliation_latest_run": _latest_run(inputs["reconciliation"]),
            "continuity_latest_run": _latest_run(inputs["continuity"]),
            "governance_latest_run": _latest_run(inputs["governance"]),
            "compliance_latest_run": _latest_run(inputs["compliance"]),
        },
        "recovery_agenda": _agenda(recovery_decisions),
    }


@router.get("/api/live-allocation-recovery-authority/summary")
def live_allocation_recovery_summary():
    session = _require_user()
    return _build_summary(session.get("email"))


@router.post("/api/live-allocation-recovery-authority/run")
def live_allocation_recovery_run(payload: dict = Body(default=None)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    summary = _build_summary(email)
    overview = summary.get("live_allocation_recovery_overview") or {}
    run = {
        "run_id": f"lara_{time.time_ns()}",
        "mission": "QNT30680",
        "trigger": (payload or {}).get("trigger") or "manual",
        "timestamp": _now_ts(),
        "generated_at": summary.get("generated_at"),
        "recovery_posture": overview.get("recovery_posture"),
        "recovery_score": overview.get("recovery_score"),
        "recover_count": overview.get("recover_count"),
        "rotate_count": overview.get("rotate_count"),
        "reduce_count": overview.get("reduce_count"),
        "exit_count": overview.get("exit_count"),
        "escalate_count": overview.get("escalate_count"),
        "recovery_capital_millions": overview.get("recovery_capital_millions"),
    }
    store.setdefault("runs", []).insert(0, run)
    store["runs"] = store.get("runs", [])[:120]
    _save(email, store)
    return {"status": "ok", "summary": summary, "run": run}


@router.get("/api/live-allocation-recovery-authority/audit")
def live_allocation_recovery_audit():
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    runs = store.get("runs") or []
    return {
        "mission": "QNT30680",
        "run_count": len(runs),
        "latest_run": runs[0] if runs else None,
        "runs": runs[:20],
        "policy": store.get("policy") or dict(DEFAULT_POLICY),
    }


@router.post("/api/live-allocation-recovery-authority/policy")
def live_allocation_recovery_policy(payload: dict = Body(...)):
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
