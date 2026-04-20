
import uuid
from datetime import datetime, timezone


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def default_scenario_engine_state():
    return {
        "version": "30359",
        "scenarios": [],
        "runs": [],
        "telemetry": {
            "scenarios_defined": 0,
            "runs_executed": 0,
            "breach_runs": 0,
            "worst_drawdown_pct": 0.0,
            "last_run_at": None,
            "last_scenario_id": None,
        },
    }


def scenario_engine_state_view(state):
    state = state or {}
    merged = default_scenario_engine_state()
    for k, v in state.items():
        merged[k] = v
    merged.setdefault("scenarios", [])
    merged.setdefault("runs", [])
    merged.setdefault("telemetry", {})
    for k, v in default_scenario_engine_state()["telemetry"].items():
        merged["telemetry"].setdefault(k, v)
    return merged


def define_scenario(state, *, name, shock_type="volatility_spike", market="equities", symbol=None, severity=0.35, volatility_multiplier=1.5, liquidity_haircut=0.2, spread_multiplier=1.8, correlation_jump=0.15, notes=None):
    state = scenario_engine_state_view(state)
    scenario = {
        "scenario_id": f"scn_{uuid.uuid4().hex[:10]}",
        "created_at": now_iso(),
        "name": name,
        "shock_type": shock_type,
        "market": market,
        "symbol": symbol,
        "severity": round(float(severity or 0.0), 4),
        "volatility_multiplier": round(float(volatility_multiplier or 1.0), 4),
        "liquidity_haircut": round(float(liquidity_haircut or 0.0), 4),
        "spread_multiplier": round(float(spread_multiplier or 1.0), 4),
        "correlation_jump": round(float(correlation_jump or 0.0), 4),
        "notes": notes,
    }
    state["scenarios"].append(scenario)
    state["telemetry"]["scenarios_defined"] = len(state["scenarios"])
    return {"status": "defined", "scenario": scenario}


def _safe_float(v, default=0.0):
    try:
        return float(v)
    except Exception:
        return default


def run_stress_test(state, *, scenario_id=None, scenario=None, portfolio_risk=None, allocator_state=None, autonomy_state=None, execution_state=None):
    state = scenario_engine_state_view(state)
    if scenario is None:
        scenario = next((s for s in state["scenarios"] if s["scenario_id"] == scenario_id), None)
    if not scenario:
        raise ValueError("scenario not found")

    risk = portfolio_risk or {}
    allocator = allocator_state or {}
    autonomy = autonomy_state or {}
    execution = execution_state or {}

    risk_summary = risk.get("summary") or risk.get("portfolio_summary") or {}
    gross = _safe_float(risk_summary.get("gross_exposure_usd") or risk_summary.get("gross_notional_usd") or risk.get("gross_exposure_usd"), 0.0)
    net = abs(_safe_float(risk_summary.get("net_exposure_usd") or risk_summary.get("net_notional_usd") or risk.get("net_exposure_usd"), 0.0))
    leverage = _safe_float(risk_summary.get("leverage_proxy") or risk.get("leverage_proxy"), 1.0)

    treasury = allocator.get("treasury") or allocator.get("allocator_snapshot", {}).get("treasury") or {}
    deployable = _safe_float(treasury.get("deployable_capital") or allocator.get("deployable_capital"), gross * 0.35 if gross else 0.0)
    reserve_floor = _safe_float(treasury.get("reserve_floor") or treasury.get("reserve_floor_usd"), deployable * 0.15 if deployable else 0.0)

    auto_summary = autonomy.get("summary") or autonomy.get("autonomy_summary") or {}
    autonomy_mode = (auto_summary.get("mode") or autonomy.get("mode") or "supervised").lower()
    autonomy_penalty = {"supervised": 0.85, "constrained_autonomy": 1.0, "delegated_autonomy": 1.08, "locked": 0.65}.get(autonomy_mode, 0.9)

    ex_opt = execution.get("execution_engine", {}).get("execution_optimizer", {}) if isinstance(execution, dict) else {}
    slippage_bps = _safe_float(ex_opt.get("avg_estimated_slippage_bps"), 12.0)

    severity = _safe_float(scenario.get("severity"), 0.35)
    vol_mult = _safe_float(scenario.get("volatility_multiplier"), 1.5)
    liq_haircut = _safe_float(scenario.get("liquidity_haircut"), 0.2)
    spread_mult = _safe_float(scenario.get("spread_multiplier"), 1.8)
    corr_jump = _safe_float(scenario.get("correlation_jump"), 0.15)

    drawdown_pct = min(0.95, (0.015 + severity * 0.09 + (leverage - 1.0) * 0.05 + liq_haircut * 0.22 + corr_jump * 0.18) * autonomy_penalty)
    liquidity_stress_pct = min(0.95, liq_haircut * spread_mult * 0.85)
    execution_cost_bps = round(slippage_bps * spread_mult * (1.0 + severity), 2)
    deployable_after_stress = max(0.0, deployable * (1.0 - drawdown_pct - liq_haircut * 0.5))
    reserve_breach = deployable_after_stress < reserve_floor
    gross_after_shock = round(gross * (1.0 + severity * 0.25 + corr_jump * 0.15), 2)
    net_after_shock = round(net * (1.0 + severity * 0.18), 2)

    breach_flags = []
    if drawdown_pct >= 0.12:
        breach_flags.append("drawdown_limit")
    if liquidity_stress_pct >= 0.28:
        breach_flags.append("liquidity_stress")
    if execution_cost_bps >= 45:
        breach_flags.append("execution_cost")
    if reserve_breach:
        breach_flags.append("reserve_floor")
    if leverage >= 2.2 and severity >= 0.35:
        breach_flags.append("leverage_proxy")

    verdict = "pass" if not breach_flags else "warn" if len(breach_flags) <= 2 else "fail"
    recommended_mode = autonomy_mode
    if verdict == "fail":
        recommended_mode = "locked" if "drawdown_limit" in breach_flags or "reserve_floor" in breach_flags else "supervised"
    elif verdict == "warn" and autonomy_mode == "delegated_autonomy":
        recommended_mode = "constrained_autonomy"

    run = {
        "run_id": f"run_{uuid.uuid4().hex[:10]}",
        "scenario_id": scenario["scenario_id"],
        "scenario_name": scenario["name"],
        "ran_at": now_iso(),
        "verdict": verdict,
        "breach_flags": breach_flags,
        "metrics": {
            "projected_drawdown_pct": round(drawdown_pct, 4),
            "gross_after_shock_usd": gross_after_shock,
            "net_after_shock_usd": net_after_shock,
            "liquidity_stress_pct": round(liquidity_stress_pct, 4),
            "execution_cost_bps": execution_cost_bps,
            "deployable_after_stress_usd": round(deployable_after_stress, 2),
            "reserve_floor_usd": round(reserve_floor, 2),
            "volatility_multiplier": vol_mult,
            "correlation_jump": corr_jump,
        },
        "governance_actions": {
            "recommended_autonomy_mode": recommended_mode,
            "throttle_new_allocation": verdict != "pass",
            "hold_large_orders": execution_cost_bps >= 45,
            "rebalance_required": reserve_breach or drawdown_pct >= 0.10,
        },
    }
    state["runs"].append(run)
    state["runs"] = state["runs"][-50:]
    tele = state["telemetry"]
    tele["runs_executed"] = int(tele.get("runs_executed", 0)) + 1
    if breach_flags:
        tele["breach_runs"] = int(tele.get("breach_runs", 0)) + 1
    tele["worst_drawdown_pct"] = round(max(_safe_float(tele.get("worst_drawdown_pct"), 0.0), drawdown_pct), 4)
    tele["last_run_at"] = run["ran_at"]
    tele["last_scenario_id"] = scenario["scenario_id"]
    return run


def scenario_engine_summary(state):
    state = scenario_engine_state_view(state)
    runs = state.get("runs", [])
    last = runs[-1] if runs else None
    return {
        "scenarios_defined": len(state.get("scenarios", [])),
        "runs_executed": len(runs),
        "latest_verdict": last.get("verdict") if last else "idle",
        "latest_breach_flags": last.get("breach_flags") if last else [],
        "worst_drawdown_pct": state["telemetry"].get("worst_drawdown_pct", 0.0),
    }
