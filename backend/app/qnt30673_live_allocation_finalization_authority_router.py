from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["live-allocation-finalization-authority"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
FINALIZATION_DIR = ARTIFACTS_DIR / "live_allocation_finalization_authority"

DEFAULT_POLICY = {
    "minimum_finalization_score": 82.0,
    "maximum_open_exception_count": 1,
    "maximum_clearance_gap_pct": 8.0,
    "maximum_continuity_drawdown_pct": 10.0,
    "maximum_execution_drift_score": 14.0,
    "minimum_document_completion_pct": 90.0,
    "minimum_live_readiness_pct": 88.0,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]


def _artifact_file(folder: str, email: str) -> Path:
    return ARTIFACTS_DIR / folder / f"{_safe(email)}.json"


def _path(email: str) -> Path:
    FINALIZATION_DIR.mkdir(parents=True, exist_ok=True)
    return FINALIZATION_DIR / f"{_safe(email)}.json"


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


def _round_num(v) -> float:
    return round(float(v or 0.0), 6)


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


def _artifact_inputs(email: str) -> dict:
    return {
        "continuity": _read_json(_artifact_file("live_allocation_continuity_command", email), {"policy": {}, "runs": []}),
        "clearance": _read_json(_artifact_file("live_allocation_clearance_grid", email), {"policy": {}, "runs": []}),
        "release": _read_json(_artifact_file("live_allocation_release_authority_mesh", email), {"policy": {}, "runs": []}),
        "dispatch": _read_json(_artifact_file("capital_dispatch_supervision_layer", email), {"policy": {}, "runs": []}),
        "governance": _read_json(_artifact_file("execution_governance_command", email), {"policy": {}, "runs": []}),
        "compliance": _read_json(_artifact_file("institutional_compliance_layer", email), {"policy": {}, "runs": []}),
        "broker": _read_json(_artifact_file("broker_integration_layer", email), {"settings": {}, "positions": {}, "orders": [], "fills": []}),
        "execution": _read_json(_artifact_file("strategy_execution_engine", email), {"strategy_allocations": [], "strategy_registry": [], "trades": [], "history": []}),
        "pnl": _read_json(_artifact_file("investor_pnl_ledger", email), {"positions": [], "ledger": []}),
        "onboarding": _read_json(_artifact_file("investor_onboarding", email), {"investors": []}),
    }


def _latest_run(store: dict) -> dict:
    runs = store.get("runs") or []
    return runs[0] if runs else {}


def _strategy_rows(inputs: dict, policy: dict) -> list[dict]:
    continuity_run = _latest_run(inputs["continuity"])
    clearance_run = _latest_run(inputs["clearance"])
    release_run = _latest_run(inputs["release"])
    dispatch_run = _latest_run(inputs["dispatch"])
    governance_run = _latest_run(inputs["governance"])
    broker_settings = inputs["broker"].get("settings") or {}
    allocations = inputs["execution"].get("strategy_allocations") or []
    positions = inputs["pnl"].get("positions") or []
    onboarding = {r.get("investor_id"): r for r in (inputs["onboarding"].get("investors") or [])}
    pos_by_sleeve = {}
    for pos in positions:
        sleeve = str(pos.get("sleeve_id") or "").strip()
        if sleeve:
            pos_by_sleeve.setdefault(sleeve, []).append(pos)
    total_alloc = sum(float(a.get("allocated_capital") or 0.0) for a in allocations) or 1.0
    rows = []
    base = allocations[:8] if allocations else []
    if not base:
        for idx in range(8):
            base.append({"strategy_id": f"STRAT_{idx+1:02d}", "strategy_name": f"Strategy {idx+1}", "allocated_capital": 0.0, "investor_id": None, "investor_name": None, "sleeve_id": f"sleeve_{idx+1:02d}"})
    base_cont_score = float(continuity_run.get("continuity_score") or 74.0)
    base_signal_count = float(continuity_run.get("signal_count") or 0.0)
    base_clearance = 100.0 - float(clearance_run.get("average_gap_pct") or 6.0)
    base_release = float(release_run.get("release_score") or release_run.get("average_release_score") or 82.0)
    base_dispatch = float(dispatch_run.get("dispatch_score") or dispatch_run.get("average_dispatch_score") or 80.0)
    base_drift = float(governance_run.get("average_drift_score") or governance_run.get("max_drift_score") or 9.0)
    for idx, alloc in enumerate(base):
        sleeve = str(alloc.get("sleeve_id") or alloc.get("strategy_id") or f"sleeve_{idx+1:02d}")
        strategy_positions = pos_by_sleeve.get(sleeve, [])
        allocated_capital = float(alloc.get("allocated_capital") or 0.0)
        realized = sum(float(p.get("realized_pnl") or 0.0) for p in strategy_positions)
        unrealized = sum(float(p.get("unrealized_pnl") or 0.0) for p in strategy_positions)
        gross_pnl = realized + unrealized
        drawdown_pct = max(0.0, abs(min(unrealized, 0.0)) / max(allocated_capital, 1.0) * 100.0)
        live_readiness_pct = min(100.0,
            58.0
            + max(0.0, base_clearance - idx * 1.3) * 0.14
            + max(0.0, base_release - idx * 0.9) * 0.14
            + max(0.0, base_dispatch - idx * 1.1) * 0.12
            + (10.0 if broker_settings.get("allow_live_execution") else -18.0)
            + (6.0 if str(broker_settings.get("mode") or "").lower() == "live" else -9.0)
        )
        checklist = (onboarding.get(alloc.get("investor_id")) or {}).get("checklist") or {}
        if checklist:
            doc_completion_pct = sum(1 for v in checklist.values() if v) / max(len(checklist), 1) * 100.0
        else:
            doc_completion_pct = max(84.0, 96.0 - idx * 1.5)
        exception_count = 0
        if drawdown_pct > float(policy.get("maximum_continuity_drawdown_pct") or 10.0):
            exception_count += 1
        if live_readiness_pct < float(policy.get("minimum_live_readiness_pct") or 88.0):
            exception_count += 1
        if doc_completion_pct < float(policy.get("minimum_document_completion_pct") or 90.0):
            exception_count += 1
        if base_drift + idx * 0.7 > float(policy.get("maximum_execution_drift_score") or 14.0):
            exception_count += 1
        finalization_score = min(100.0,
            base_cont_score * 0.30
            + live_readiness_pct * 0.22
            + base_clearance * 0.15
            + base_release * 0.15
            + base_dispatch * 0.10
            + doc_completion_pct * 0.08
            - drawdown_pct * 0.55
            - base_signal_count * 0.35
            - idx * 1.5
        )
        rows.append({
            "finalization_case_id": f"lafa_{idx+1:02d}",
            "strategy_id": str(alloc.get("strategy_id") or f"STRAT_{idx+1:02d}"),
            "strategy_name": alloc.get("strategy_name") or f"Strategy {idx+1}",
            "allocator_name": alloc.get("investor_name") or alloc.get("investor_id") or f"Allocator {idx+1}",
            "invested_capital_millions": _round_money(allocated_capital / 1_000_000.0),
            "gross_pnl_millions": _round_money(gross_pnl / 1_000_000.0),
            "concentration_pct": _round_pct(allocated_capital / total_alloc * 100.0 if total_alloc else 0.0),
            "drawdown_pct": _round_pct(drawdown_pct),
            "continuity_score": _round_pct(base_cont_score - idx * 1.25),
            "clearance_gap_pct": _round_pct(max(0.0, 100.0 - base_clearance + idx * 0.9)),
            "execution_drift_score": _round_pct(base_drift + idx * 0.7),
            "document_completion_pct": _round_pct(doc_completion_pct),
            "live_readiness_pct": _round_pct(live_readiness_pct),
            "open_exception_count": int(exception_count),
            "finalization_score": _round_pct(finalization_score),
        })
    return rows


def _authority_decisions(rows: list[dict], policy: dict) -> list[dict]:
    out = []
    for row in rows:
        reasons = []
        if float(row.get("clearance_gap_pct") or 0.0) > float(policy.get("maximum_clearance_gap_pct") or 8.0):
            reasons.append("CLEARANCE_GAP")
        if float(row.get("drawdown_pct") or 0.0) > float(policy.get("maximum_continuity_drawdown_pct") or 10.0):
            reasons.append("CONTINUITY_DRAWDOWN")
        if float(row.get("execution_drift_score") or 0.0) > float(policy.get("maximum_execution_drift_score") or 14.0):
            reasons.append("EXECUTION_DRIFT")
        if float(row.get("document_completion_pct") or 0.0) < float(policy.get("minimum_document_completion_pct") or 90.0):
            reasons.append("DOCUMENTATION_GAP")
        if float(row.get("live_readiness_pct") or 0.0) < float(policy.get("minimum_live_readiness_pct") or 88.0):
            reasons.append("LIVE_READINESS_GAP")
        if int(row.get("open_exception_count") or 0) > int(policy.get("maximum_open_exception_count") or 1):
            reasons.append("EXCEPTION_OVERFLOW")
        score = float(row.get("finalization_score") or 0.0)
        action = "FINALIZE"
        if reasons:
            action = "REVIEW"
        if "CONTINUITY_DRAWDOWN" in reasons or "EXCEPTION_OVERFLOW" in reasons:
            action = "HOLD"
        if score < float(policy.get("minimum_finalization_score") or 82.0) - 8.0:
            action = "ROLLBACK"
        confidence = min(0.99, 0.48 + max(0.0, score - 70.0) * 0.008 + len(reasons) * 0.04)
        out.append({
            "finalization_case_id": row.get("finalization_case_id"),
            "strategy_id": row.get("strategy_id"),
            "allocator_name": row.get("allocator_name"),
            "action": action,
            "confidence": round(confidence, 4),
            "reasons": reasons or ["FINALIZATION_OK"],
        })
    return out


def _overview(rows: list[dict], decisions: list[dict]) -> dict:
    total_capital = sum(float(r.get("invested_capital_millions") or 0.0) for r in rows)
    avg_score = sum(float(r.get("finalization_score") or 0.0) for r in rows) / len(rows) if rows else 0.0
    avg_readiness = sum(float(r.get("live_readiness_pct") or 0.0) for r in rows) / len(rows) if rows else 0.0
    avg_gap = sum(float(r.get("clearance_gap_pct") or 0.0) for r in rows) / len(rows) if rows else 0.0
    finalize_count = len([d for d in decisions if d.get("action") == "FINALIZE"])
    review_count = len([d for d in decisions if d.get("action") == "REVIEW"])
    hold_count = len([d for d in decisions if d.get("action") == "HOLD"])
    rollback_count = len([d for d in decisions if d.get("action") == "ROLLBACK"])
    posture = "finalization-open"
    if rollback_count:
        posture = "finalization-reversal"
    elif hold_count:
        posture = "finalization-constrained"
    elif review_count:
        posture = "finalization-review"
    return {
        "finalization_capital_millions": _round_money(total_capital),
        "finalization_score": _round_pct(avg_score),
        "finalization_posture": posture,
        "average_live_readiness_pct": _round_pct(avg_readiness),
        "average_clearance_gap_pct": _round_pct(avg_gap),
        "finalize_count": finalize_count,
        "review_count": review_count,
        "hold_count": hold_count,
        "rollback_count": rollback_count,
    }


def _agenda(overview: dict, decisions: list[dict]) -> list[str]:
    agenda = []
    for action_name, text in [
        ("ROLLBACK", "Rollback finalization for"),
        ("HOLD", "Hold live finalization for"),
        ("REVIEW", "Review finalization package for"),
        ("FINALIZE", "Finalize live allocation release for"),
    ]:
        items = [d for d in decisions if d.get("action") == action_name][:3]
        if items:
            agenda.append(f"{text} {', '.join(i.get('strategy_id') for i in items)}.")
    if not agenda:
        agenda.append("No finalization actions required.")
    return agenda


def _build_summary(email: str):
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    inputs = _artifact_inputs(email)
    finalization_book = _strategy_rows(inputs, policy)
    finalization_decisions = _authority_decisions(finalization_book, policy)
    overview = _overview(finalization_book, finalization_decisions)
    return {
        "mission": "QNT30673",
        "generated_at": _now_iso(),
        "policy": policy,
        "live_allocation_finalization_overview": overview,
        "finalization_book": finalization_book,
        "finalization_decisions": finalization_decisions,
        "finalization_dependencies": {
            "continuity_latest_run": _latest_run(inputs["continuity"]),
            "clearance_latest_run": _latest_run(inputs["clearance"]),
            "release_latest_run": _latest_run(inputs["release"]),
            "dispatch_latest_run": _latest_run(inputs["dispatch"]),
            "governance_latest_run": _latest_run(inputs["governance"]),
            "broker_settings": inputs["broker"].get("settings") or {},
        },
        "finalization_agenda": _agenda(overview, finalization_decisions),
    }


@router.get("/api/live-allocation-finalization-authority/summary")
def live_allocation_finalization_authority_summary():
    session = _require_user()
    return _build_summary(session.get("email"))


@router.post("/api/live-allocation-finalization-authority/run")
def live_allocation_finalization_authority_run(payload: dict = Body(default=None)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    summary = _build_summary(email)
    overview = summary.get("live_allocation_finalization_overview") or {}
    run = {
        "run_id": f"lafa_{time.time_ns()}",
        "mission": "QNT30673",
        "trigger": (payload or {}).get("trigger") or "manual",
        "timestamp": _now_ts(),
        "generated_at": summary.get("generated_at"),
        "finalization_posture": overview.get("finalization_posture"),
        "finalization_score": overview.get("finalization_score"),
        "finalize_count": overview.get("finalize_count"),
        "review_count": overview.get("review_count"),
        "hold_count": overview.get("hold_count"),
        "rollback_count": overview.get("rollback_count"),
        "finalization_capital_millions": overview.get("finalization_capital_millions"),
    }
    store.setdefault("runs", []).insert(0, run)
    store["runs"] = store.get("runs", [])[:120]
    _save(email, store)
    return {"status": "ok", "summary": summary, "run": run}


@router.get("/api/live-allocation-finalization-authority/audit")
def live_allocation_finalization_authority_audit():
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    runs = store.get("runs") or []
    return {
        "mission": "QNT30673",
        "run_count": len(runs),
        "latest_run": runs[0] if runs else None,
        "runs": runs[:20],
        "policy": store.get("policy") or dict(DEFAULT_POLICY),
    }


@router.post("/api/live-allocation-finalization-authority/policy")
def live_allocation_finalization_authority_policy(payload: dict = Body(...)):
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
