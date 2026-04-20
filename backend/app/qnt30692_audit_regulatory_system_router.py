from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["audit-regulatory-system"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
AUDIT_DIR = ARTIFACTS_DIR / "audit_regulatory_system"

DEFAULT_POLICY = {
    "minimum_audit_score": 86.0,
    "minimum_routing_score": 78.0,
    "minimum_allocation_score": 78.0,
    "minimum_orchestration_score": 78.0,
    "minimum_governance_score": 80.0,
    "minimum_compliance_score": 82.0,
    "maximum_exception_pressure": 20.0,
    "maximum_break_pressure": 18.0,
    "maximum_drawdown_pct": 14.0,
    "minimum_disclosure_completeness_pct": 75.0,
}

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _artifact_file(folder: str, email: str) -> Path:
    return ARTIFACTS_DIR / folder / f"{_safe(email)}.json"

def _path(email: str) -> Path:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    return AUDIT_DIR / f"{_safe(email)}.json"

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
        "routing": _read_json(_artifact_file("global_capital_routing", email), {"policy": {}, "runs": []}),
        "cross_fund": _read_json(_artifact_file("cross_fund_allocation", email), {"policy": {}, "runs": []}),
        "orchestration": _read_json(_artifact_file("multi_fund_orchestration", email), {"policy": {}, "runs": []}),
        "brain": _read_json(_artifact_file("portfolio_intelligence_brain", email), {"policy": {}, "runs": []}),
        "selection": _read_json(_artifact_file("strategy_selection_ai", email), {"policy": {}, "runs": []}),
        "governance": _read_json(_artifact_file("execution_governance_command", email), {"policy": {}, "runs": []}),
        "committee": _read_json(_artifact_file("capital_committee_oversight_mesh", email), {"policy": {}, "runs": []}),
        "compliance": _read_json(_artifact_file("institutional_compliance_layer", email), {"policy": {}, "runs": []}),
        "transparency": _read_json(_artifact_file("transparency_layer", email), {"policy": {}, "runs": []}),
        "statements": _read_json(_artifact_file("investor_statement_engine", email), {"policy": {}, "runs": []}),
        "ledger": _read_json(_artifact_file("investor_capital_ledger", email), {"accounts": [], "entries": [], "allocations": []}),
        "pnl": _read_json(_artifact_file("investor_pnl_ledger", email), {"positions": [], "ledger": []}),
    }

def _rows(inputs: dict, policy: dict) -> list[dict]:
    routing_run = _latest_run(inputs["routing"])
    xfa_run = _latest_run(inputs["cross_fund"])
    orch_run = _latest_run(inputs["orchestration"])
    brain_run = _latest_run(inputs["brain"])
    selection_run = _latest_run(inputs["selection"])
    governance_run = _latest_run(inputs["governance"])
    committee_run = _latest_run(inputs["committee"])
    compliance_run = _latest_run(inputs["compliance"])
    transparency_run = _latest_run(inputs["transparency"])
    statements_run = _latest_run(inputs["statements"])
    ledger_entries = inputs["ledger"].get("entries") or []
    ledger_allocs = inputs["ledger"].get("allocations") or []
    pnl_ledger = inputs["pnl"].get("ledger") or []
    positions = inputs["pnl"].get("positions") or []

    ledger_capital = sum(float(a.get("amount") or a.get("capital") or a.get("allocated_amount") or 0.0) for a in ledger_allocs)
    total_mv = sum(float(p.get("market_value") or p.get("notional") or p.get("value") or 0.0) for p in positions)
    governed_capital = max(ledger_capital, total_mv)
    realized = sum(float(x.get("realized_pnl") or x.get("pnl") or 0.0) for x in pnl_ledger)
    unrealized = sum(float(p.get("unrealized_pnl") or 0.0) for p in positions)
    pnl_total = realized + unrealized
    drawdown_pct = abs(min(pnl_total, 0.0)) / max(governed_capital, 1.0) * 100.0

    routing_score = float(routing_run.get("routing_score") or 0.0)
    allocation_score = float(xfa_run.get("allocation_score") or 0.0)
    orchestration_score = float(orch_run.get("orchestration_score") or 0.0)
    brain_score = float(brain_run.get("brain_score") or 0.0)
    selection_score = float(selection_run.get("selection_score") or 0.0)
    governance_score = float(governance_run.get("governance_score") or governance_run.get("supervisory_score") or 0.0)
    compliance_score = float(compliance_run.get("release_score") or compliance_run.get("compliance_score") or 0.0)

    disclosure_signals = 0
    if transparency_run: disclosure_signals += 1
    if statements_run: disclosure_signals += 1
    if ledger_entries: disclosure_signals += 1
    if pnl_ledger: disclosure_signals += 1
    disclosure_completeness_pct = (disclosure_signals / 4.0) * 100.0

    exception_pressure = min(
        float(routing_run.get("escalate_count") or 0.0) * 5.0 +
        float(xfa_run.get("escalate_count") or 0.0) * 4.0 +
        float(committee_run.get("escalate_count") or committee_run.get("review_count") or 0.0) * 2.0,
        30.0
    )

    break_pressure = 0.0
    if drawdown_pct > policy["maximum_drawdown_pct"]:
        break_pressure += min(6.0, (drawdown_pct - policy["maximum_drawdown_pct"]) * 0.35)
    if routing_score < policy["minimum_routing_score"]:
        break_pressure += min(5.0, (policy["minimum_routing_score"] - routing_score) * 0.30)
    if allocation_score < policy["minimum_allocation_score"]:
        break_pressure += min(5.0, (policy["minimum_allocation_score"] - allocation_score) * 0.30)
    if orchestration_score < policy["minimum_orchestration_score"]:
        break_pressure += min(5.0, (policy["minimum_orchestration_score"] - orchestration_score) * 0.30)
    if governance_score < policy["minimum_governance_score"]:
        break_pressure += min(5.0, (policy["minimum_governance_score"] - governance_score) * 0.30)
    if compliance_score < policy["minimum_compliance_score"]:
        break_pressure += min(6.0, (policy["minimum_compliance_score"] - compliance_score) * 0.30)
    if disclosure_completeness_pct < policy["minimum_disclosure_completeness_pct"]:
        break_pressure += min(6.0, (policy["minimum_disclosure_completeness_pct"] - disclosure_completeness_pct) * 0.12)

    audit_raw = (
        routing_score * 0.16 +
        allocation_score * 0.14 +
        orchestration_score * 0.12 +
        brain_score * 0.10 +
        selection_score * 0.08 +
        governance_score * 0.16 +
        compliance_score * 0.16 +
        disclosure_completeness_pct * 0.08
    )
    audit_score = max(0.0, min(100.0, audit_raw - exception_pressure - break_pressure))

    return [{
        "audit_scope": "GLOBAL_CAPITAL_AUDIT",
        "governed_capital_millions": _round_money(governed_capital / 1_000_000.0),
        "ledger_entry_count": len(ledger_entries),
        "pnl_entry_count": len(pnl_ledger),
        "routing_score": _round_pct(routing_score),
        "allocation_score": _round_pct(allocation_score),
        "orchestration_score": _round_pct(orchestration_score),
        "brain_score": _round_pct(brain_score),
        "selection_score": _round_pct(selection_score),
        "governance_score": _round_pct(governance_score),
        "compliance_score": _round_pct(compliance_score),
        "disclosure_completeness_pct": _round_pct(disclosure_completeness_pct),
        "drawdown_pct": _round_pct(drawdown_pct),
        "exception_pressure": _round_pct(exception_pressure),
        "break_pressure": _round_pct(break_pressure),
        "audit_score": _round_pct(audit_score),
    }]

def _decisions(rows: list[dict], policy: dict) -> list[dict]:
    decisions = []
    for row in rows:
        score = float(row.get("audit_score") or 0.0)
        disclosure = float(row.get("disclosure_completeness_pct") or 0.0)
        exception_pressure = float(row.get("exception_pressure") or 0.0)
        break_pressure = float(row.get("break_pressure") or 0.0)

        action = "AUDIT"
        reasons = []
        if score < policy["minimum_audit_score"]:
            action = "REMEDIATE"
            reasons.append("audit score below threshold")
        if disclosure < policy["minimum_disclosure_completeness_pct"] and action in {"AUDIT", "REMEDIATE"}:
            action = "DISCLOSE"
            reasons.append("disclosure completeness below threshold")
        if exception_pressure > policy["maximum_exception_pressure"]:
            action = "HOLD"
            reasons.append("exception pressure above threshold")
        if break_pressure > policy["maximum_break_pressure"]:
            action = "ESCALATE"
            reasons.append("break pressure above threshold")
        if not reasons:
            reasons.append("audit posture inside governed band")
        confidence = max(0.5, min(0.99, 0.99 - (exception_pressure + break_pressure) / 200.0))
        decisions.append({
            "audit_scope": row.get("audit_scope"),
            "action": action,
            "confidence": _round_pct(confidence),
            "reason": "; ".join(reasons),
            "governed_capital_millions": row.get("governed_capital_millions"),
            "audit_score": row.get("audit_score"),
        })
    return decisions

def _overview(rows: list[dict], decisions: list[dict]) -> dict:
    if not rows:
        return {"audit_posture":"EMPTY","audit_score":0.0,"audit_count":0,"remediate_count":0,"disclose_count":0,"hold_count":0,"escalate_count":0,"governed_capital_millions":0.0}
    score = sum(float(r.get("audit_score") or 0.0) for r in rows) / len(rows)
    cap = sum(float(r.get("governed_capital_millions") or 0.0) for r in rows)
    counts = {"AUDIT":0,"REMEDIATE":0,"DISCLOSE":0,"HOLD":0,"ESCALATE":0}
    for d in decisions:
        counts[d.get("action")] = counts.get(d.get("action"), 0) + 1
    posture = "AUDITED"
    if counts["ESCALATE"] > 0:
        posture = "ESCALATED"
    elif counts["HOLD"] > 0:
        posture = "CONSTRAINED"
    elif counts["DISCLOSE"] > 0:
        posture = "DISCLOSURE_REQUIRED"
    elif counts["REMEDIATE"] > 0:
        posture = "REMEDIATION_REQUIRED"
    return {
        "audit_posture": posture,
        "audit_score": _round_pct(score),
        "audit_count": counts["AUDIT"],
        "remediate_count": counts["REMEDIATE"],
        "disclose_count": counts["DISCLOSE"],
        "hold_count": counts["HOLD"],
        "escalate_count": counts["ESCALATE"],
        "governed_capital_millions": _round_money(cap),
    }

def _agenda(decisions: list[dict]) -> list[dict]:
    return [{
        "sequence": idx,
        "audit_scope": d.get("audit_scope"),
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
        "mission": "QNT30692",
        "generated_at": _now_iso(),
        "policy": policy,
        "audit_regulatory_overview": overview,
        "audit_book": book,
        "audit_decisions": decisions,
        "audit_dependencies": {
            "routing_latest_run": _latest_run(inputs["routing"]),
            "cross_fund_latest_run": _latest_run(inputs["cross_fund"]),
            "orchestration_latest_run": _latest_run(inputs["orchestration"]),
            "brain_latest_run": _latest_run(inputs["brain"]),
            "selection_latest_run": _latest_run(inputs["selection"]),
            "governance_latest_run": _latest_run(inputs["governance"]),
            "committee_latest_run": _latest_run(inputs["committee"]),
            "compliance_latest_run": _latest_run(inputs["compliance"]),
            "transparency_latest_run": _latest_run(inputs["transparency"]),
            "statements_latest_run": _latest_run(inputs["statements"]),
        },
        "audit_agenda": _agenda(decisions),
    }

@router.get("/api/audit-regulatory-system/summary")
def audit_regulatory_system_summary():
    session = _require_user()
    return _build_summary(session.get("email"))

@router.post("/api/audit-regulatory-system/run")
def audit_regulatory_system_run(payload: dict = Body(default=None)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    summary = _build_summary(email)
    overview = summary.get("audit_regulatory_overview") or {}
    run = {
        "run_id": f"ars_{time.time_ns()}",
        "mission": "QNT30692",
        "trigger": (payload or {}).get("trigger") or "manual",
        "timestamp": _now_ts(),
        "generated_at": summary.get("generated_at"),
        "audit_posture": overview.get("audit_posture"),
        "audit_score": overview.get("audit_score"),
        "audit_count": overview.get("audit_count"),
        "remediate_count": overview.get("remediate_count"),
        "disclose_count": overview.get("disclose_count"),
        "hold_count": overview.get("hold_count"),
        "escalate_count": overview.get("escalate_count"),
        "governed_capital_millions": overview.get("governed_capital_millions"),
    }
    store.setdefault("runs", []).insert(0, run)
    store["runs"] = store.get("runs", [])[:120]
    _save(email, store)
    return {"status": "ok", "summary": summary, "run": run}

@router.get("/api/audit-regulatory-system/audit")
def audit_regulatory_system_audit():
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    runs = store.get("runs") or []
    return {
        "mission": "QNT30692",
        "run_count": len(runs),
        "latest_run": runs[0] if runs else None,
        "runs": runs[:20],
        "policy": store.get("policy") or dict(DEFAULT_POLICY),
    }

@router.post("/api/audit-regulatory-system/policy")
def audit_regulatory_system_policy(payload: dict = Body(...)):
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
