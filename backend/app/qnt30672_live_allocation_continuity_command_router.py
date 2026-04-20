from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import statistics
import time

router = APIRouter(tags=["live-allocation-continuity-command"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
CONTINUITY_DIR = ARTIFACTS_DIR / "live_allocation_continuity_command"

DEFAULT_POLICY = {
    "priority_strategy_count": 8,
    "minimum_continuity_score": 78.0,
    "minimum_sharpe_ratio": 0.75,
    "maximum_drawdown_pct": 12.0,
    "maximum_volatility_proxy_pct": 18.0,
    "maximum_correlation_proxy_pct": 72.0,
    "maximum_concentration_pct": 38.0,
    "minimum_compliance_doc_completion_pct": 85.0,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]


def _artifact_file(folder: str, email: str) -> Path:
    return ARTIFACTS_DIR / folder / f"{_safe(email)}.json"


def _path(email: str) -> Path:
    CONTINUITY_DIR.mkdir(parents=True, exist_ok=True)
    return CONTINUITY_DIR / f"{_safe(email)}.json"


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
        "identity": _read_json(_artifact_file("investor_identity_registry", email), {"investors": [], "profiles": []}),
        "onboarding": _read_json(_artifact_file("investor_onboarding", email), {"investors": []}),
        "ledger": _read_json(_artifact_file("investor_capital_ledger", email), {"accounts": [], "entries": [], "allocations": []}),
        "pnl": _read_json(_artifact_file("investor_pnl_ledger", email), {"positions": [], "ledger": []}),
        "execution": _read_json(_artifact_file("strategy_execution_engine", email), {"strategy_allocations": [], "strategy_registry": [], "trades": [], "history": []}),
        "performance_store": _read_json(_artifact_file("performance_engine_v2", email), {"snapshots": [], "strategy_history": [], "investor_history": []}),
        "allocation_policy": _read_json(_artifact_file("allocation_engine", email), {"policy": {}, "decisions": []}),
        "broker": _read_json(_artifact_file("broker_integration_layer", email), {"settings": {}, "positions": {}, "orders": [], "fills": []}),
        "control_store": _read_json(_artifact_file("live_allocation_control_tower", email), {"policy": {}, "runs": []}),
        "clearance_store": _read_json(_artifact_file("live_allocation_clearance_grid", email), {"policy": {}, "runs": []}),
        "governance_store": _read_json(_artifact_file("execution_governance_command", email), {"policy": {}, "runs": []}),
        "compliance_store": _read_json(_artifact_file("institutional_compliance_layer", email), {"policy": {}, "runs": []}),
    }


def _return_series_from_positions(positions: list[dict]) -> list[float]:
    out = []
    for pos in positions or []:
        exposure = float(pos.get("qty") or 0.0) * float(pos.get("avg_price") or 0.0)
        pnl = float(pos.get("realized_pnl") or 0.0) + float(pos.get("unrealized_pnl") or 0.0)
        if exposure > 0:
            out.append((pnl / exposure) * 100.0)
    return out


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    try:
        return statistics.stdev(values)
    except Exception:
        return 0.0


def _strategy_metrics(inputs: dict, policy: dict) -> list[dict]:
    allocations = inputs["execution"].get("strategy_allocations") or []
    registry = {r.get("strategy_id"): r for r in (inputs["execution"].get("strategy_registry") or [])}
    positions = inputs["pnl"].get("positions") or []
    onboarding = {r.get("investor_id"): r for r in (inputs["onboarding"].get("investors") or [])}
    identity = {r.get("investor_id"): r for r in (inputs["identity"].get("investors") or [])}
    broker = inputs["broker"]
    control_policy = inputs["control_store"].get("policy") or {}
    clearance_policy = inputs["clearance_store"].get("policy") or {}
    governance_policy = inputs["governance_store"].get("policy") or {}
    compliance_policy = inputs["compliance_store"].get("policy") or {}
    alloc_policy = inputs["allocation_policy"].get("policy") or {}

    total_allocated = sum(float(a.get("allocated_capital") or 0.0) for a in allocations) or 1.0
    pos_by_sleeve = {}
    for pos in positions:
        sleeve = str(pos.get("sleeve_id") or "").strip()
        if not sleeve:
            continue
        pos_by_sleeve.setdefault(sleeve, []).append(pos)

    rows = []
    count = max(int(policy.get("priority_strategy_count") or 8), 4)
    base = allocations[:count] if allocations else []
    if not base:
        for idx in range(count):
            base.append({"strategy_id": f"STRAT_{idx+1:02d}", "strategy_name": f"Strategy {idx+1}", "allocated_capital": 0.0, "investor_id": None, "investor_name": None, "sleeve_id": f"sleeve_{idx+1:02d}"})

    for idx, alloc in enumerate(base):
        strategy_id = str(alloc.get("strategy_id") or f"STRAT_{idx+1:02d}")
        sleeve = str(alloc.get("sleeve_id") or strategy_id)
        strategy_positions = pos_by_sleeve.get(sleeve, [])
        allocated_capital = float(alloc.get("allocated_capital") or 0.0)
        realized = sum(float(p.get("realized_pnl") or 0.0) for p in strategy_positions)
        unrealized = sum(float(p.get("unrealized_pnl") or 0.0) for p in strategy_positions)
        gross_pnl = realized + unrealized
        return_pct = (gross_pnl / allocated_capital * 100.0) if allocated_capital > 0 else 0.0
        position_returns = _return_series_from_positions(strategy_positions)
        volatility_proxy = _std(position_returns) * 3.0 + max(0.0, -return_pct * 0.25)
        drawdown_proxy = max(0.0, abs(min(return_pct, 0.0)) * 0.65 + max(0.0, -unrealized) / max(allocated_capital, 1.0) * 100.0 * 0.55)
        concentration_pct = allocated_capital / total_allocated * 100.0 if total_allocated > 0 else 0.0
        correlation_proxy = min(100.0, concentration_pct * 1.15 + max(0.0, 8.0 - _std(position_returns)) * 1.8 + idx * 1.25)
        sharpe_proxy = 0.0
        if position_returns:
            sd = _std(position_returns)
            sharpe_proxy = (_avg(position_returns) / sd) if sd > 1e-12 else 0.0
        investor_id = alloc.get("investor_id")
        checklist = (onboarding.get(investor_id) or {}).get("checklist") or {}
        checklist_passes = sum(1 for v in checklist.values() if v)
        checklist_total = max(len(checklist), 1)
        doc_completion_pct = checklist_passes / checklist_total * 100.0
        readiness_mix = min(100.0,
            45.0
            + max(-12.0, min(18.0, return_pct)) * 1.4
            + max(0.0, 100.0 - volatility_proxy) * 0.12
            + max(0.0, 100.0 - correlation_proxy) * 0.08
            + doc_completion_pct * 0.12
            + max(0.0, float(control_policy.get("minimum_allocation_readiness_score") or 87.0) - 75.0) * 0.15
            + max(0.0, float(clearance_policy.get("minimum_clearance_readiness_score") or 86.0) - 75.0) * 0.10
        )
        broker_mode = str((broker.get("settings") or {}).get("mode") or "paper")
        live_permission = bool((broker.get("settings") or {}).get("allow_live_execution"))
        rows.append({
            "continuity_case_id": f"lacc_{idx+1:02d}",
            "strategy_id": strategy_id,
            "strategy_name": alloc.get("strategy_name") or strategy_id,
            "allocator_name": alloc.get("investor_name") or alloc.get("investor_id") or f"Allocator {idx+1}",
            "investor_id": investor_id,
            "jurisdiction": (identity.get(investor_id) or {}).get("jurisdiction") or "US",
            "sleeve_id": sleeve,
            "invested_capital_millions": _round_money(allocated_capital / 1_000_000.0),
            "gross_pnl_millions": _round_money(gross_pnl / 1_000_000.0),
            "return_pct": _round_pct(return_pct),
            "drawdown_pct": _round_pct(drawdown_proxy),
            "volatility_proxy_pct": _round_pct(volatility_proxy),
            "correlation_proxy_pct": _round_pct(correlation_proxy),
            "concentration_pct": _round_pct(concentration_pct),
            "sharpe_proxy": _round_num(sharpe_proxy),
            "doc_completion_pct": _round_pct(doc_completion_pct),
            "position_count": len(strategy_positions),
            "live_permission": live_permission,
            "broker_mode": broker_mode,
            "allocation_policy_max_drawdown_pct": float(alloc_policy.get("max_drawdown_pct") or 12.0),
            "governance_max_drift_score": float(governance_policy.get("maximum_drift_score") or 15.0),
            "compliance_min_docs_pct": float(policy.get("minimum_compliance_doc_completion_pct") or 85.0),
            "continuity_health_score": _round_pct(readiness_mix),
        })
    return rows


def _degradation_signals(book: list[dict], policy: dict) -> list[dict]:
    out = []
    for row in book:
        signals = []
        if float(row.get("drawdown_pct") or 0.0) > float(policy.get("maximum_drawdown_pct") or 12.0):
            signals.append("DRAWDOWN_BREACH")
        if float(row.get("volatility_proxy_pct") or 0.0) > float(policy.get("maximum_volatility_proxy_pct") or 18.0):
            signals.append("VOLATILITY_EXPANSION")
        if float(row.get("correlation_proxy_pct") or 0.0) > float(policy.get("maximum_correlation_proxy_pct") or 72.0):
            signals.append("CORRELATION_PRESSURE")
        if float(row.get("concentration_pct") or 0.0) > float(policy.get("maximum_concentration_pct") or 38.0):
            signals.append("CONCENTRATION_RISK")
        if float(row.get("sharpe_proxy") or 0.0) < float(policy.get("minimum_sharpe_ratio") or 0.75):
            signals.append("SHARPE_EROSION")
        if float(row.get("doc_completion_pct") or 0.0) < float(policy.get("minimum_compliance_doc_completion_pct") or 85.0):
            signals.append("COMPLIANCE_GAP")
        if not bool(row.get("live_permission")) or str(row.get("broker_mode") or "").lower() != "live":
            signals.append("LIVE_EXECUTION_NOT_ENABLED")
        out.append({
            "continuity_case_id": row.get("continuity_case_id"),
            "strategy_id": row.get("strategy_id"),
            "signals": signals,
            "signal_count": len(signals),
        })
    return out


def _continuity_actions(book: list[dict], signals: list[dict]) -> list[dict]:
    signal_map = {s.get("continuity_case_id"): s for s in signals}
    out = []
    for row in book:
        signal_list = (signal_map.get(row.get("continuity_case_id")) or {}).get("signals") or []
        action = "MAINTAIN"
        resize_pct = 0.0
        if "COMPLIANCE_GAP" in signal_list or "LIVE_EXECUTION_NOT_ENABLED" in signal_list:
            action = "REVIEW"
        if "CONCENTRATION_RISK" in signal_list or "CORRELATION_PRESSURE" in signal_list:
            action = "REDUCE"
            resize_pct = -20.0
        if "DRAWDOWN_BREACH" in signal_list and "VOLATILITY_EXPANSION" in signal_list:
            action = "EXIT"
            resize_pct = -100.0
        elif "SHARPE_EROSION" in signal_list and action == "MAINTAIN":
            action = "REBALANCE"
            resize_pct = -10.0
        confidence = min(0.99, 0.42 + len(signal_list) * 0.08 + max(0.0, float(row.get("drawdown_pct") or 0.0) - 10.0) * 0.01)
        out.append({
            "continuity_case_id": row.get("continuity_case_id"),
            "strategy_id": row.get("strategy_id"),
            "allocator_name": row.get("allocator_name"),
            "action": action,
            "capital_resize_pct": _round_pct(resize_pct),
            "confidence": round(confidence, 4),
            "reasons": signal_list or ["CONTINUITY_OK"],
        })
    return out


def _overview(inputs: dict, book: list[dict], signals: list[dict], actions: list[dict]) -> dict:
    total_capital = sum(float(r.get("invested_capital_millions") or 0.0) for r in book)
    avg_health = _avg([float(r.get("continuity_health_score") or 0.0) for r in book])
    avg_drawdown = _avg([float(r.get("drawdown_pct") or 0.0) for r in book])
    avg_vol = _avg([float(r.get("volatility_proxy_pct") or 0.0) for r in book])
    avg_corr = _avg([float(r.get("correlation_proxy_pct") or 0.0) for r in book])
    avg_sharpe = _avg([float(r.get("sharpe_proxy") or 0.0) for r in book])
    avg_docs = _avg([float(r.get("doc_completion_pct") or 0.0) for r in book])
    maintain_count = len([a for a in actions if a.get("action") == "MAINTAIN"])
    rebalance_count = len([a for a in actions if a.get("action") == "REBALANCE"])
    reduce_count = len([a for a in actions if a.get("action") == "REDUCE"])
    review_count = len([a for a in actions if a.get("action") == "REVIEW"])
    exit_count = len([a for a in actions if a.get("action") == "EXIT"])
    signal_count = sum(int(s.get("signal_count") or 0) for s in signals)
    score = min(100.0, avg_health * 0.52 + max(0.0, avg_sharpe) * 12.0 + avg_docs * 0.10 - avg_drawdown * 0.45 - avg_vol * 0.25 - avg_corr * 0.10)
    posture = "continuity-stable"
    if exit_count:
        posture = "continuity-broken"
    elif reduce_count or review_count:
        posture = "continuity-adjusting"
    return {
        "continuity_capital_millions": _round_money(total_capital),
        "continuity_score": _round_pct(score),
        "continuity_posture": posture,
        "maintain_count": maintain_count,
        "rebalance_count": rebalance_count,
        "reduce_count": reduce_count,
        "review_count": review_count,
        "exit_count": exit_count,
        "signal_count": signal_count,
        "average_health_score": _round_pct(avg_health),
        "average_drawdown_pct": _round_pct(avg_drawdown),
        "average_volatility_proxy_pct": _round_pct(avg_vol),
        "average_correlation_proxy_pct": _round_pct(avg_corr),
        "average_sharpe_proxy": _round_num(avg_sharpe),
        "average_doc_completion_pct": _round_pct(avg_docs),
    }


def _agenda(overview: dict, actions: list[dict]) -> list[str]:
    agenda = []
    if overview.get("continuity_posture") != "continuity-stable":
        agenda.append("Refresh continuity controls before allowing passive live scale continuation.")
    for action_name in ["EXIT", "REDUCE", "REBALANCE", "REVIEW"]:
        items = [a for a in actions if a.get("action") == action_name][:3]
        if not items:
            continue
        names = ", ".join(a.get("strategy_id") for a in items)
        if action_name == "EXIT":
            agenda.append(f"Exit {names} and recycle capital back into governed allocation control.")
        elif action_name == "REDUCE":
            agenda.append(f"Reduce {names} to relieve live concentration and correlation pressure.")
        elif action_name == "REBALANCE":
            agenda.append(f"Rebalance {names} under tighter execution supervision.")
        elif action_name == "REVIEW":
            agenda.append(f"Review {names} for compliance / live-permission gaps before continuing deployment.")
    if not agenda:
        agenda.append("Maintain live allocations and continue continuity monitoring cadence.")
    return agenda


def _build_summary(email: str):
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    inputs = _artifact_inputs(email)
    monitoring_book = _strategy_metrics(inputs, policy)
    degradation_signals = _degradation_signals(monitoring_book, policy)
    continuity_actions = _continuity_actions(monitoring_book, degradation_signals)
    overview = _overview(inputs, monitoring_book, degradation_signals, continuity_actions)
    broker_settings = inputs["broker"].get("settings") or {}
    compliance_policy = inputs["compliance_store"].get("policy") or {}
    return {
        "mission": "QNT30672",
        "generated_at": _now_iso(),
        "policy": policy,
        "live_allocation_continuity_overview": overview,
        "monitoring_book": monitoring_book,
        "degradation_signals": degradation_signals,
        "continuity_actions": continuity_actions,
        "continuity_dependencies": {
            "broker_mode": broker_settings.get("mode"),
            "allow_live_execution": broker_settings.get("allow_live_execution"),
            "kill_switch": broker_settings.get("kill_switch"),
            "max_strategy_exposure_pct": broker_settings.get("max_strategy_exposure_pct"),
            "allocation_engine_policy": inputs["allocation_policy"].get("policy") or {},
            "control_policy": inputs["control_store"].get("policy") or {},
            "clearance_policy": inputs["clearance_store"].get("policy") or {},
            "governance_policy": inputs["governance_store"].get("policy") or {},
            "compliance_policy": compliance_policy,
            "tracked_strategies": len(inputs["execution"].get("strategy_registry") or []),
            "tracked_positions": len(inputs["pnl"].get("positions") or []),
        },
        "continuity_agenda": _agenda(overview, continuity_actions),
    }


@router.get("/api/live-allocation-continuity-command/summary")
def live_allocation_continuity_command_summary():
    session = _require_user()
    return _build_summary(session.get("email"))


@router.post("/api/live-allocation-continuity-command/run")
def live_allocation_continuity_command_run(payload: dict = Body(default=None)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    summary = _build_summary(email)
    overview = summary.get("live_allocation_continuity_overview") or {}
    run = {
        "run_id": f"lacc_{time.time_ns()}",
        "mission": "QNT30672",
        "trigger": (payload or {}).get("trigger") or "manual",
        "timestamp": _now_ts(),
        "generated_at": summary.get("generated_at"),
        "continuity_posture": overview.get("continuity_posture"),
        "continuity_score": overview.get("continuity_score"),
        "maintain_count": overview.get("maintain_count"),
        "rebalance_count": overview.get("rebalance_count"),
        "reduce_count": overview.get("reduce_count"),
        "review_count": overview.get("review_count"),
        "exit_count": overview.get("exit_count"),
        "signal_count": overview.get("signal_count"),
        "continuity_capital_millions": overview.get("continuity_capital_millions"),
    }
    store.setdefault("runs", []).insert(0, run)
    store["runs"] = store.get("runs", [])[:120]
    _save(email, store)
    return {"status": "ok", "summary": summary, "run": run}


@router.get("/api/live-allocation-continuity-command/audit")
def live_allocation_continuity_command_audit():
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    runs = store.get("runs") or []
    return {
        "mission": "QNT30672",
        "run_count": len(runs),
        "latest_run": runs[0] if runs else None,
        "runs": runs[:20],
        "policy": store.get("policy") or dict(DEFAULT_POLICY),
    }


@router.post("/api/live-allocation-continuity-command/policy")
def live_allocation_continuity_command_policy(payload: dict = Body(...)):
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
