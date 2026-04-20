
import math
from datetime import datetime, timezone


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def default_allocator_intelligence_state():
    return {
        "enabled": True,
        "last_snapshot_at": None,
        "last_rebalance_at": None,
        "treasury": {
            "total_capital_usd": 100000.0,
            "reserve_ratio_target": 0.18,
            "min_reserve_usd": 15000.0,
            "reserve_balance_usd": 18000.0,
            "deployed_capital_usd": 0.0,
            "available_to_deploy_usd": 82000.0,
            "buffer_mode": "dynamic",
            "treasury_score": 100.0,
        },
        "allocation_policy": {
            "max_strategy_weight": 0.35,
            "min_strategy_weight": 0.05,
            "max_deploy_ratio": 0.82,
            "risk_haircut_enabled": True,
            "profit_recycle_ratio": 0.5,
            "drawdown_buffer_ratio": 0.12,
        },
        "strategy_budgets": {},
        "proposals": [],
        "alerts": [],
        "telemetry": {
            "snapshots_built": 0,
            "rebalance_runs": 0,
            "treasury_updates": 0,
            "reserve_releases": 0,
        },
    }


def allocator_intelligence_state_view(state):
    state = state or default_allocator_intelligence_state()
    defaults = default_allocator_intelligence_state()
    for k, v in defaults.items():
        state.setdefault(k, v.copy() if isinstance(v, dict) else v)
    for k, v in defaults["treasury"].items():
        state["treasury"].setdefault(k, v)
    for k, v in defaults["allocation_policy"].items():
        state["allocation_policy"].setdefault(k, v)
    state.setdefault("strategy_budgets", {})
    state.setdefault("proposals", [])
    state.setdefault("alerts", [])
    state.setdefault("telemetry", defaults["telemetry"].copy())
    return state


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def _strategy_rows(operator_state):
    operator_state = operator_state or {}
    engine = operator_state.get("strategy_engine", {}) or {}
    metrics = engine.get("metrics", {}) or {}
    rows = []
    for strategy in operator_state.get("strategies", {}).get("strategies", []) or []:
        if strategy.get("deleted"):
            continue
        metric = metrics.get(strategy.get("strategy_id"), {}) or {}
        realized = _safe_float(metric.get("realized_pnl"), 0.0)
        unrealized = _safe_float(metric.get("unrealized_pnl"), 0.0)
        win_rate = _safe_float(metric.get("win_rate"), 0.0)
        orders = max(_safe_int(metric.get("orders_count"), 0), 0)
        capital_in_use = max(_safe_float(metric.get("capital_in_use"), strategy.get("capital_limit") or 0.0), 0.0)
        conf = _safe_float(strategy.get("ai_confidence") or strategy.get("confidence") or 0.55, 0.55)
        pnl_efficiency = (realized + unrealized) / max(capital_in_use, 1.0)
        activity_score = min(1.0, orders / 20.0)
        win_component = min(1.0, max(0.0, win_rate / 100.0 if win_rate > 1 else win_rate))
        pnl_component = min(1.0, max(0.0, (pnl_efficiency + 0.15) / 0.3))
        score = (conf * 0.35) + (win_component * 0.25) + (pnl_component * 0.25) + (activity_score * 0.15)
        score = round(max(0.01, min(1.0, score)), 6)
        rows.append({
            "strategy_id": strategy.get("strategy_id"),
            "name": strategy.get("name"),
            "symbol": strategy.get("symbol"),
            "enabled": bool(strategy.get("enabled", True)),
            "status": strategy.get("status", "idle"),
            "capital_limit": round(_safe_float(strategy.get("capital_limit"), 0.0), 2),
            "confidence": round(conf, 4),
            "realized_pnl": round(realized, 2),
            "unrealized_pnl": round(unrealized, 2),
            "win_rate": round(win_component * 100.0, 2),
            "orders_count": orders,
            "capital_in_use": round(capital_in_use, 2),
            "allocator_score": round(score * 100.0, 2),
            "score_weight": score,
        })
    rows.sort(key=lambda r: (-r["score_weight"], -r["realized_pnl"], r["name"] or ""))
    return rows


def _portfolio_risk_haircut(portfolio_risk):
    if not portfolio_risk:
        return 1.0
    metrics = (portfolio_risk.get("risk_metrics") or {})
    leverage = _safe_float(metrics.get("portfolio_leverage_proxy"), 0.0)
    hedge = _safe_float(metrics.get("hedge_coverage_ratio"), 0.0)
    gross = _safe_float(metrics.get("gross_notional"), 0.0)
    haircut = 1.0
    if leverage > 2.0:
        haircut -= min(0.3, (leverage - 2.0) * 0.15)
    if hedge < 0.1 and gross > 0:
        haircut -= 0.08
    return round(max(0.55, min(1.0, haircut)), 4)


def build_allocator_snapshot(state, operator_state=None, portfolio_risk=None):
    state = allocator_intelligence_state_view(state)
    treasury = state["treasury"]
    policy = state["allocation_policy"]
    rows = _strategy_rows(operator_state or {})
    total_capital = max(_safe_float(treasury.get("total_capital_usd"), 0.0), 0.0)
    min_reserve = max(_safe_float(treasury.get("min_reserve_usd"), 0.0), 0.0)
    reserve_target = max(min_reserve, total_capital * max(_safe_float(treasury.get("reserve_ratio_target"), 0.0), 0.0))
    deploy_cap = max(0.0, (total_capital - reserve_target) * max(_safe_float(policy.get("max_deploy_ratio"), 0.0), 0.0))
    risk_haircut = _portfolio_risk_haircut(portfolio_risk)
    deploy_cap = round(deploy_cap * risk_haircut, 2)
    deployed = round(sum(max(r.get("capital_in_use", 0.0), r.get("capital_limit", 0.0) * 0.5) for r in rows if r.get("enabled")), 2)
    treasury["deployed_capital_usd"] = deployed
    treasury["reserve_balance_usd"] = round(max(reserve_target, total_capital - deploy_cap), 2)
    treasury["available_to_deploy_usd"] = round(max(0.0, deploy_cap - deployed), 2)
    treasury["treasury_score"] = round(max(0.0, min(100.0, 100.0 * risk_haircut * (1.0 if treasury["available_to_deploy_usd"] >= 0 else 0.75))), 2)
    snapshot = {
        "generated_at": now_iso(),
        "risk_haircut": risk_haircut,
        "deployable_capital_usd": deploy_cap,
        "treasury": treasury,
        "strategy_rows": rows,
    }
    state["last_snapshot_at"] = snapshot["generated_at"]
    state["telemetry"]["snapshots_built"] = int(state["telemetry"].get("snapshots_built", 0)) + 1
    return snapshot


def propose_rebalance(state, operator_state=None, portfolio_risk=None, market_bias="neutral"):
    state = allocator_intelligence_state_view(state)
    snapshot = build_allocator_snapshot(state, operator_state=operator_state, portfolio_risk=portfolio_risk)
    rows = snapshot["strategy_rows"]
    policy = state["allocation_policy"]
    max_weight = _safe_float(policy.get("max_strategy_weight"), 0.35)
    min_weight = _safe_float(policy.get("min_strategy_weight"), 0.05)
    deployable = _safe_float(snapshot.get("deployable_capital_usd"), 0.0)
    total_score = sum(r["score_weight"] for r in rows if r.get("enabled")) or 1.0
    proposals = []
    rebalance_amount = 0.0
    for row in rows:
        if not row.get("enabled"):
            continue
        raw_weight = row["score_weight"] / total_score
        target_weight = max(min_weight, min(max_weight, raw_weight))
        if market_bias == "risk_off":
            target_weight *= 0.85
        elif market_bias == "risk_on":
            target_weight *= 1.08
        target_weight = round(min(max_weight, max(min_weight, target_weight)), 4)
        target_capital = round(deployable * target_weight, 2)
        current_capital = round(max(row.get("capital_limit", 0.0), row.get("capital_in_use", 0.0)), 2)
        delta = round(target_capital - current_capital, 2)
        rebalance_amount += abs(delta)
        action = "hold"
        if delta > 250:
            action = "increase"
        elif delta < -250:
            action = "decrease"
        proposal = {
            "strategy_id": row["strategy_id"],
            "name": row["name"],
            "symbol": row["symbol"],
            "allocator_score": row["allocator_score"],
            "target_weight": target_weight,
            "target_capital_usd": target_capital,
            "current_capital_usd": current_capital,
            "delta_usd": delta,
            "action": action,
            "market_bias": market_bias,
        }
        proposals.append(proposal)
        state["strategy_budgets"][row["strategy_id"]] = proposal
    proposals.sort(key=lambda x: (-x["allocator_score"], x["name"] or ""))
    state["proposals"] = proposals
    state["last_rebalance_at"] = now_iso()
    state["telemetry"]["rebalance_runs"] = int(state["telemetry"].get("rebalance_runs", 0)) + 1
    state["alerts"] = [
        {"level": "warn", "type": "reserve_floor", "message": "Reserve buffer at or below target"}
        for _ in ([1] if state["treasury"].get("reserve_balance_usd", 0.0) <= max(state["treasury"].get("min_reserve_usd", 0.0), state["treasury"].get("total_capital_usd", 0.0) * state["treasury"].get("reserve_ratio_target", 0.0)) else [])
    ]
    return {
        "status": "ok",
        "generated_at": state["last_rebalance_at"],
        "market_bias": market_bias,
        "deployable_capital_usd": round(deployable, 2),
        "rebalance_notional_usd": round(rebalance_amount, 2),
        "proposals": proposals,
        "summary": allocator_summary(state),
    }


def update_treasury_policy(state, *, total_capital_usd=None, reserve_ratio_target=None, min_reserve_usd=None, max_deploy_ratio=None, profit_recycle_ratio=None):
    state = allocator_intelligence_state_view(state)
    treasury = state["treasury"]
    policy = state["allocation_policy"]
    if total_capital_usd is not None:
        treasury["total_capital_usd"] = round(max(_safe_float(total_capital_usd, treasury["total_capital_usd"]), 0.0), 2)
    if reserve_ratio_target is not None:
        treasury["reserve_ratio_target"] = round(min(0.9, max(0.0, _safe_float(reserve_ratio_target, treasury["reserve_ratio_target"]))), 4)
    if min_reserve_usd is not None:
        treasury["min_reserve_usd"] = round(max(0.0, _safe_float(min_reserve_usd, treasury["min_reserve_usd"])), 2)
    if max_deploy_ratio is not None:
        policy["max_deploy_ratio"] = round(min(1.0, max(0.05, _safe_float(max_deploy_ratio, policy["max_deploy_ratio"]))), 4)
    if profit_recycle_ratio is not None:
        policy["profit_recycle_ratio"] = round(min(1.0, max(0.0, _safe_float(profit_recycle_ratio, policy["profit_recycle_ratio"]))), 4)
    state["telemetry"]["treasury_updates"] = int(state["telemetry"].get("treasury_updates", 0)) + 1
    return {"status": "updated", "treasury": treasury, "allocation_policy": policy}


def release_reserve(state, *, amount_usd=0.0, reason="rebalance"):
    state = allocator_intelligence_state_view(state)
    treasury = state["treasury"]
    amount = max(0.0, _safe_float(amount_usd, 0.0))
    reserve_floor = max(_safe_float(treasury.get("min_reserve_usd"), 0.0), _safe_float(treasury.get("total_capital_usd"), 0.0) * _safe_float(treasury.get("reserve_ratio_target"), 0.0))
    reserve_balance = _safe_float(treasury.get("reserve_balance_usd"), 0.0)
    releasable = max(0.0, reserve_balance - reserve_floor)
    released = round(min(releasable, amount), 2)
    treasury["reserve_balance_usd"] = round(reserve_balance - released, 2)
    treasury["available_to_deploy_usd"] = round(_safe_float(treasury.get("available_to_deploy_usd"), 0.0) + released, 2)
    state["telemetry"]["reserve_releases"] = int(state["telemetry"].get("reserve_releases", 0)) + 1
    return {
        "status": "ok",
        "requested_usd": round(amount, 2),
        "released_usd": released,
        "reason": reason,
        "reserve_floor_usd": round(reserve_floor, 2),
        "reserve_balance_usd": treasury["reserve_balance_usd"],
    }


def allocator_summary(state):
    state = allocator_intelligence_state_view(state)
    budgets = list(state.get("strategy_budgets", {}).values())
    treasury = state["treasury"]
    return {
        "strategies": len(budgets),
        "increase_actions": len([b for b in budgets if b.get("action") == "increase"]),
        "decrease_actions": len([b for b in budgets if b.get("action") == "decrease"]),
        "hold_actions": len([b for b in budgets if b.get("action") == "hold"]),
        "reserve_balance_usd": round(_safe_float(treasury.get("reserve_balance_usd"), 0.0), 2),
        "available_to_deploy_usd": round(_safe_float(treasury.get("available_to_deploy_usd"), 0.0), 2),
        "treasury_score": round(_safe_float(treasury.get("treasury_score"), 0.0), 2),
    }
