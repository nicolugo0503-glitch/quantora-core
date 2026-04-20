from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["cross-fund-allocation"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
XFA_DIR = ARTIFACTS_DIR / "cross_fund_allocation"

DEFAULT_POLICY = {
    "minimum_allocation_score": 84.0,
    "minimum_orchestration_score": 78.0,
    "minimum_brain_score": 78.0,
    "minimum_selection_score": 78.0,
    "minimum_regime_score": 78.0,
    "minimum_governance_score": 78.0,
    "minimum_compliance_score": 78.0,
    "maximum_fund_load_pct": 55.0,
    "maximum_exception_pressure": 22.0,
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
    XFA_DIR.mkdir(parents=True, exist_ok=True)
    return XFA_DIR / f"{_safe(email)}.json"

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
        "orchestration": _read_json(_artifact_file("multi_fund_orchestration", email), {"policy": {}, "runs": []}),
        "brain": _read_json(_artifact_file("portfolio_intelligence_brain", email), {"policy": {}, "runs": []}),
        "selection": _read_json(_artifact_file("strategy_selection_ai", email), {"policy": {}, "runs": []}),
        "regime": _read_json(_artifact_file("regime_detection_engine", email), {"policy": {}, "runs": []}),
        "governance": _read_json(_artifact_file("execution_governance_command", email), {"policy": {}, "runs": []}),
        "committee": _read_json(_artifact_file("capital_committee_oversight_mesh", email), {"policy": {}, "runs": []}),
        "compliance": _read_json(_artifact_file("institutional_compliance_layer", email), {"policy": {}, "runs": []}),
        "execution": _read_json(_artifact_file("strategy_execution_engine", email), {"strategy_allocations": [], "trades": [], "history": []}),
        "pnl": _read_json(_artifact_file("investor_pnl_ledger", email), {"positions": [], "ledger": []}),
        "ledger": _read_json(_artifact_file("investor_capital_ledger", email), {"accounts": [], "entries": [], "allocations": []}),
        "multi_fund": _read_json(_artifact_file("multi_fund_architecture", email), {"policy": {}, "runs": []}),
    }

def _fund_buckets(inputs: dict):
    orch_run = _latest_run(inputs["orchestration"])
    existing = inputs["multi_fund"].get("funds") or []
    if existing:
        return existing
    base = [
        {"fund_id": "MASTER_FUND", "fund_name": "master_fund", "base_weight": 0.40},
        {"fund_id": "ALPHA_FUND", "fund_name": "alpha_fund", "base_weight": 0.28},
        {"fund_id": "INCOME_FUND", "fund_name": "income_fund", "base_weight": 0.18},
        {"fund_id": "OPPORTUNITY_FUND", "fund_name": "opportunity_fund", "base_weight": 0.14},
    ]
    if orch_run:
        posture = orch_run.get("multi_fund_posture")
        if posture == "REDISTRIBUTING":
            base[0]["base_weight"] = 0.34
            base[1]["base_weight"] = 0.30
            base[2]["base_weight"] = 0.20
            base[3]["base_weight"] = 0.16
    return base

def _rows(inputs: dict, policy: dict) -> list[dict]:
    orch_run = _latest_run(inputs["orchestration"])
    brain_run = _latest_run(inputs["brain"])
    selection_run = _latest_run(inputs["selection"])
    regime_run = _latest_run(inputs["regime"])
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

    pnl_ledger = inputs["pnl"].get("ledger") or []
    realized = sum(float(x.get("realized_pnl") or x.get("pnl") or 0.0) for x in pnl_ledger)
    unrealized = sum(float(p.get("unrealized_pnl") or 0.0) for p in positions)
    pnl_total = realized + unrealized
    drawdown_pct = abs(min(pnl_total, 0.0)) / max(governed_capital, 1.0) * 100.0

    orch_score = float(orch_run.get("orchestration_score") or 0.0)
    brain_score = float(brain_run.get("brain_score") or 0.0)
    selection_score = float(selection_run.get("selection_score") or 0.0)
    regime_score = float(regime_run.get("regime_score") or 0.0)
    governance_score = float(governance_run.get("governance_score") or governance_run.get("supervisory_score") or 0.0)
    compliance_score = float(compliance_run.get("release_score") or compliance_run.get("compliance_score") or 0.0)

    exception_pressure = min(
        float(orch_run.get("escalate_count") or 0.0) * 5.0 +
        float(brain_run.get("escalate_count") or 0.0) * 4.0 +
        float(committee_run.get("escalate_count") or committee_run.get("review_count") or 0.0) * 2.0,
        30.0
    )

    rows = []
    for fund in _fund_buckets(inputs):
        weight = float(fund.get("base_weight") or 0.0)
        allocated_capital = governed_capital * weight
        fund_load_pct = weight * 100.0

        break_pressure = 0.0
        if fund_load_pct > policy["maximum_fund_load_pct"]:
            break_pressure += min(6.0, (fund_load_pct - policy["maximum_fund_load_pct"]) * 0.25)
        if drawdown_pct > policy["maximum_drawdown_pct"]:
            break_pressure += min(6.0, (drawdown_pct - policy["maximum_drawdown_pct"]) * 0.35)
        if orch_score < policy["minimum_orchestration_score"]:
            break_pressure += min(5.0, (policy["minimum_orchestration_score"] - orch_score) * 0.30)
        if brain_score < policy["minimum_brain_score"]:
            break_pressure += min(5.0, (policy["minimum_brain_score"] - brain_score) * 0.30)
        if selection_score < policy["minimum_selection_score"]:
            break_pressure += min(5.0, (policy["minimum_selection_score"] - selection_score) * 0.30)
        if regime_score < policy["minimum_regime_score"]:
            break_pressure += min(5.0, (policy["minimum_regime_score"] - regime_score) * 0.30)

        allocation_raw = (
            orch_score * 0.24 +
            brain_score * 0.18 +
            selection_score * 0.16 +
            regime_score * 0.14 +
            governance_score * 0.14 +
            compliance_score * 0.14
        )
        allocation_score = max(0.0, min(100.0, allocation_raw - exception_pressure - break_pressure))

        rows.append({
            "fund_id": fund.get("fund_id"),
            "fund_name": fund.get("fund_name"),
            "allocated_capital_millions": _round_money(allocated_capital / 1_000_000.0),
            "fund_load_pct": _round_pct(fund_load_pct),
            "orchestration_score": _round_pct(orch_score),
            "brain_score": _round_pct(brain_score),
            "selection_score": _round_pct(selection_score),
            "regime_score": _round_pct(regime_score),
            "governance_score": _round_pct(governance_score),
            "compliance_score": _round_pct(compliance_score),
            "drawdown_pct": _round_pct(drawdown_pct),
            "exception_pressure": _round_pct(exception_pressure),
            "break_pressure": _round_pct(break_pressure),
            "allocation_score": _round_pct(allocation_score),
        })
    return rows

def _decisions(rows: list[dict], policy: dict) -> list[dict]:
    decisions = []
    for row in rows:
        score = float(row.get("allocation_score") or 0.0)
        load_pct = float(row.get("fund_load_pct") or 0.0)
        exception_pressure = float(row.get("exception_pressure") or 0.0)
        break_pressure = float(row.get("break_pressure") or 0.0)

        action = "ALLOCATE"
        reasons = []

        if score < policy["minimum_allocation_score"]:
            action = "REBALANCE"
            reasons.append("allocation score below threshold")
        if load_pct > policy["maximum_fund_load_pct"] and action in {"ALLOCATE", "REBALANCE"}:
            action = "REDISTRIBUTE"
            reasons.append("fund load exceeds allocation tolerance")
        if exception_pressure > policy["maximum_exception_pressure"]:
            action = "HOLD"
            reasons.append("exception pressure above threshold")
        if break_pressure > policy["maximum_break_pressure"]:
            action = "ESCALATE"
            reasons.append("break pressure above threshold")
        if not reasons:
            reasons.append("cross-fund allocation posture inside governed band")

        confidence = max(0.5, min(0.99, 0.99 - (exception_pressure + break_pressure) / 200.0))
        decisions.append({
            "fund_id": row.get("fund_id"),
            "action": action,
            "confidence": _round_pct(confidence),
            "reason": "; ".join(reasons),
            "allocated_capital_millions": row.get("allocated_capital_millions"),
            "allocation_score": row.get("allocation_score"),
        })
    return decisions

def _overview(rows: list[dict], decisions: list[dict]) -> dict:
    if not rows:
        return {
            "cross_fund_posture": "EMPTY",
            "allocation_score": 0.0,
            "allocate_count": 0,
            "rebalance_count": 0,
            "redistribute_count": 0,
            "hold_count": 0,
            "escalate_count": 0,
            "governed_capital_millions": 0.0,
            "fund_count": 0,
        }
    score = sum(float(r.get("allocation_score") or 0.0) for r in rows) / len(rows)
    cap = sum(float(r.get("allocated_capital_millions") or 0.0) for r in rows)
    counts = {"ALLOCATE": 0, "REBALANCE": 0, "REDISTRIBUTE": 0, "HOLD": 0, "ESCALATE": 0}
    for d in decisions:
        counts[d.get("action")] = counts.get(d.get("action"), 0) + 1
    posture = "ALLOCATING"
    if counts["ESCALATE"] > 0:
        posture = "ESCALATED"
    elif counts["HOLD"] > 0:
        posture = "CONSTRAINED"
    elif counts["REDISTRIBUTE"] > 0:
        posture = "REDISTRIBUTING"
    elif counts["REBALANCE"] > 0:
        posture = "REBALANCING"
    return {
        "cross_fund_posture": posture,
        "allocation_score": _round_pct(score),
        "allocate_count": counts["ALLOCATE"],
        "rebalance_count": counts["REBALANCE"],
        "redistribute_count": counts["REDISTRIBUTE"],
        "hold_count": counts["HOLD"],
        "escalate_count": counts["ESCALATE"],
        "governed_capital_millions": _round_money(cap),
        "fund_count": len(rows),
    }

def _agenda(decisions: list[dict]) -> list[dict]:
    agenda = []
    for idx, d in enumerate(decisions, start=1):
        agenda.append({
            "sequence": idx,
            "fund_id": d.get("fund_id"),
            "action": d.get("action"),
            "reason": d.get("reason"),
            "allocated_capital_millions": d.get("allocated_capital_millions"),
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
        "mission": "QNT30690",
        "generated_at": _now_iso(),
        "policy": policy,
        "cross_fund_allocation_overview": overview,
        "cross_fund_book": book,
        "cross_fund_decisions": decisions,
        "cross_fund_dependencies": {
            "orchestration_latest_run": _latest_run(inputs["orchestration"]),
            "brain_latest_run": _latest_run(inputs["brain"]),
            "selection_latest_run": _latest_run(inputs["selection"]),
            "regime_latest_run": _latest_run(inputs["regime"]),
            "governance_latest_run": _latest_run(inputs["governance"]),
            "committee_latest_run": _latest_run(inputs["committee"]),
            "compliance_latest_run": _latest_run(inputs["compliance"]),
            "architecture_latest_run": _latest_run(inputs["multi_fund"]),
        },
        "cross_fund_agenda": _agenda(decisions),
    }

@router.get("/api/cross-fund-allocation/summary")
def cross_fund_allocation_summary():
    session = _require_user()
    return _build_summary(session.get("email"))

@router.post("/api/cross-fund-allocation/run")
def cross_fund_allocation_run(payload: dict = Body(default=None)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    summary = _build_summary(email)
    overview = summary.get("cross_fund_allocation_overview") or {}
    run = {
        "run_id": f"cfa_{time.time_ns()}",
        "mission": "QNT30690",
        "trigger": (payload or {}).get("trigger") or "manual",
        "timestamp": _now_ts(),
        "generated_at": summary.get("generated_at"),
        "cross_fund_posture": overview.get("cross_fund_posture"),
        "allocation_score": overview.get("allocation_score"),
        "allocate_count": overview.get("allocate_count"),
        "rebalance_count": overview.get("rebalance_count"),
        "redistribute_count": overview.get("redistribute_count"),
        "hold_count": overview.get("hold_count"),
        "escalate_count": overview.get("escalate_count"),
        "governed_capital_millions": overview.get("governed_capital_millions"),
        "fund_count": overview.get("fund_count"),
    }
    store.setdefault("runs", []).insert(0, run)
    store["runs"] = store.get("runs", [])[:120]
    _save(email, store)
    return {"status": "ok", "summary": summary, "run": run}

@router.get("/api/cross-fund-allocation/audit")
def cross_fund_allocation_audit():
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    runs = store.get("runs") or []
    return {
        "mission": "QNT30690",
        "run_count": len(runs),
        "latest_run": runs[0] if runs else None,
        "runs": runs[:20],
        "policy": store.get("policy") or dict(DEFAULT_POLICY),
    }

@router.post("/api/cross-fund-allocation/policy")
def cross_fund_allocation_policy(payload: dict = Body(...)):
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
