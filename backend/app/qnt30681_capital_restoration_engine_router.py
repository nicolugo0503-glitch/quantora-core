from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["capital-restoration-engine"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
RESTORATION_DIR = ARTIFACTS_DIR / "capital_restoration_engine"

DEFAULT_POLICY = {
    "minimum_restoration_score": 84.0,
    "minimum_recovery_score": 80.0,
    "minimum_remediation_score": 80.0,
    "minimum_continuity_score": 76.0,
    "minimum_governance_score": 78.0,
    "minimum_compliance_score": 78.0,
    "minimum_recovery_probability_pct": 55.0,
    "maximum_drawdown_pct": 18.0,
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
    RESTORATION_DIR.mkdir(parents=True, exist_ok=True)
    return RESTORATION_DIR / f"{_safe(email)}.json"


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
        "recovery": _read_json(_artifact_file("live_allocation_recovery_authority", email), {"policy": {}, "runs": []}),
        "remediation": _read_json(_artifact_file("live_allocation_remediation_command", email), {"policy": {}, "runs": []}),
        "exception": _read_json(_artifact_file("live_allocation_exception_governance_layer", email), {"policy": {}, "runs": []}),
        "oversight": _read_json(_artifact_file("live_allocation_post_close_oversight_layer", email), {"policy": {}, "runs": []}),
        "continuity": _read_json(_artifact_file("live_allocation_continuity_command", email), {"policy": {}, "runs": []}),
        "governance": _read_json(_artifact_file("execution_governance_command", email), {"policy": {}, "runs": []}),
        "committee": _read_json(_artifact_file("capital_committee_oversight_mesh", email), {"policy": {}, "runs": []}),
        "compliance": _read_json(_artifact_file("institutional_compliance_layer", email), {"policy": {}, "runs": []}),
        "ledger": _read_json(_artifact_file("investor_capital_ledger", email), {"accounts": [], "entries": [], "allocations": []}),
        "pnl": _read_json(_artifact_file("investor_pnl_ledger", email), {"positions": [], "ledger": []}),
        "execution": _read_json(_artifact_file("strategy_execution_engine", email), {"strategy_allocations": [], "trades": [], "history": []}),
    }


def _restoration_rows(inputs: dict, policy: dict) -> list[dict]:
    recovery_run = _latest_run(inputs["recovery"])
    remediation_run = _latest_run(inputs["remediation"])
    exception_run = _latest_run(inputs["exception"])
    oversight_run = _latest_run(inputs["oversight"])
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
    active_positions = len([p for p in positions if float(p.get("market_value") or p.get("notional") or p.get("value") or 0.0) != 0.0])
    active_allocations = len(allocations)

    recovery_score = float(recovery_run.get("recovery_score") or 0.0)
    remediation_score = float(remediation_run.get("remediation_score") or 0.0)
    continuity_score = float(continuity_run.get("continuity_score") or 0.0)
    oversight_score = float(oversight_run.get("oversight_score") or 0.0)
    governance_score = float(governance_run.get("governance_score") or governance_run.get("supervisory_score") or 0.0)
    compliance_score = float(compliance_run.get("release_score") or compliance_run.get("compliance_score") or 0.0)
    recovery_probability_pct = float(recovery_run.get("recovery_probability_pct") or recovery_run.get("recovery_probability") or 0.0)

    exception_pressure = 0.0
    break_pressure = 0.0

    ex_runs = exception_run.get("runs") or []
    if ex_runs:
        exception_pressure += float(ex_runs[0].get("escalate_count") or 0.0) * 6.0
    exception_pressure += float(remediation_run.get("escalate_count") or 0.0) * 5.0
    exception_pressure += float(recovery_run.get("escalate_count") or 0.0) * 6.0
    exception_pressure += float(committee_run.get("review_count") or committee_run.get("escalate_count") or 0.0) * 2.0
    exception_pressure = min(exception_pressure, 30.0)

    if recovery_score < policy["minimum_recovery_score"]:
        break_pressure += min(6.0, (policy["minimum_recovery_score"] - recovery_score) * 0.35)
    if remediation_score < policy["minimum_remediation_score"]:
        break_pressure += min(6.0, (policy["minimum_remediation_score"] - remediation_score) * 0.35)
    if continuity_score < policy["minimum_continuity_score"]:
        break_pressure += min(5.0, (policy["minimum_continuity_score"] - continuity_score) * 0.30)
    if governance_score < policy["minimum_governance_score"]:
        break_pressure += min(5.0, (policy["minimum_governance_score"] - governance_score) * 0.30)
    if compliance_score < policy["minimum_compliance_score"]:
        break_pressure += min(5.0, (policy["minimum_compliance_score"] - compliance_score) * 0.30)
    if drawdown_pct > policy["maximum_drawdown_pct"]:
        break_pressure += min(6.0, (drawdown_pct - policy["maximum_drawdown_pct"]) * 0.40)
    if recovery_probability_pct < policy["minimum_recovery_probability_pct"]:
        break_pressure += min(6.0, (policy["minimum_recovery_probability_pct"] - recovery_probability_pct) * 0.20)

    restoration_raw = (
        recovery_score * 0.24
        + remediation_score * 0.18
        + continuity_score * 0.14
        + oversight_score * 0.12
        + governance_score * 0.12
        + compliance_score * 0.12
        + max(0.0, 100.0 - min(drawdown_pct * 2.0, 25.0)) * 0.08
    )
    restoration_score = max(0.0, min(100.0, restoration_raw - exception_pressure - break_pressure))

    return [{
        "portfolio_id": "CAPITAL_RESTORATION_BOOK",
        "governed_capital_millions": _round_money(governed_capital / 1_000_000.0),
        "active_positions": active_positions,
        "active_allocations": active_allocations,
        "pnl_total": _round_money(pnl_total),
        "drawdown_pct": _round_pct(drawdown_pct),
        "recovery_probability_pct": _round_pct(recovery_probability_pct),
        "recovery_score": _round_pct(recovery_score),
        "remediation_score": _round_pct(remediation_score),
        "continuity_score": _round_pct(continuity_score),
        "oversight_score": _round_pct(oversight_score),
        "governance_score": _round_pct(governance_score),
        "compliance_score": _round_pct(compliance_score),
        "exception_pressure": _round_pct(exception_pressure),
        "break_pressure": _round_pct(break_pressure),
        "restoration_score": _round_pct(restoration_score),
        "latest_recovery_action": recovery_run.get("recovery_posture") or recovery_run.get("action"),
        "latest_remediation_action": remediation_run.get("remediation_posture") or remediation_run.get("action"),
        "latest_continuity_action": continuity_run.get("continuity_posture") or continuity_run.get("action"),
    }]


def _decisions(rows: list[dict], policy: dict) -> list[dict]:
    decisions = []
    for row in rows:
        score = float(row.get("restoration_score") or 0.0)
        exception_pressure = float(row.get("exception_pressure") or 0.0)
        break_pressure = float(row.get("break_pressure") or 0.0)
        drawdown_pct = float(row.get("drawdown_pct") or 0.0)
        recovery_probability_pct = float(row.get("recovery_probability_pct") or 0.0)

        action = "RESTORE"
        reasons = []

        if score < policy["minimum_restoration_score"]:
            action = "REVIEW"
            reasons.append("restoration score below threshold")
        if exception_pressure > policy["maximum_exception_pressure"]:
            action = "HOLD"
            reasons.append("exception pressure above threshold")
        if break_pressure > policy["maximum_break_pressure"]:
            action = "ESCALATE"
            reasons.append("break pressure above threshold")
        if drawdown_pct > policy["maximum_drawdown_pct"]:
            action = "ESCALATE"
            reasons.append("drawdown exceeds restoration tolerance")
        if recovery_probability_pct < policy["minimum_recovery_probability_pct"] and action == "RESTORE":
            action = "REVIEW"
            reasons.append("recovery probability below threshold")
        if not reasons:
            reasons.append("restoration posture inside governed band")

        confidence = max(0.5, min(0.99, 0.99 - (exception_pressure + break_pressure) / 200.0))
        decisions.append({
            "portfolio_id": row.get("portfolio_id"),
            "action": action,
            "confidence": _round_pct(confidence),
            "reason": "; ".join(reasons),
            "governed_capital_millions": row.get("governed_capital_millions"),
            "restoration_score": row.get("restoration_score"),
        })
    return decisions


def _overview(rows: list[dict], decisions: list[dict]) -> dict:
    if not rows:
        return {
            "restoration_posture": "EMPTY",
            "restoration_score": 0.0,
            "restore_count": 0,
            "review_count": 0,
            "hold_count": 0,
            "escalate_count": 0,
            "restorable_capital_millions": 0.0,
        }
    score = sum(float(r.get("restoration_score") or 0.0) for r in rows) / len(rows)
    cap = sum(float(r.get("governed_capital_millions") or 0.0) for r in rows)
    counts = {"RESTORE": 0, "REVIEW": 0, "HOLD": 0, "ESCALATE": 0}
    for d in decisions:
        counts[d.get("action")] = counts.get(d.get("action"), 0) + 1
    posture = "STABLE_RESTORATION"
    if counts["ESCALATE"] > 0:
        posture = "ESCALATED"
    elif counts["HOLD"] > 0:
        posture = "CONSTRAINED"
    elif counts["REVIEW"] > 0:
        posture = "UNDER_REVIEW"
    return {
        "restoration_posture": posture,
        "restoration_score": _round_pct(score),
        "restore_count": counts["RESTORE"],
        "review_count": counts["REVIEW"],
        "hold_count": counts["HOLD"],
        "escalate_count": counts["ESCALATE"],
        "restorable_capital_millions": _round_money(cap),
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
    restoration_book = _restoration_rows(inputs, policy)
    restoration_decisions = _decisions(restoration_book, policy)
    overview = _overview(restoration_book, restoration_decisions)
    return {
        "mission": "QNT30681",
        "generated_at": _now_iso(),
        "policy": policy,
        "capital_restoration_overview": overview,
        "restoration_book": restoration_book,
        "restoration_decisions": restoration_decisions,
        "restoration_dependencies": {
            "recovery_latest_run": _latest_run(inputs["recovery"]),
            "remediation_latest_run": _latest_run(inputs["remediation"]),
            "exception_latest_run": _latest_run(inputs["exception"]),
            "oversight_latest_run": _latest_run(inputs["oversight"]),
            "continuity_latest_run": _latest_run(inputs["continuity"]),
            "governance_latest_run": _latest_run(inputs["governance"]),
            "committee_latest_run": _latest_run(inputs["committee"]),
            "compliance_latest_run": _latest_run(inputs["compliance"]),
        },
        "restoration_agenda": _agenda(restoration_decisions),
    }


@router.get("/api/capital-restoration-engine/summary")
def capital_restoration_engine_summary():
    session = _require_user()
    return _build_summary(session.get("email"))


@router.post("/api/capital-restoration-engine/run")
def capital_restoration_engine_run(payload: dict = Body(default=None)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    summary = _build_summary(email)
    overview = summary.get("capital_restoration_overview") or {}
    run = {
        "run_id": f"cre_{time.time_ns()}",
        "mission": "QNT30681",
        "trigger": (payload or {}).get("trigger") or "manual",
        "timestamp": _now_ts(),
        "generated_at": summary.get("generated_at"),
        "restoration_posture": overview.get("restoration_posture"),
        "restoration_score": overview.get("restoration_score"),
        "restore_count": overview.get("restore_count"),
        "review_count": overview.get("review_count"),
        "hold_count": overview.get("hold_count"),
        "escalate_count": overview.get("escalate_count"),
        "restorable_capital_millions": overview.get("restorable_capital_millions"),
    }
    store.setdefault("runs", []).insert(0, run)
    store["runs"] = store.get("runs", [])[:120]
    _save(email, store)
    return {"status": "ok", "summary": summary, "run": run}


@router.get("/api/capital-restoration-engine/audit")
def capital_restoration_engine_audit():
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    runs = store.get("runs") or []
    return {
        "mission": "QNT30681",
        "run_count": len(runs),
        "latest_run": runs[0] if runs else None,
        "runs": runs[:20],
        "policy": store.get("policy") or dict(DEFAULT_POLICY),
    }


@router.post("/api/capital-restoration-engine/policy")
def capital_restoration_engine_policy(payload: dict = Body(...)):
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
