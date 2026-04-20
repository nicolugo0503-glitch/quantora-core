from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["live-allocation-remediation-command"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
REMEDIATION_DIR = ARTIFACTS_DIR / "live_allocation_remediation_command"

DEFAULT_POLICY = {
    "minimum_remediation_score": 84.0,
    "minimum_exception_governance_score": 82.0,
    "minimum_oversight_score": 80.0,
    "minimum_continuity_score": 76.0,
    "minimum_governance_score": 78.0,
    "minimum_compliance_score": 78.0,
    "maximum_exception_pressure": 24.0,
    "maximum_break_pressure": 18.0,
    "maximum_backlog_pressure": 18.0,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]


def _artifact_file(folder: str, email: str) -> Path:
    return ARTIFACTS_DIR / folder / f"{_safe(email)}.json"


def _path(email: str) -> Path:
    REMEDIATION_DIR.mkdir(parents=True, exist_ok=True)
    return REMEDIATION_DIR / f"{_safe(email)}.json"


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
        "exception": _read_json(_artifact_file("live_allocation_exception_governance_layer", email), {"policy": {}, "runs": []}),
        "oversight": _read_json(_artifact_file("live_allocation_post_close_oversight_layer", email), {"policy": {}, "runs": []}),
        "close": _read_json(_artifact_file("live_allocation_close_authority", email), {"policy": {}, "runs": []}),
        "reconciliation": _read_json(_artifact_file("live_allocation_reconciliation_command", email), {"policy": {}, "runs": []}),
        "settlement": _read_json(_artifact_file("live_allocation_settlement_command", email), {"policy": {}, "runs": []}),
        "finalization": _read_json(_artifact_file("live_allocation_finalization_authority", email), {"policy": {}, "runs": []}),
        "continuity": _read_json(_artifact_file("live_allocation_continuity_command", email), {"policy": {}, "runs": []}),
        "clearance": _read_json(_artifact_file("live_allocation_clearance_grid", email), {"policy": {}, "runs": []}),
        "release": _read_json(_artifact_file("live_allocation_release_authority_mesh", email), {"policy": {}, "runs": []}),
        "dispatch": _read_json(_artifact_file("capital_dispatch_supervision_layer", email), {"policy": {}, "runs": []}),
        "governance": _read_json(_artifact_file("execution_governance_command", email), {"policy": {}, "runs": []}),
        "committee": _read_json(_artifact_file("capital_committee_oversight_mesh", email), {"policy": {}, "runs": []}),
        "compliance": _read_json(_artifact_file("institutional_compliance_layer", email), {"policy": {}, "runs": []}),
        "ledger": _read_json(_artifact_file("investor_capital_ledger", email), {"accounts": [], "entries": [], "allocations": []}),
        "pnl": _read_json(_artifact_file("investor_pnl_ledger", email), {"positions": [], "ledger": []}),
        "execution": _read_json(_artifact_file("strategy_execution_engine", email), {"strategy_allocations": [], "trades": [], "history": []}),
        "broker": _read_json(_artifact_file("broker_integration", email), {"brokers": [], "routes": [], "accounts": []}),
        "onboarding": _read_json(_artifact_file("investor_onboarding_pipeline", email), {"investors": [], "subscriptions": []}),
    }


def _remediation_rows(inputs: dict, policy: dict) -> list[dict]:
    exception_run = _latest_run(inputs["exception"])
    oversight_run = _latest_run(inputs["oversight"])
    close_run = _latest_run(inputs["close"])
    reconciliation_run = _latest_run(inputs["reconciliation"])
    settlement_run = _latest_run(inputs["settlement"])
    continuity_run = _latest_run(inputs["continuity"])
    governance_run = _latest_run(inputs["governance"])
    compliance_run = _latest_run(inputs["compliance"])

    allocations = inputs["execution"].get("strategy_allocations") or []
    positions = inputs["pnl"].get("positions") or []
    pnl_ledger = inputs["pnl"].get("ledger") or []
    broker_routes = inputs["broker"].get("routes") or []
    subscriptions = inputs["onboarding"].get("subscriptions") or []

    total_capital = sum(float(a.get("allocated_amount") or a.get("allocation_amount") or a.get("capital") or 0.0) for a in allocations)
    total_mv = sum(float(p.get("market_value") or p.get("notional") or p.get("value") or 0.0) for p in positions)
    governed_capital = max(total_capital, total_mv)
    active_strategies = max(len(allocations), 1)

    realized = sum(float(x.get("realized_pnl") or x.get("pnl") or 0.0) for x in pnl_ledger)
    unrealized = sum(float(p.get("unrealized_pnl") or 0.0) for p in positions)
    pnl_total = realized + unrealized

    exception_score = float(exception_run.get("exception_governance_score") or 0.0)
    oversight_score = float(oversight_run.get("oversight_score") or 0.0)
    close_score = float(close_run.get("close_score") or 0.0)
    reconciliation_score = float(reconciliation_run.get("reconciliation_score") or 0.0)
    settlement_score = float(settlement_run.get("settlement_score") or 0.0)
    continuity_score = float(continuity_run.get("continuity_score") or 0.0)
    governance_score = float(governance_run.get("governance_score") or governance_run.get("supervisory_score") or 0.0)
    compliance_score = float(compliance_run.get("release_score") or compliance_run.get("compliance_score") or 0.0)

    exception_pressure = float(exception_run.get("exception_pressure") or 0.0)
    break_pressure = float(exception_run.get("break_pressure") or 0.0)
    backlog_pressure = 0.0
    if exception_run.get("review_count", 0):
        backlog_pressure += 5.0
    if oversight_run.get("review_count", 0):
        backlog_pressure += 4.0
    if close_run.get("review_count", 0):
        backlog_pressure += 4.0
    if reconciliation_run.get("review_count", 0):
        backlog_pressure += 3.0
    if settlement_run.get("review_count", 0):
        backlog_pressure += 3.0
    if not broker_routes:
        backlog_pressure += 3.0
    if not subscriptions:
        backlog_pressure += 3.0

    docs_gap = 0.0
    if not broker_routes:
        docs_gap += 2.0
    if not subscriptions:
        docs_gap += 2.0
    if not positions and not allocations:
        docs_gap += 4.0

    remediation_raw = (
        exception_score * 0.22
        + oversight_score * 0.16
        + close_score * 0.12
        + reconciliation_score * 0.12
        + settlement_score * 0.10
        + continuity_score * 0.10
        + governance_score * 0.09
        + compliance_score * 0.09
    )
    remediation_score = max(0.0, min(100.0, remediation_raw - exception_pressure - break_pressure - backlog_pressure - docs_gap))

    return [{
        "portfolio_id": "LIVE_ALLOCATION_REMEDIATION_BOOK",
        "governed_capital_millions": _round_money(governed_capital / 1_000_000.0),
        "active_strategies": active_strategies,
        "exception_governance_score": _round_pct(exception_score),
        "oversight_score": _round_pct(oversight_score),
        "close_score": _round_pct(close_score),
        "reconciliation_score": _round_pct(reconciliation_score),
        "settlement_score": _round_pct(settlement_score),
        "continuity_score": _round_pct(continuity_score),
        "governance_score": _round_pct(governance_score),
        "compliance_score": _round_pct(compliance_score),
        "exception_pressure": _round_pct(exception_pressure),
        "break_pressure": _round_pct(break_pressure),
        "backlog_pressure": _round_pct(backlog_pressure),
        "documentation_gap": _round_pct(docs_gap),
        "remediation_score": _round_pct(remediation_score),
        "pnl_total": _round_money(pnl_total),
        "latest_exception_action": exception_run.get("exception_governance_posture") or exception_run.get("action"),
        "latest_oversight_action": oversight_run.get("oversight_posture") or oversight_run.get("action"),
        "latest_close_action": close_run.get("close_posture") or close_run.get("action"),
        "latest_reconciliation_action": reconciliation_run.get("reconciliation_posture") or reconciliation_run.get("action"),
        "latest_settlement_action": settlement_run.get("settlement_posture") or settlement_run.get("action"),
        "latest_continuity_action": continuity_run.get("continuity_posture") or continuity_run.get("action"),
    }]


def _decisions(rows: list[dict], policy: dict) -> list[dict]:
    decisions = []
    for row in rows:
        reasons = []
        action = "REMEDIATE"
        score = float(row.get("remediation_score") or 0.0)
        exception_pressure = float(row.get("exception_pressure") or 0.0)
        break_pressure = float(row.get("break_pressure") or 0.0)
        backlog_pressure = float(row.get("backlog_pressure") or 0.0)
        docs_gap = float(row.get("documentation_gap") or 0.0)

        if score < policy["minimum_remediation_score"]:
            action = "REVIEW"
            reasons.append("remediation score below threshold")
        if backlog_pressure > policy["maximum_backlog_pressure"]:
            action = "HOLD"
            reasons.append("backlog pressure above threshold")
        if exception_pressure > policy["maximum_exception_pressure"] or break_pressure > policy["maximum_break_pressure"]:
            action = "ESCALATE"
            reasons.append("exception or break pressure above threshold")
        if float(row.get("governance_score") or 0.0) < policy["minimum_governance_score"]:
            action = "ESCALATE"
            reasons.append("governance posture below threshold")
        if float(row.get("compliance_score") or 0.0) < policy["minimum_compliance_score"]:
            action = "ESCALATE"
            reasons.append("compliance posture below threshold")
        if docs_gap >= 4.0 and action == "REMEDIATE":
            action = "REVIEW"
            reasons.append("documentation completion gap detected")
        if not reasons:
            reasons.append("remediation posture inside governed band")

        confidence = max(0.5, min(0.99, 0.99 - (exception_pressure + break_pressure + backlog_pressure + docs_gap) / 220.0))
        decisions.append({
            "portfolio_id": row.get("portfolio_id"),
            "action": action,
            "confidence": _round_pct(confidence),
            "reason": "; ".join(reasons),
            "governed_capital_millions": row.get("governed_capital_millions"),
            "remediation_score": row.get("remediation_score"),
        })
    return decisions


def _overview(rows: list[dict], decisions: list[dict]) -> dict:
    if not rows:
        return {
            "remediation_posture": "EMPTY",
            "remediation_score": 0.0,
            "remediate_count": 0,
            "review_count": 0,
            "hold_count": 0,
            "escalate_count": 0,
            "governed_capital_millions": 0.0,
        }
    score = sum(float(r.get("remediation_score") or 0.0) for r in rows) / len(rows)
    cap = sum(float(r.get("governed_capital_millions") or 0.0) for r in rows)
    counts = {"REMEDIATE": 0, "REVIEW": 0, "HOLD": 0, "ESCALATE": 0}
    for d in decisions:
        counts[d.get("action")] = counts.get(d.get("action"), 0) + 1
    posture = "CONTROLLED"
    if counts["ESCALATE"] > 0:
        posture = "ESCALATED"
    elif counts["HOLD"] > 0:
        posture = "CONSTRAINED"
    elif counts["REVIEW"] > 0:
        posture = "UNDER_REMEDIATION_REVIEW"
    return {
        "remediation_posture": posture,
        "remediation_score": _round_pct(score),
        "remediate_count": counts["REMEDIATE"],
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
            "governed_capital_millions": d.get("governed_capital_millions"),
        })
    return agenda


def _build_summary(email: str):
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    inputs = _artifact_inputs(email)
    remediation_book = _remediation_rows(inputs, policy)
    remediation_decisions = _decisions(remediation_book, policy)
    overview = _overview(remediation_book, remediation_decisions)
    return {
        "mission": "QNT30679",
        "generated_at": _now_iso(),
        "policy": policy,
        "live_allocation_remediation_overview": overview,
        "remediation_book": remediation_book,
        "remediation_decisions": remediation_decisions,
        "remediation_dependencies": {
            "exception_latest_run": _latest_run(inputs["exception"]),
            "oversight_latest_run": _latest_run(inputs["oversight"]),
            "close_latest_run": _latest_run(inputs["close"]),
            "reconciliation_latest_run": _latest_run(inputs["reconciliation"]),
            "settlement_latest_run": _latest_run(inputs["settlement"]),
            "continuity_latest_run": _latest_run(inputs["continuity"]),
            "governance_latest_run": _latest_run(inputs["governance"]),
            "committee_latest_run": _latest_run(inputs["committee"]),
            "compliance_latest_run": _latest_run(inputs["compliance"]),
        },
        "remediation_agenda": _agenda(remediation_decisions),
    }


@router.get("/api/live-allocation-remediation-command/summary")
def live_allocation_remediation_summary():
    session = _require_user()
    return _build_summary(session.get("email"))


@router.post("/api/live-allocation-remediation-command/run")
def live_allocation_remediation_run(payload: dict = Body(default=None)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    summary = _build_summary(email)
    overview = summary.get("live_allocation_remediation_overview") or {}
    run = {
        "run_id": f"larc_{time.time_ns()}",
        "mission": "QNT30679",
        "trigger": (payload or {}).get("trigger") or "manual",
        "timestamp": _now_ts(),
        "generated_at": summary.get("generated_at"),
        "remediation_posture": overview.get("remediation_posture"),
        "remediation_score": overview.get("remediation_score"),
        "remediate_count": overview.get("remediate_count"),
        "review_count": overview.get("review_count"),
        "hold_count": overview.get("hold_count"),
        "escalate_count": overview.get("escalate_count"),
        "governed_capital_millions": overview.get("governed_capital_millions"),
    }
    store.setdefault("runs", []).insert(0, run)
    store["runs"] = store.get("runs", [])[:120]
    _save(email, store)
    return {"status": "ok", "summary": summary, "run": run}


@router.get("/api/live-allocation-remediation-command/audit")
def live_allocation_remediation_audit():
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    runs = store.get("runs") or []
    return {
        "mission": "QNT30679",
        "run_count": len(runs),
        "latest_run": runs[0] if runs else None,
        "runs": runs[:20],
        "policy": store.get("policy") or dict(DEFAULT_POLICY),
    }


@router.post("/api/live-allocation-remediation-command/policy")
def live_allocation_remediation_policy(payload: dict = Body(...)):
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
