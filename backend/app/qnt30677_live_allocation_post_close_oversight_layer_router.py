from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["live-allocation-post-close-oversight-layer"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
OVERSIGHT_DIR = ARTIFACTS_DIR / "live_allocation_post_close_oversight_layer"

DEFAULT_POLICY = {
    "minimum_oversight_score": 88.0,
    "minimum_close_score": 86.0,
    "minimum_reconciliation_score": 84.0,
    "minimum_settlement_score": 84.0,
    "minimum_continuity_score": 80.0,
    "maximum_exception_pressure": 22.0,
    "maximum_drift_pressure": 18.0,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]


def _artifact_file(folder: str, email: str) -> Path:
    return ARTIFACTS_DIR / folder / f"{_safe(email)}.json"


def _path(email: str) -> Path:
    OVERSIGHT_DIR.mkdir(parents=True, exist_ok=True)
    return OVERSIGHT_DIR / f"{_safe(email)}.json"


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
    }


def _oversight_rows(inputs: dict, policy: dict) -> list[dict]:
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

    base = allocations[:10] if allocations else []
    if not base:
        for idx in range(10):
            base.append({
                "strategy_id": f"STRAT_{idx+1:02d}",
                "strategy_name": f"Strategy {idx+1}",
                "allocated_capital": 0.0,
                "sleeve_id": f"sleeve_{idx+1:02d}",
            })

    close_score = float(close_run.get("close_score") or 82.0)
    reconciliation_score = float(reconciliation_run.get("reconciliation_score") or 82.0)
    settlement_score = float(settlement_run.get("settlement_score") or 82.0)
    finalization_score = float(finalization_run.get("finalization_score") or 82.0)
    continuity_score = float(continuity_run.get("continuity_score") or 80.0)
    clearance_score = float(clearance_run.get("clearance_score") or 82.0)
    release_score = float(release_run.get("release_score") or 82.0)
    dispatch_score = float(dispatch_run.get("dispatch_score") or 81.0)
    governance_score = float(governance_run.get("governance_score") or 80.0)
    committee_score = float(committee_run.get("oversight_score") or 80.0)
    compliance_release = float(compliance_run.get("release_score") or 86.0)

    rows = []
    for idx, alloc in enumerate(base):
        strategy_id = str(alloc.get("strategy_id") or f"STRAT_{idx+1:02d}")
        sleeve_id = str(alloc.get("sleeve_id") or strategy_id)
        allocated_capital = float(alloc.get("allocated_capital") or 0.0)
        strategy_positions = [p for p in positions if str(p.get("strategy_id") or p.get("sleeve_id") or "") in {strategy_id, sleeve_id}]
        strategy_pnl = [p for p in pnl_ledger if str(p.get("strategy_id") or p.get("sleeve_id") or "") in {strategy_id, sleeve_id}]
        unrealized = sum(float(p.get("unrealized_pnl") or p.get("pnl") or 0.0) for p in strategy_positions)
        realized = sum(float(p.get("realized_pnl") or p.get("amount") or 0.0) for p in strategy_pnl)
        gross_pnl = unrealized + realized
        pnl_yield_pct = (gross_pnl / allocated_capital * 100.0) if allocated_capital else 0.0
        drift_pressure = max(0.0, 8.0 - pnl_yield_pct) if pnl_yield_pct < 8.0 else max(0.0, (pnl_yield_pct - 20.0) * 0.4)
        exception_pressure = max(0.0, 86.0 - close_score) * 0.20
        exception_pressure += max(0.0, 84.0 - reconciliation_score) * 0.14
        exception_pressure += max(0.0, 84.0 - settlement_score) * 0.12
        exception_pressure += max(0.0, 80.0 - continuity_score) * 0.16
        exception_pressure += max(0.0, 82.0 - governance_score) * 0.10
        exception_pressure += max(0.0, 84.0 - compliance_release) * 0.08
        exception_pressure += drift_pressure * 0.85
        post_close_readiness_pct = min(100.0, 58.0 + len(strategy_positions) * 6.0 + max(0.0, pnl_yield_pct) * 1.8 + close_score * 0.18)
        oversight_score = (
            close_score * 0.20 + reconciliation_score * 0.14 + settlement_score * 0.12 +
            finalization_score * 0.08 + continuity_score * 0.12 + clearance_score * 0.06 +
            release_score * 0.05 + dispatch_score * 0.05 + governance_score * 0.07 +
            committee_score * 0.04 + compliance_release * 0.04 + post_close_readiness_pct * 0.10 +
            min(100.0, max(0.0, pnl_yield_pct + 50.0)) * 0.03
        )
        oversight_score = max(0.0, min(100.0, oversight_score - exception_pressure * 0.35))
        rows.append({
            "strategy_id": strategy_id,
            "strategy_name": alloc.get("strategy_name") or strategy_id,
            "allocated_capital_millions": _round_money(allocated_capital / 1_000_000.0),
            "close_score": _round_pct(close_score),
            "reconciliation_score": _round_pct(reconciliation_score),
            "settlement_score": _round_pct(settlement_score),
            "continuity_score": _round_pct(continuity_score),
            "governance_score": _round_pct(governance_score),
            "compliance_release_score": _round_pct(compliance_release),
            "pnl_yield_pct": _round_pct(pnl_yield_pct),
            "drift_pressure": _round_pct(drift_pressure),
            "exception_pressure": _round_pct(exception_pressure),
            "post_close_readiness_pct": _round_pct(post_close_readiness_pct),
            "oversight_score": _round_pct(oversight_score),
        })
    return rows


def _decisions(rows: list[dict], policy: dict) -> list[dict]:
    decisions = []
    for row in rows:
        reasons = []
        if row["close_score"] < float(policy["minimum_close_score"]):
            reasons.append("close authority below threshold")
        if row["reconciliation_score"] < float(policy["minimum_reconciliation_score"]):
            reasons.append("reconciliation below threshold")
        if row["settlement_score"] < float(policy["minimum_settlement_score"]):
            reasons.append("settlement below threshold")
        if row["continuity_score"] < float(policy["minimum_continuity_score"]):
            reasons.append("continuity below threshold")
        if row["exception_pressure"] > float(policy["maximum_exception_pressure"]):
            reasons.append("exception pressure elevated")
        if row["drift_pressure"] > float(policy["maximum_drift_pressure"]):
            reasons.append("post-close drift elevated")

        if row["oversight_score"] >= float(policy["minimum_oversight_score"]) and not reasons:
            action = "MAINTAIN"
        elif row["oversight_score"] >= float(policy["minimum_oversight_score"]) - 4.0:
            action = "REVIEW"
        elif row["oversight_score"] >= float(policy["minimum_oversight_score"]) - 10.0:
            action = "HOLD"
        else:
            action = "ESCALATE"

        decisions.append({
            "strategy_id": row["strategy_id"],
            "strategy_name": row["strategy_name"],
            "action": action,
            "oversight_score": row["oversight_score"],
            "exception_pressure": row["exception_pressure"],
            "drift_pressure": row["drift_pressure"],
            "reasons": reasons or ["post-close oversight stable"],
        })
    return decisions


def _overview(rows: list[dict], decisions: list[dict]) -> dict:
    avg_score = sum(r["oversight_score"] for r in rows) / max(len(rows), 1)
    avg_exception = sum(r["exception_pressure"] for r in rows) / max(len(rows), 1)
    avg_drift = sum(r["drift_pressure"] for r in rows) / max(len(rows), 1)
    total_capital = sum(r["allocated_capital_millions"] for r in rows)
    counts = {k: 0 for k in ["MAINTAIN", "REVIEW", "HOLD", "ESCALATE"]}
    for d in decisions:
        counts[d["action"]] = counts.get(d["action"], 0) + 1
    posture = "maintain"
    if counts["ESCALATE"]:
        posture = "escalate"
    elif counts["HOLD"]:
        posture = "hold"
    elif counts["REVIEW"]:
        posture = "review"
    return {
        "oversight_score": _round_pct(avg_score),
        "oversight_posture": posture,
        "oversight_capital_millions": _round_money(total_capital),
        "average_exception_pressure": _round_pct(avg_exception),
        "average_drift_pressure": _round_pct(avg_drift),
        "maintain_count": counts["MAINTAIN"],
        "review_count": counts["REVIEW"],
        "hold_count": counts["HOLD"],
        "escalate_count": counts["ESCALATE"],
    }


def _agenda(decisions: list[dict]) -> list[str]:
    agenda = []
    for action_name, text in [
        ("ESCALATE", "Escalate post-close oversight for"),
        ("HOLD", "Hold post-close scaling for"),
        ("REVIEW", "Review post-close oversight packet for"),
        ("MAINTAIN", "Maintain post-close supervision for"),
    ]:
        items = [d for d in decisions if d.get("action") == action_name][:3]
        if items:
            agenda.append(f"{text} {', '.join(i.get('strategy_id') for i in items)}.")
    if not agenda:
        agenda.append("No post-close oversight actions required.")
    return agenda


def _build_summary(email: str):
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    inputs = _artifact_inputs(email)
    oversight_book = _oversight_rows(inputs, policy)
    oversight_decisions = _decisions(oversight_book, policy)
    overview = _overview(oversight_book, oversight_decisions)
    return {
        "mission": "QNT30677",
        "generated_at": _now_iso(),
        "policy": policy,
        "live_allocation_post_close_oversight_overview": overview,
        "oversight_book": oversight_book,
        "oversight_decisions": oversight_decisions,
        "oversight_dependencies": {
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
        "oversight_agenda": _agenda(oversight_decisions),
    }


@router.get("/api/live-allocation-post-close-oversight-layer/summary")
def live_allocation_post_close_oversight_summary():
    session = _require_user()
    return _build_summary(session.get("email"))


@router.post("/api/live-allocation-post-close-oversight-layer/run")
def live_allocation_post_close_oversight_run(payload: dict = Body(default=None)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    summary = _build_summary(email)
    overview = summary.get("live_allocation_post_close_oversight_overview") or {}
    run = {
        "run_id": f"lapcol_{time.time_ns()}",
        "mission": "QNT30677",
        "trigger": (payload or {}).get("trigger") or "manual",
        "timestamp": _now_ts(),
        "generated_at": summary.get("generated_at"),
        "oversight_posture": overview.get("oversight_posture"),
        "oversight_score": overview.get("oversight_score"),
        "maintain_count": overview.get("maintain_count"),
        "review_count": overview.get("review_count"),
        "hold_count": overview.get("hold_count"),
        "escalate_count": overview.get("escalate_count"),
        "oversight_capital_millions": overview.get("oversight_capital_millions"),
    }
    store.setdefault("runs", []).insert(0, run)
    store["runs"] = store.get("runs", [])[:120]
    _save(email, store)
    return {"status": "ok", "summary": summary, "run": run}


@router.get("/api/live-allocation-post-close-oversight-layer/audit")
def live_allocation_post_close_oversight_audit():
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    runs = store.get("runs") or []
    return {
        "mission": "QNT30677",
        "run_count": len(runs),
        "latest_run": runs[0] if runs else None,
        "runs": runs[:20],
        "policy": store.get("policy") or dict(DEFAULT_POLICY),
    }


@router.post("/api/live-allocation-post-close-oversight-layer/policy")
def live_allocation_post_close_oversight_policy(payload: dict = Body(...)):
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
