from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["investor-transparency-engine"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
TRANSPARENCY_DIR = ARTIFACTS_DIR / "investor_transparency_engine"

DEFAULT_POLICY = {
    "minimum_transparency_score": 86.0,
    "minimum_audit_score": 80.0,
    "minimum_compliance_score": 82.0,
    "minimum_disclosure_completeness_pct": 80.0,
    "minimum_statement_coverage_pct": 75.0,
    "maximum_exception_pressure": 20.0,
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
    TRANSPARENCY_DIR.mkdir(parents=True, exist_ok=True)
    return TRANSPARENCY_DIR / f"{_safe(email)}.json"

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
        "audit": _read_json(_artifact_file("audit_regulatory_system", email), {"policy": {}, "runs": []}),
        "routing": _read_json(_artifact_file("global_capital_routing", email), {"policy": {}, "runs": []}),
        "cross_fund": _read_json(_artifact_file("cross_fund_allocation", email), {"policy": {}, "runs": []}),
        "compliance": _read_json(_artifact_file("institutional_compliance_layer", email), {"policy": {}, "runs": []}),
        "transparency": _read_json(_artifact_file("transparency_layer", email), {"policy": {}, "runs": []}),
        "statements": _read_json(_artifact_file("investor_statement_engine", email), {"policy": {}, "runs": []}),
        "identity": _read_json(_artifact_file("investor_identity_registry", email), {"investors": []}),
        "ledger": _read_json(_artifact_file("investor_capital_ledger", email), {"accounts": [], "entries": [], "allocations": []}),
        "pnl": _read_json(_artifact_file("investor_pnl_ledger", email), {"positions": [], "ledger": []}),
    }

def _rows(inputs: dict, policy: dict) -> list[dict]:
    audit_run = _latest_run(inputs["audit"])
    routing_run = _latest_run(inputs["routing"])
    xfa_run = _latest_run(inputs["cross_fund"])
    compliance_run = _latest_run(inputs["compliance"])
    transparency_run = _latest_run(inputs["transparency"])
    statements_run = _latest_run(inputs["statements"])

    investors = inputs["identity"].get("investors") or []
    ledger_entries = inputs["ledger"].get("entries") or []
    ledger_allocs = inputs["ledger"].get("allocations") or []
    pnl_ledger = inputs["pnl"].get("ledger") or []
    positions = inputs["pnl"].get("positions") or []

    investor_count = len(investors)
    ledger_capital = sum(float(a.get("amount") or a.get("capital") or a.get("allocated_amount") or 0.0) for a in ledger_allocs)
    total_mv = sum(float(p.get("market_value") or p.get("notional") or p.get("value") or 0.0) for p in positions)
    governed_capital = max(ledger_capital, total_mv)

    realized = sum(float(x.get("realized_pnl") or x.get("pnl") or 0.0) for x in pnl_ledger)
    unrealized = sum(float(p.get("unrealized_pnl") or 0.0) for p in positions)
    pnl_total = realized + unrealized
    drawdown_pct = abs(min(pnl_total, 0.0)) / max(governed_capital, 1.0) * 100.0

    audit_score = float(audit_run.get("audit_score") or 0.0)
    routing_score = float(routing_run.get("routing_score") or 0.0)
    allocation_score = float(xfa_run.get("allocation_score") or 0.0)
    compliance_score = float(compliance_run.get("release_score") or compliance_run.get("compliance_score") or 0.0)

    disclosure_signals = 0
    if transparency_run: disclosure_signals += 1
    if statements_run: disclosure_signals += 1
    if ledger_entries: disclosure_signals += 1
    if pnl_ledger: disclosure_signals += 1
    disclosure_completeness_pct = (disclosure_signals / 4.0) * 100.0

    statement_coverage_pct = 0.0
    if investor_count > 0:
        statement_coverage_pct = min(100.0, (1.0 if statements_run else 0.0) * 100.0)
    elif statements_run:
        statement_coverage_pct = 100.0

    exception_pressure = min(
        float(audit_run.get("escalate_count") or 0.0) * 5.0 +
        float(routing_run.get("escalate_count") or 0.0) * 4.0,
        30.0
    )

    break_pressure = 0.0
    if drawdown_pct > policy["maximum_drawdown_pct"]:
        break_pressure += min(6.0, (drawdown_pct - policy["maximum_drawdown_pct"]) * 0.35)
    if audit_score < policy["minimum_audit_score"]:
        break_pressure += min(6.0, (policy["minimum_audit_score"] - audit_score) * 0.30)
    if compliance_score < policy["minimum_compliance_score"]:
        break_pressure += min(6.0, (policy["minimum_compliance_score"] - compliance_score) * 0.30)
    if disclosure_completeness_pct < policy["minimum_disclosure_completeness_pct"]:
        break_pressure += min(6.0, (policy["minimum_disclosure_completeness_pct"] - disclosure_completeness_pct) * 0.12)
    if statement_coverage_pct < policy["minimum_statement_coverage_pct"]:
        break_pressure += min(6.0, (policy["minimum_statement_coverage_pct"] - statement_coverage_pct) * 0.12)

    transparency_raw = (
        audit_score * 0.24 +
        routing_score * 0.12 +
        allocation_score * 0.10 +
        compliance_score * 0.18 +
        disclosure_completeness_pct * 0.18 +
        statement_coverage_pct * 0.18
    )
    transparency_score = max(0.0, min(100.0, transparency_raw - exception_pressure - break_pressure))

    return [{
        "investor_scope": "GLOBAL_INVESTOR_TRANSPARENCY",
        "investor_count": investor_count,
        "governed_capital_millions": _round_money(governed_capital / 1_000_000.0),
        "audit_score": _round_pct(audit_score),
        "routing_score": _round_pct(routing_score),
        "allocation_score": _round_pct(allocation_score),
        "compliance_score": _round_pct(compliance_score),
        "disclosure_completeness_pct": _round_pct(disclosure_completeness_pct),
        "statement_coverage_pct": _round_pct(statement_coverage_pct),
        "drawdown_pct": _round_pct(drawdown_pct),
        "exception_pressure": _round_pct(exception_pressure),
        "break_pressure": _round_pct(break_pressure),
        "transparency_score": _round_pct(transparency_score),
    }]

def _decisions(rows: list[dict], policy: dict) -> list[dict]:
    decisions = []
    for row in rows:
        score = float(row.get("transparency_score") or 0.0)
        disclosure = float(row.get("disclosure_completeness_pct") or 0.0)
        statement_cov = float(row.get("statement_coverage_pct") or 0.0)
        exception_pressure = float(row.get("exception_pressure") or 0.0)
        break_pressure = float(row.get("break_pressure") or 0.0)

        action = "PUBLISH"
        reasons = []

        if score < policy["minimum_transparency_score"]:
            action = "REMEDIATE"
            reasons.append("transparency score below threshold")
        if disclosure < policy["minimum_disclosure_completeness_pct"] and action in {"PUBLISH", "REMEDIATE"}:
            action = "DISCLOSE"
            reasons.append("disclosure completeness below threshold")
        if statement_cov < policy["minimum_statement_coverage_pct"] and action in {"PUBLISH", "REMEDIATE", "DISCLOSE"}:
            action = "STATEMENT"
            reasons.append("statement coverage below threshold")
        if exception_pressure > policy["maximum_exception_pressure"]:
            action = "HOLD"
            reasons.append("exception pressure above threshold")
        if break_pressure > policy["maximum_break_pressure"]:
            action = "ESCALATE"
            reasons.append("break pressure above threshold")
        if not reasons:
            reasons.append("investor transparency posture inside governed band")

        confidence = max(0.5, min(0.99, 0.99 - (exception_pressure + break_pressure) / 200.0))
        decisions.append({
            "investor_scope": row.get("investor_scope"),
            "action": action,
            "confidence": _round_pct(confidence),
            "reason": "; ".join(reasons),
            "governed_capital_millions": row.get("governed_capital_millions"),
            "transparency_score": row.get("transparency_score"),
        })
    return decisions

def _overview(rows: list[dict], decisions: list[dict]) -> dict:
    if not rows:
        return {
            "transparency_posture": "EMPTY",
            "transparency_score": 0.0,
            "publish_count": 0,
            "remediate_count": 0,
            "disclose_count": 0,
            "statement_count": 0,
            "hold_count": 0,
            "escalate_count": 0,
            "governed_capital_millions": 0.0,
        }
    score = sum(float(r.get("transparency_score") or 0.0) for r in rows) / len(rows)
    cap = sum(float(r.get("governed_capital_millions") or 0.0) for r in rows)
    counts = {"PUBLISH": 0, "REMEDIATE": 0, "DISCLOSE": 0, "STATEMENT": 0, "HOLD": 0, "ESCALATE": 0}
    for d in decisions:
        counts[d.get("action")] = counts.get(d.get("action"), 0) + 1
    posture = "PUBLISHING"
    if counts["ESCALATE"] > 0:
        posture = "ESCALATED"
    elif counts["HOLD"] > 0:
        posture = "CONSTRAINED"
    elif counts["STATEMENT"] > 0:
        posture = "STATEMENT_REQUIRED"
    elif counts["DISCLOSE"] > 0:
        posture = "DISCLOSURE_REQUIRED"
    elif counts["REMEDIATE"] > 0:
        posture = "REMEDIATION_REQUIRED"
    return {
        "transparency_posture": posture,
        "transparency_score": _round_pct(score),
        "publish_count": counts["PUBLISH"],
        "remediate_count": counts["REMEDIATE"],
        "disclose_count": counts["DISCLOSE"],
        "statement_count": counts["STATEMENT"],
        "hold_count": counts["HOLD"],
        "escalate_count": counts["ESCALATE"],
        "governed_capital_millions": _round_money(cap),
    }

def _agenda(decisions: list[dict]) -> list[dict]:
    return [{
        "sequence": idx,
        "investor_scope": d.get("investor_scope"),
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
        "mission": "QNT30693",
        "generated_at": _now_iso(),
        "policy": policy,
        "investor_transparency_overview": overview,
        "transparency_book": book,
        "transparency_decisions": decisions,
        "transparency_dependencies": {
            "audit_latest_run": _latest_run(inputs["audit"]),
            "routing_latest_run": _latest_run(inputs["routing"]),
            "cross_fund_latest_run": _latest_run(inputs["cross_fund"]),
            "compliance_latest_run": _latest_run(inputs["compliance"]),
            "transparency_layer_latest_run": _latest_run(inputs["transparency"]),
            "statements_latest_run": _latest_run(inputs["statements"]),
        },
        "transparency_agenda": _agenda(decisions),
    }

@router.get("/api/investor-transparency-engine/summary")
def investor_transparency_engine_summary():
    session = _require_user()
    return _build_summary(session.get("email"))

@router.post("/api/investor-transparency-engine/run")
def investor_transparency_engine_run(payload: dict = Body(default=None)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    summary = _build_summary(email)
    overview = summary.get("investor_transparency_overview") or {}
    run = {
        "run_id": f"ite_{time.time_ns()}",
        "mission": "QNT30693",
        "trigger": (payload or {}).get("trigger") or "manual",
        "timestamp": _now_ts(),
        "generated_at": summary.get("generated_at"),
        "transparency_posture": overview.get("transparency_posture"),
        "transparency_score": overview.get("transparency_score"),
        "publish_count": overview.get("publish_count"),
        "remediate_count": overview.get("remediate_count"),
        "disclose_count": overview.get("disclose_count"),
        "statement_count": overview.get("statement_count"),
        "hold_count": overview.get("hold_count"),
        "escalate_count": overview.get("escalate_count"),
        "governed_capital_millions": overview.get("governed_capital_millions"),
    }
    store.setdefault("runs", []).insert(0, run)
    store["runs"] = store.get("runs", [])[:120]
    _save(email, store)
    return {"status": "ok", "summary": summary, "run": run}

@router.get("/api/investor-transparency-engine/audit")
def investor_transparency_engine_audit():
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    runs = store.get("runs") or []
    return {
        "mission": "QNT30693",
        "run_count": len(runs),
        "latest_run": runs[0] if runs else None,
        "runs": runs[:20],
        "policy": store.get("policy") or dict(DEFAULT_POLICY),
    }

@router.post("/api/investor-transparency-engine/policy")
def investor_transparency_engine_policy(payload: dict = Body(...)):
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
