from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List


def _f(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def _now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _risk_multiplier(risk: Dict[str, Any]) -> float:
    if not risk:
        return 0.75
    if risk.get("kill_switch_active") or risk.get("breached"):
        return 0.0
    drawdown = abs(_f(risk.get("current_drawdown_pct")))
    daily = abs(_f(risk.get("current_daily_realized_pnl")))
    max_dd = max(_f(risk.get("max_drawdown_pct"), 12.0), 1.0)
    max_daily = max(_f(risk.get("max_daily_loss"), 1500.0), 1.0)
    dd_pressure = _clamp(drawdown / max_dd, 0.0, 1.0)
    daily_pressure = _clamp(daily / max_daily, 0.0, 1.0)
    pressure = max(dd_pressure, daily_pressure)
    return round(_clamp(1.0 - pressure * 0.75, 0.15, 1.0), 4)


def _capital_context(state: Dict[str, Any]) -> Dict[str, float]:
    alloc = _f((((state or {}).get("allocator_caps") or {}).get("operator") or {}).get("allocated_capital"))
    latest = ((state or {}).get("monitoring") or {}).get("latest_snapshot") or {}
    used = _f(latest.get("used_capital"))
    if used <= 0:
        positions = latest.get("positions") or []
        used = round(sum(abs(_f(p.get("market_value"))) for p in positions), 2)
    remaining = max(0.0, round(alloc - used, 2))
    return {
        "allocated_capital": round(alloc, 2),
        "used_capital": round(used, 2),
        "remaining_capital": round(remaining, 2),
    }


def build_decision_snapshot(state: Dict[str, Any], signal_book: Dict[str, Any], market_bias: str = "neutral") -> Dict[str, Any]:
    risk = (state or {}).get("risk_engine") or {}
    capital = _capital_context(state)
    signals = list((signal_book or {}).get("signals") or [])
    risk_mult = _risk_multiplier(risk)
    max_notional_per_trade = max(_f(risk.get("max_notional_per_trade"), 20.0), 1.0)
    max_orders_per_run = max(int(risk.get("max_orders_per_run") or 3), 1)
    base_budget = capital["remaining_capital"] if capital["remaining_capital"] > 0 else capital["allocated_capital"] * 0.1
    deployment_budget = round(max(0.0, base_budget) * risk_mult, 2)

    ranked: List[Dict[str, Any]] = []
    for signal in signals:
        current_price = max(_f(signal.get("current_price"), 0.0), 0.0001)
        confidence = _clamp(_f(signal.get("confidence"), 0.0), 0.0, 1.0)
        action = signal.get("signal_action") or "hold"

        if action in {"stop_exit", "take_profit"}:
            recommended_notional = round(abs(_f(signal.get("position_qty"))) * current_price, 2)
            recommended_qty = round(abs(_f(signal.get("position_qty"))), 6)
            decision = "execute"
            risk_score = "exit"
            allocation_pct = 0.0
        elif action == "hold":
            recommended_notional = 0.0
            recommended_qty = 0.0
            decision = "hold"
            risk_score = "idle"
            allocation_pct = 0.0
        else:
            target_pct = _clamp(0.015 + confidence * 0.08, 0.01, 0.10)
            desired_notional = round(capital["allocated_capital"] * target_pct * risk_mult, 2)
            recommended_notional = round(min(max_notional_per_trade, desired_notional) if capital["allocated_capital"] > 0 else 0.0, 2)
            if deployment_budget <= 0 or recommended_notional <= 0:
                recommended_qty = 0.0
                decision = "skip"
            else:
                recommended_qty = round(min(recommended_notional, deployment_budget) / current_price, 6)
                decision = "execute" if confidence >= 0.55 and recommended_qty > 0 else "skip"
            if risk_mult >= 0.8:
                risk_score = "low"
            elif risk_mult >= 0.45:
                risk_score = "medium"
            else:
                risk_score = "high"
            allocation_pct = round((min(recommended_notional, capital["allocated_capital"]) / capital["allocated_capital"]), 4) if capital["allocated_capital"] > 0 else 0.0

        row = {
            **signal,
            "decision": decision,
            "risk_score": risk_score,
            "allocation_pct": allocation_pct,
            "recommended_notional": recommended_notional,
            "recommended_qty": recommended_qty,
            "decision_generated_at": _now(),
        }
        ranked.append(row)

    ranked.sort(key=lambda r: (r.get("decision") != "execute", -(r.get("confidence") or 0.0)))
    executable = [r for r in ranked if r.get("decision") == "execute"][:max_orders_per_run]
    blocked = [r for r in ranked if r.get("decision") == "skip"]

    allocations = []
    deployed = 0.0
    if executable and capital["allocated_capital"] > 0:
        total_conf = sum(max(_f(r.get("confidence")), 0.01) for r in executable) or 1.0
        for row in executable:
            share = round(max(_f(row.get("confidence")), 0.01) / total_conf, 4)
            alloc_cap = round(min(deployment_budget, capital["remaining_capital"] if capital["remaining_capital"] > 0 else deployment_budget) * share, 2)
            deployed += alloc_cap
            allocations.append({
                "strategy_id": row.get("strategy_id"),
                "symbol": row.get("symbol"),
                "share": share,
                "assigned_capital": alloc_cap,
                "recommended_qty": row.get("recommended_qty"),
                "decision": row.get("decision"),
            })

    return {
        "generated_at": _now(),
        "market_bias": market_bias,
        "capital": {
            **capital,
            "deployment_budget": round(deployment_budget, 2),
            "deployed_capital": round(deployed, 2),
        },
        "risk": {
            "kill_switch_active": bool(risk.get("kill_switch_active")),
            "breached": bool(risk.get("breached")),
            "risk_multiplier": risk_mult,
            "max_orders_per_run": max_orders_per_run,
            "max_notional_per_trade": round(max_notional_per_trade, 2),
        },
        "summary": {
            "signals": len(ranked),
            "actionable_signals": len([r for r in ranked if r.get("signal_action") != "hold"]),
            "executable_signals": len(executable),
            "blocked_signals": len(blocked),
        },
        "decisions": ranked,
        "allocations": allocations,
    }
