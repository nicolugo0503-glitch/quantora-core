from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["live-allocation-exception-governance-layer"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
EXCEPTION_DIR = ARTIFACTS_DIR / "live_allocation_exception_governance_layer"

DEFAULT_POLICY = {
    "minimum_exception_governance_score": 86.0,
    "minimum_oversight_score": 84.0,
    "minimum_close_score": 84.0,
    "minimum_reconciliation_score": 82.0,
    "minimum_settlement_score": 82.0,
    "minimum_continuity_score": 78.0,
    "minimum_governance_score": 80.0,
    "minimum_compliance_score": 80.0,
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
    EXCEPTION_DIR.mkdir(parents=True, exist_ok=True)
    return EXCEPTION_DIR / f"{_safe(email)}.json"


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
        "identity": _read_json(_artifact_file("investor_identity_registry", email), {"investors": []}),
        "onboarding": _read_json(_artifact_file("investor_onboarding_pipeline", email), {"investors": [], "subscriptions": []}),
    }


def _exception_rows(inputs: dict, policy: dict) -> list[dict]:
    oversight_run = _latest_run(inputs["oversight"])
    close_run = _latest_run(inputs["close"])
    reconciliation_run = _latest_run(inputs["reconciliation"])
    settlement_run = _latest_run(inputs["settlement"])
    finalization_run = _latest_run(inputs["finalization"])
    continuity_run = _latest_run(inputs["continuity"])
    clearance_run = _latest_run(inputs["clearance"])
    release_run = _latest_run(inputs["release"])
    dispatch_run = _latest_run(inputs["dispatch"])
    governance_run = _latest_run(inputs["governance"])
    committee_run = _latest_run(inputs["committee"])
    compliance_run = _latest_run(inputs["compliance"])

    allocations = inputs["execution"].get("strategy_allocations") or []
    positions = inputs["pnl"].get("positions") or []
    pnl_ledger = inputs["pnl"].get("ledger") or []
    subscriptions = inputs["onboarding"].get("subscriptions") or []
    broker_routes = inputs["broker"].get("routes") or []

    total_capital = sum(float(a.get("allocated_amount") or a.get("allocation_amount") or a.get("capital") or 0.0) for a in allocations)
    total_mv = sum(float(p.get("market_value") or p.get("notional") or p.get("value") or 0.0) for p in positions)
    total_exposure = max(total_capital, total_mv)
    active_strategies = max(len(allocations), 1)

    realized = sum(float(x.get("realized_pnl") or x.get("pnl") or 0.0) for x in pnl_ledger)
    unrealized = sum(float(p.get("unrealized_pnl") or 0.0) for p in positions)
    pnl_total = realized + unrealized

    oversight_score = float(oversight_run.get("oversight_score") or 0.0)
    close_score = float(close_run.get("close_score") or 0.0)
    reconciliation_score = float(reconciliation_run.get("reconciliation_score") or 0.0)
    settlement_score = float(settlement_run.get("settlement_score") or 0.0)
    continuity_score = float(continuity_run.get("continuity_score") or 0.0)
    governance_score = float(governance_run.get("governance_score") or governance_run.get("supervisory_score") or 0.0)
    compliance_score = float(compliance_run.get("release_score") or compliance_run.get("compliance_score") or 0.0)

    exception_pressure = 0.0
    break_pressure = 0.0

    if oversight_run.get("escalate_count", 0):
        exception_pressure += 8.0
    if close_run.get("escalate_count", 0):
        exception_pressure += 7.0
    if reconciliation_run.get("escalate_count", 0):
        exception_pressure += 6.0
    if settlement_run.get("escalate_count", 0):
        exception_pressure += 6.0
    if continuity_run.get("review_count", 0):
        exception_pressure += 4.0
    if governance_run.get("halt_count", 0):
        exception_pressure += 9.0
    if compliance_run.get("hold_count", 0):
        exception_pressure += 7.0

    if close_score < policy["minimum_close_score"]:
        break_pressure += min(6.0, (policy["minimum_close_score"] - close_score) * 0.35)
    if reconciliation_score < policy["minimum_reconciliation_score"]:
        break_pressure += min(6.0, (policy["minimum_reconciliation_score"] - reconciliation_score) * 0.35)
    if settlement_score < policy["minimum_settlement_score"]:
        break_pressure += min(5.0, (policy["minimum_settlement_score"] - settlement_score) * 0.30)
    if continuity_score < policy["minimum_continuity_score"]:
        break_pressure += min(4.0, (policy["minimum_continuity_score"] - continuity_score) * 0.25)
    if oversight_score < policy["minimum_oversight_score"]:
        break_pressure += min(5.0, (policy["minimum_oversight_score"] - oversight_score) * 0.30)
    if governance_score < policy["minimum_governance_score"]:
        break_pressure += min(5.0, (policy["minimum_governance_score"] - governance_score) * 0.30)
    if compliance_score < policy["minimum_compliance_score"]:
        break_pressure += min(5.0, (policy["minimum_compliance_score"] - compliance_score) * 0.30)

    docs_gap = 0.0
    if not subscriptions:
        docs_gap += 3.0
    if not broker_routes:
        docs_gap += 3.0
    if not positions and not allocations:
        docs_gap += 4.0

    governance_raw = (
        oversight_score * 0.18
        + close_score * 0.14
        + reconciliation_score * 0.14
        + settlement_score * 0.12
        + continuity_score * 0.12
        + governance_score * 0.12
        + compliance_score * 0.12
        + max(0.0, 100.0 - min(abs(pnl_total) / max(total_exposure, 1.0) * 100.0 * 3.0, 20.0)) * 0.06
    )
    exception_governance_score = max(0.0, min(100.0, governance_raw - exception_pressure - break_pressure - docs_gap))

    return [{
        "portfolio_id": "LIVE_ALLOCATION_EXCEPTION_BOOK",
        "capital_millions": _round_money(total_exposure / 1_000_000.0),
        "active_strategies": active_strategies,
        "oversight_score": _round_pct(oversight_score),
        "close_score": _round_pct(close_score),
        "reconciliation_score": _round_pct(reconciliation_score),
        "settlement_score": _round_pct(settlement_score),
        "continuity_score": _round_pct(continuity_score),
        "governance_score": _round_pct(governance_score),
        "compliance_score": _round_pct(compliance_score),
        "exception_pressure": _round_pct(exception_pressure),
        "break_pressure": _round_pct(break_pressure),
        "documentation_gap": _round_pct(docs_gap),
        "exception_governance_score": _round_pct(exception_governance_score),
        "pnl_total": _round_money(pnl_total),
        "latest_close_action": close_run.get("close_posture") or close_run.get("action"),
        "latest_settlement_action": settlement_run.get("settlement_posture") or settlement_run.get("action"),
        "latest_reconciliation_action": reconciliation_run.get("reconciliation_posture") or reconciliation_run.get("action"),
        "latest_oversight_action": oversight_run.get("oversight_posture") or oversight_run.get("action"),
        "latest_continuity_action": continuity_run.get("continuity_posture") or continuity_run.get("action"),
        "latest_governance_action": governance_run.get("governance_posture") or governance_run.get("action"),
        "latest_compliance_action": compliance_run.get("compliance_posture") or compliance_run.get("action"),
    }]


def _decisions(rows: list[dict], policy: dict) -> list[dict]:
    decisions = []
    for row in rows:
        reasons = []
        action = "RESOLVE"
        score = float(row.get("exception_governance_score") or 0.0)
        exception_pressure = float(row.get("exception_pressure") or 0.0)
        break_pressure = float(row.get("break_pressure") or 0.0)
        docs_gap = float(row.get("documentation_gap") or 0.0)

        if score < policy["minimum_exception_governance_score"]:
            action = "REVIEW"
            reasons.append("exception governance score below threshold")
        if exception_pressure > policy["maximum_exception_pressure"]:
            action = "HOLD"
            reasons.append("exception pressure above threshold")
        if break_pressure > policy["maximum_break_pressure"]:
            action = "ESCALATE"
            reasons.append("break pressure above threshold")
        if float(row.get("compliance_score") or 0.0) < policy["minimum_compliance_score"]:
            action = "ESCALATE"
            reasons.append("compliance posture below threshold")
        if float(row.get("governance_score") or 0.0) < policy["minimum_governance_score"]:
            action = "ESCALATE"
            reasons.append("governance posture below threshold")
        if docs_gap >= 4.0 and action == "RESOLVE":
            action = "REVIEW"
            reasons.append("documentation completion gap detected")
        if not reasons:
            reasons.append("exception posture inside governed band")

        confidence = max(0.5, min(0.99, 0.99 - (exception_pressure + break_pressure + docs_gap) / 200.0))
        decisions.append({
            "portfolio_id": row.get("portfolio_id"),
            "action": action,
            "confidence": _round_pct(confidence),
            "reason": "; ".join(reasons),
            "capital_millions": row.get("capital_millions"),
            "exception_governance_score": row.get("exception_governance_score"),
        })
    return decisions


def _overview(rows: list[dict], decisions: list[dict]) -> dict:
    if not rows:
        return {
            "exception_governance_posture": "EMPTY",
            "exception_governance_score": 0.0,
            "resolve_count": 0,
            "review_count": 0,
            "hold_count": 0,
            "escalate_count": 0,
            "governed_capital_millions": 0.0,
        }
    score = sum(float(r.get("exception_governance_score") or 0.0) for r in rows) / len(rows)
    cap = sum(float(r.get("capital_millions") or 0.0) for r in rows)
    counts = {"RESOLVE": 0, "REVIEW": 0, "HOLD": 0, "ESCALATE": 0}
    for d in decisions:
        counts[d.get("action")] = counts.get(d.get("action"), 0) + 1
    posture = "CONTROLLED"
    if counts["ESCALATE"] > 0:
        posture = "ESCALATED"
    elif counts["HOLD"] > 0:
        posture = "CONSTRAINED"
    elif counts["REVIEW"] > 0:
        posture = "UNDER_REVIEW"
    return {
        "exception_governance_posture": posture,
        "exception_governance_score": _round_pct(score),
        "resolve_count": counts["RESOLVE"],
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
            "capital_millions": d.get("capital_millions"),
        })
    return agenda


def _build_summary(email: str):
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    inputs = _artifact_inputs(email)
    exception_book = _exception_rows(inputs, policy)
    exception_decisions = _decisions(exception_book, policy)
    overview = _overview(exception_book, exception_decisions)
    return {
        "mission": "QNT30678",
        "generated_at": _now_iso(),
        "policy": policy,
        "live_allocation_exception_governance_overview": overview,
        "exception_book": exception_book,
        "exception_decisions": exception_decisions,
        "exception_dependencies": {
            "oversight_latest_run": _latest_run(inputs["oversight"]),
            "close_latest_run": _latest_run(inputs["close"]),
            "reconciliation_latest_run": _latest_run(inputs["reconciliation"]),
            "settlement_latest_run": _latest_run(inputs["settlement"]),
            "finalization_latest_run": _latest_run(inputs["finalization"]),
            "continuity_latest_run": _latest_run(inputs["continuity"]),
            "clearance_latest_run": _latest_run(inputs["clearance"]),
            "release_latest_run": _latest_run(inputs["release"]),
            "dispatch_latest_run": _latest_run(inputs["dispatch"]),
            "governance_latest_run": _latest_run(inputs["governance"]),
            "committee_latest_run": _latest_run(inputs["committee"]),
            "compliance_latest_run": _latest_run(inputs["compliance"]),
        },
        "exception_agenda": _agenda(exception_decisions),
    }


@router.get("/api/live-allocation-exception-governance-layer/summary")
def live_allocation_exception_governance_summary():
    session = _require_user()
    return _build_summary(session.get("email"))


@router.post("/api/live-allocation-exception-governance-layer/run")
def live_allocation_exception_governance_run(payload: dict = Body(default=None)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    summary = _build_summary(email)
    overview = summary.get("live_allocation_exception_governance_overview") or {}
    run = {
        "run_id": f"laegl_{time.time_ns()}",
        "mission": "QNT30678",
        "trigger": (payload or {}).get("trigger") or "manual",
        "timestamp": _now_ts(),
        "generated_at": summary.get("generated_at"),
        "exception_governance_posture": overview.get("exception_governance_posture"),
        "exception_governance_score": overview.get("exception_governance_score"),
        "resolve_count": overview.get("resolve_count"),
        "review_count": overview.get("review_count"),
        "hold_count": overview.get("hold_count"),
        "escalate_count": overview.get("escalate_count"),
        "governed_capital_millions": overview.get("governed_capital_millions"),
    }
    store.setdefault("runs", []).insert(0, run)
    store["runs"] = store.get("runs", [])[:120]
    _save(email, store)
    return {"status": "ok", "summary": summary, "run": run}


@router.get("/api/live-allocation-exception-governance-layer/audit")
def live_allocation_exception_governance_audit():
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    runs = store.get("runs") or []
    return {
        "mission": "QNT30678",
        "run_count": len(runs),
        "latest_run": runs[0] if runs else None,
        "runs": runs[:20],
        "policy": store.get("policy") or dict(DEFAULT_POLICY),
    }


@router.post("/api/live-allocation-exception-governance-layer/policy")
def live_allocation_exception_governance_policy(payload: dict = Body(...)):
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
