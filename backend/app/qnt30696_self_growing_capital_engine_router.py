from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["self-growing-capital-engine"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
GROWTH_DIR = ARTIFACTS_DIR / "self_growing_capital_engine"

DEFAULT_POLICY = {
    "minimum_growth_score": 88.0,
    "minimum_autonomy_score": 84.0,
    "minimum_reporting_score": 82.0,
    "minimum_transparency_score": 82.0,
    "minimum_audit_score": 82.0,
    "minimum_routing_score": 78.0,
    "minimum_governance_score": 82.0,
    "minimum_compliance_score": 84.0,
    "maximum_exception_pressure": 18.0,
    "maximum_break_pressure": 16.0,
    "maximum_drawdown_pct": 12.0,
    "minimum_growth_runbook_pct": 82.0,
}

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _artifact_file(folder: str, email: str) -> Path:
    return ARTIFACTS_DIR / folder / f"{_safe(email)}.json"

def _path(email: str) -> Path:
    GROWTH_DIR.mkdir(parents=True, exist_ok=True)
    return GROWTH_DIR / f"{_safe(email)}.json"

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
        "autonomy": _read_json(_artifact_file("autonomous_fund_mode", email), {"policy": {}, "runs": []}),
        "reporting": _read_json(_artifact_file("reporting_disclosure_automation", email), {"policy": {}, "runs": []}),
        "transparency": _read_json(_artifact_file("investor_transparency_engine", email), {"policy": {}, "runs": []}),
        "audit": _read_json(_artifact_file("audit_regulatory_system", email), {"policy": {}, "runs": []}),
        "routing": _read_json(_artifact_file("global_capital_routing", email), {"policy": {}, "runs": []}),
        "cross_fund": _read_json(_artifact_file("cross_fund_allocation", email), {"policy": {}, "runs": []}),
        "governance": _read_json(_artifact_file("execution_governance_command", email), {"policy": {}, "runs": []}),
        "committee": _read_json(_artifact_file("capital_committee_oversight_mesh", email), {"policy": {}, "runs": []}),
        "compliance": _read_json(_artifact_file("institutional_compliance_layer", email), {"policy": {}, "runs": []}),
        "treasury": _read_json(_artifact_file("sovereign_treasury_command", email), {"policy": {}, "runs": []}),
        "mobility": _read_json(_artifact_file("capital_mobility_control_plane", email), {"policy": {}, "runs": []}),
        "execution": _read_json(_artifact_file("strategy_execution_engine", email), {"strategy_allocations": [], "trades": [], "history": []}),
        "ledger": _read_json(_artifact_file("investor_capital_ledger", email), {"accounts": [], "entries": [], "allocations": []}),
        "pnl": _read_json(_artifact_file("investor_pnl_ledger", email), {"positions": [], "ledger": []}),
    }

def _rows(inputs: dict, policy: dict) -> list[dict]:
    autonomy_run = _latest_run(inputs["autonomy"])
    reporting_run = _latest_run(inputs["reporting"])
    transparency_run = _latest_run(inputs["transparency"])
    audit_run = _latest_run(inputs["audit"])
    routing_run = _latest_run(inputs["routing"])
    cross_fund_run = _latest_run(inputs["cross_fund"])
    governance_run = _latest_run(inputs["governance"])
    committee_run = _latest_run(inputs["committee"])
    compliance_run = _latest_run(inputs["compliance"])
    treasury_run = _latest_run(inputs["treasury"])
    mobility_run = _latest_run(inputs["mobility"])

    ledger_entries = inputs["ledger"].get("entries") or []
    ledger_allocs = inputs["ledger"].get("allocations") or []
    pnl_ledger = inputs["pnl"].get("ledger") or []
    positions = inputs["pnl"].get("positions") or []
    trades = inputs["execution"].get("trades") or []
    allocations = inputs["execution"].get("strategy_allocations") or []

    ledger_capital = sum(float(a.get("amount") or a.get("capital") or a.get("allocated_amount") or 0.0) for a in ledger_allocs)
    total_mv = sum(float(p.get("market_value") or p.get("notional") or p.get("value") or 0.0) for p in positions)
    allocated_capital = sum(float(a.get("allocated_amount") or a.get("allocation_amount") or a.get("capital") or 0.0) for a in allocations)
    governed_capital = max(ledger_capital, total_mv, allocated_capital)

    realized = sum(float(x.get("realized_pnl") or x.get("pnl") or 0.0) for x in pnl_ledger)
    unrealized = sum(float(p.get("unrealized_pnl") or 0.0) for p in positions)
    pnl_total = realized + unrealized
    drawdown_pct = abs(min(pnl_total, 0.0)) / max(governed_capital, 1.0) * 100.0

    autonomy_score = float(autonomy_run.get("autonomy_score") or 0.0)
    reporting_score = float(reporting_run.get("reporting_score") or 0.0)
    transparency_score = float(transparency_run.get("transparency_score") or 0.0)
    audit_score = float(audit_run.get("audit_score") or 0.0)
    routing_score = float(routing_run.get("routing_score") or 0.0)
    allocation_score = float(cross_fund_run.get("allocation_score") or 0.0)
    governance_score = float(governance_run.get("governance_score") or governance_run.get("supervisory_score") or 0.0)
    compliance_score = float(compliance_run.get("release_score") or compliance_run.get("compliance_score") or 0.0)
    treasury_score = float(treasury_run.get("treasury_score") or treasury_run.get("readiness_score") or 0.0)
    mobility_score = float(mobility_run.get("mobility_score") or mobility_run.get("readiness_score") or 0.0)

    growth_runbook_signals = 0
    if autonomy_run: growth_runbook_signals += 1
    if reporting_run: growth_runbook_signals += 1
    if transparency_run: growth_runbook_signals += 1
    if audit_run: growth_runbook_signals += 1
    if ledger_entries: growth_runbook_signals += 1
    growth_runbook_pct = (growth_runbook_signals / 5.0) * 100.0

    operating_signal_pct = min(100.0, (((1 if trades else 0) + (1 if positions else 0) + (1 if pnl_ledger else 0) + (1 if allocations else 0)) / 4.0) * 100.0)
    compounding_signal_pct = min(100.0, (((1 if treasury_run else 0) + (1 if mobility_run else 0) + (1 if compliance_run else 0) + (1 if governance_run else 0)) / 4.0) * 100.0)

    exception_pressure = min(
        float(autonomy_run.get("escalate_count") or 0.0) * 5.0 +
        float(reporting_run.get("escalate_count") or 0.0) * 4.0 +
        float(committee_run.get("escalate_count") or committee_run.get("review_count") or 0.0) * 2.0,
        30.0
    )

    break_pressure = 0.0
    if drawdown_pct > policy["maximum_drawdown_pct"]:
        break_pressure += min(6.0, (drawdown_pct - policy["maximum_drawdown_pct"]) * 0.40)
    if autonomy_score < policy["minimum_autonomy_score"]:
        break_pressure += min(6.0, (policy["minimum_autonomy_score"] - autonomy_score) * 0.30)
    if reporting_score < policy["minimum_reporting_score"]:
        break_pressure += min(6.0, (policy["minimum_reporting_score"] - reporting_score) * 0.30)
    if transparency_score < policy["minimum_transparency_score"]:
        break_pressure += min(6.0, (policy["minimum_transparency_score"] - transparency_score) * 0.30)
    if audit_score < policy["minimum_audit_score"]:
        break_pressure += min(6.0, (policy["minimum_audit_score"] - audit_score) * 0.30)
    if governance_score < policy["minimum_governance_score"]:
        break_pressure += min(6.0, (policy["minimum_governance_score"] - governance_score) * 0.30)
    if compliance_score < policy["minimum_compliance_score"]:
        break_pressure += min(6.0, (policy["minimum_compliance_score"] - compliance_score) * 0.30)
    if growth_runbook_pct < policy["minimum_growth_runbook_pct"]:
        break_pressure += min(6.0, (policy["minimum_growth_runbook_pct"] - growth_runbook_pct) * 0.12)

    growth_raw = (
        autonomy_score * 0.16 +
        reporting_score * 0.12 +
        transparency_score * 0.12 +
        audit_score * 0.12 +
        routing_score * 0.08 +
        allocation_score * 0.06 +
        governance_score * 0.10 +
        compliance_score * 0.10 +
        treasury_score * 0.04 +
        mobility_score * 0.04 +
        growth_runbook_pct * 0.03 +
        operating_signal_pct * 0.02 +
        compounding_signal_pct * 0.01
    )
    growth_score = max(0.0, min(100.0, growth_raw - exception_pressure - break_pressure))

    return [{
        "growth_scope": "SELF_GROWING_CAPITAL",
        "governed_capital_millions": _round_money(governed_capital / 1_000_000.0),
        "trade_count": len(trades),
        "allocation_count": len(allocations),
        "ledger_entry_count": len(ledger_entries),
        "autonomy_score": _round_pct(autonomy_score),
        "reporting_score": _round_pct(reporting_score),
        "transparency_score": _round_pct(transparency_score),
        "audit_score": _round_pct(audit_score),
        "routing_score": _round_pct(routing_score),
        "allocation_score": _round_pct(allocation_score),
        "governance_score": _round_pct(governance_score),
        "compliance_score": _round_pct(compliance_score),
        "treasury_score": _round_pct(treasury_score),
        "mobility_score": _round_pct(mobility_score),
        "growth_runbook_pct": _round_pct(growth_runbook_pct),
        "operating_signal_pct": _round_pct(operating_signal_pct),
        "compounding_signal_pct": _round_pct(compounding_signal_pct),
        "drawdown_pct": _round_pct(drawdown_pct),
        "exception_pressure": _round_pct(exception_pressure),
        "break_pressure": _round_pct(break_pressure),
        "growth_score": _round_pct(growth_score),
    }]

def _decisions(rows: list[dict], policy: dict) -> list[dict]:
    decisions = []
    for row in rows:
        score = float(row.get("growth_score") or 0.0)
        runbook = float(row.get("growth_runbook_pct") or 0.0)
        exception_pressure = float(row.get("exception_pressure") or 0.0)
        break_pressure = float(row.get("break_pressure") or 0.0)

        action = "GROW"
        reasons = []

        if score < policy["minimum_growth_score"]:
            action = "REVIEW"
            reasons.append("growth score below threshold")
        if runbook < policy["minimum_growth_runbook_pct"] and action in {"GROW", "REVIEW"}:
            action = "RUNBOOK"
            reasons.append("growth runbook completeness below threshold")
        if exception_pressure > policy["maximum_exception_pressure"]:
            action = "HOLD"
            reasons.append("exception pressure above threshold")
        if break_pressure > policy["maximum_break_pressure"]:
            action = "ESCALATE"
            reasons.append("break pressure above threshold")
        if not reasons:
            reasons.append("self-growing capital posture inside governed band")

        confidence = max(0.5, min(0.99, 0.99 - (exception_pressure + break_pressure) / 200.0))
        decisions.append({
            "growth_scope": row.get("growth_scope"),
            "action": action,
            "confidence": _round_pct(confidence),
            "reason": "; ".join(reasons),
            "governed_capital_millions": row.get("governed_capital_millions"),
            "growth_score": row.get("growth_score"),
        })
    return decisions

def _overview(rows: list[dict], decisions: list[dict]) -> dict:
    if not rows:
        return {
            "growth_posture": "EMPTY",
            "growth_score": 0.0,
            "grow_count": 0,
            "review_count": 0,
            "runbook_count": 0,
            "hold_count": 0,
            "escalate_count": 0,
            "governed_capital_millions": 0.0,
        }
    score = sum(float(r.get("growth_score") or 0.0) for r in rows) / len(rows)
    cap = sum(float(r.get("governed_capital_millions") or 0.0) for r in rows)
    counts = {"GROW": 0, "REVIEW": 0, "RUNBOOK": 0, "HOLD": 0, "ESCALATE": 0}
    for d in decisions:
        counts[d.get("action")] = counts.get(d.get("action"), 0) + 1
    posture = "GROWING"
    if counts["ESCALATE"] > 0:
        posture = "ESCALATED"
    elif counts["HOLD"] > 0:
        posture = "CONSTRAINED"
    elif counts["RUNBOOK"] > 0:
        posture = "RUNBOOK_REQUIRED"
    elif counts["REVIEW"] > 0:
        posture = "UNDER_REVIEW"
    return {
        "growth_posture": posture,
        "growth_score": _round_pct(score),
        "grow_count": counts["GROW"],
        "review_count": counts["REVIEW"],
        "runbook_count": counts["RUNBOOK"],
        "hold_count": counts["HOLD"],
        "escalate_count": counts["ESCALATE"],
        "governed_capital_millions": _round_money(cap),
    }

def _agenda(decisions: list[dict]) -> list[dict]:
    return [{
        "sequence": idx,
        "growth_scope": d.get("growth_scope"),
        "action": d.get("action"),
        "reason": d.get("reason"),
        "governed_capital_millions": d.get("governed_capital_millions"),
    } for idx, d in enumerate(decisions, start=1)]

def _build_summary(email: str):
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    inputs = _artifact_inputs(email)
    book = _rows(inputs, policy)
    decisions = _decisions(book, policy)
    overview = _overview(book, decisions)
    return {
        "mission": "QNT30696",
        "generated_at": _now_iso(),
        "policy": policy,
        "self_growing_capital_overview": overview,
        "growth_book": book,
        "growth_decisions": decisions,
        "growth_dependencies": {
            "autonomy_latest_run": _latest_run(inputs["autonomy"]),
            "reporting_latest_run": _latest_run(inputs["reporting"]),
            "transparency_latest_run": _latest_run(inputs["transparency"]),
            "audit_latest_run": _latest_run(inputs["audit"]),
            "routing_latest_run": _latest_run(inputs["routing"]),
            "cross_fund_latest_run": _latest_run(inputs["cross_fund"]),
            "governance_latest_run": _latest_run(inputs["governance"]),
            "committee_latest_run": _latest_run(inputs["committee"]),
            "compliance_latest_run": _latest_run(inputs["compliance"]),
            "treasury_latest_run": _latest_run(inputs["treasury"]),
            "mobility_latest_run": _latest_run(inputs["mobility"]),
        },
        "growth_agenda": _agenda(decisions),
    }

@router.get("/api/self-growing-capital-engine/summary")
def self_growing_capital_engine_summary():
    session = _require_user()
    return _build_summary(session.get("email"))

@router.post("/api/self-growing-capital-engine/run")
def self_growing_capital_engine_run(payload: dict = Body(default=None)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    summary = _build_summary(email)
    overview = summary.get("self_growing_capital_overview") or {}
    run = {
        "run_id": f"sgc_{time.time_ns()}",
        "mission": "QNT30696",
        "trigger": (payload or {}).get("trigger") or "manual",
        "timestamp": _now_ts(),
        "generated_at": summary.get("generated_at"),
        "growth_posture": overview.get("growth_posture"),
        "growth_score": overview.get("growth_score"),
        "grow_count": overview.get("grow_count"),
        "review_count": overview.get("review_count"),
        "runbook_count": overview.get("runbook_count"),
        "hold_count": overview.get("hold_count"),
        "escalate_count": overview.get("escalate_count"),
        "governed_capital_millions": overview.get("governed_capital_millions"),
    }
    store.setdefault("runs", []).insert(0, run)
    store["runs"] = store.get("runs", [])[:120]
    _save(email, store)
    return {"status": "ok", "summary": summary, "run": run}

@router.get("/api/self-growing-capital-engine/audit")
def self_growing_capital_engine_audit():
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    runs = store.get("runs") or []
    return {
        "mission": "QNT30696",
        "run_count": len(runs),
        "latest_run": runs[0] if runs else None,
        "runs": runs[:20],
        "policy": store.get("policy") or dict(DEFAULT_POLICY),
    }

@router.post("/api/self-growing-capital-engine/policy")
def self_growing_capital_engine_policy(payload: dict = Body(...)):
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
