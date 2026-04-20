import datetime
from typing import Any, Dict, List, Tuple


PRICE_BOOK_DEFAULT = {
    "AAPL": 180.0,
    "TSLA": 175.0,
    "SPY": 510.0,
    "NVDA": 910.0,
    "MSFT": 420.0,
    "AMZN": 185.0,
    "META": 505.0,
}


def now_iso() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def _price_book(state: Dict[str, Any]) -> Dict[str, float]:
    custom = state.get("price_book") or {}
    merged = dict(PRICE_BOOK_DEFAULT)
    for k, v in custom.items():
        merged[str(k).upper()] = _as_float(v, PRICE_BOOK_DEFAULT.get(str(k).upper(), 100.0))
    return merged


def _fill_price(order: Dict[str, Any], price_book: Dict[str, float]) -> float:
    qty = _as_float(order.get("qty"), 0.0)
    if qty > 0 and _as_float(order.get("notional"), 0.0) > 0:
        return round(_as_float(order.get("notional")) / qty, 6)
    raw = (order.get("raw") or {}) if isinstance(order.get("raw"), dict) else {}
    for key in ("filled_avg_price", "limit_price", "price"):
        if raw.get(key):
            return _as_float(raw.get(key), price_book.get(str(order.get("symbol") or "").upper(), 100.0))
    return price_book.get(str(order.get("symbol") or "").upper(), 100.0)


def _event_time(order: Dict[str, Any]) -> str:
    return str(order.get("timestamp") or order.get("submitted_at") or order.get("created_at") or "")


def _mode_latency_ms(order: Dict[str, Any]) -> int:
    mode = str(order.get("mode") or order.get("broker") or "internal").lower()
    if mode in {"live", "alpaca"}:
        return 95
    if mode == "paper":
        return 35
    return 18


def _slippage_bps(order: Dict[str, Any]) -> float:
    direct = order.get("estimated_slippage_bps")
    if direct not in (None, ""):
        return round(_as_float(direct), 2)
    plan = order.get("execution_plan") or {}
    if isinstance(plan, dict) and plan.get("estimated_slippage_bps") not in (None, ""):
        return round(_as_float(plan.get("estimated_slippage_bps")), 2)
    mode = str(order.get("mode") or order.get("broker") or "internal").lower()
    return 4.0 if mode in {"internal", "paper"} else 11.0


def _execution_quality(order: Dict[str, Any]) -> float:
    slippage = _slippage_bps(order)
    latency = _mode_latency_ms(order)
    penalty = (slippage * 1.9) + (latency * 0.09)
    if str(order.get("status") or "").lower() not in {"filled", "accepted", "new", "submitted", "partially_filled"}:
        penalty += 12
    return round(max(0.0, min(100.0, 100.0 - penalty)), 2)


def _regime_tag(state: Dict[str, Any]) -> str:
    risk = state.get("risk_engine") or {}
    if risk.get("kill_switch_active"):
        return "kill-switch"
    drawdown = _as_float(risk.get("current_drawdown_pct"), 0.0)
    if drawdown >= 8:
        return "risk-off"
    monitoring = state.get("monitoring") or {}
    alerts = monitoring.get("alerts") or []
    critical = [a for a in alerts if str(a.get("level") or "").lower() == "critical"]
    if critical:
        return "defensive"
    if state.get("strategy_loop", {}).get("running"):
        return "active"
    return "neutral"


def _iter_orders(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    orders = state.get("orders") or {}
    items = orders.get("orders") if isinstance(orders, dict) else orders
    if not isinstance(items, list):
        return []
    valid = [o for o in items if isinstance(o, dict)]
    return sorted(valid, key=_event_time)


def _strategy_lookup(state: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    strategies = (state.get("strategies") or {}).get("strategies") or []
    return {s.get("strategy_id"): s for s in strategies if isinstance(s, dict) and s.get("strategy_id")}


def _portfolio_context(state: Dict[str, Any]) -> Dict[str, float]:
    cap = (state.get("allocator_caps") or {}).get("operator") or {}
    allocated = _as_float(cap.get("allocated_capital"), 0.0)
    risk = state.get("risk_engine") or {}
    used = _as_float(risk.get("current_total_exposure"), 0.0)
    daily_realized = _as_float(risk.get("current_daily_realized_pnl"), 0.0)
    drawdown = _as_float(risk.get("current_drawdown_pct"), 0.0)
    remaining = max(allocated - used, 0.0)
    utilization = round((used / allocated) * 100, 2) if allocated > 0 else 0.0
    return {
        "allocated_capital": round(allocated, 2),
        "used_capital": round(used, 2),
        "remaining_capital": round(remaining, 2),
        "utilization_pct": utilization,
        "daily_realized_pnl": round(daily_realized, 2),
        "drawdown_pct": round(drawdown, 2),
    }


def build_attribution_snapshot(state: Dict[str, Any]) -> Dict[str, Any]:
    price_book = _price_book(state)
    orders = _iter_orders(state)
    strategies = _strategy_lookup(state)
    regime = _regime_tag(state)

    lots: Dict[Tuple[str, str], Dict[str, float]] = {}
    strategy_rows: Dict[str, Dict[str, Any]] = {}
    execution_buckets: Dict[str, Dict[str, Any]] = {}
    symbol_rows: Dict[str, Dict[str, Any]] = {}
    trade_rows: List[Dict[str, Any]] = []
    realized_total = 0.0
    total_quality = 0.0
    total_slippage = 0.0
    venues = set()

    for idx, order in enumerate(orders, start=1):
        strategy_id = order.get("strategy_id") or "manual"
        strategy = strategies.get(strategy_id, {})
        symbol = str(order.get("symbol") or "UNKNOWN").upper()
        qty = abs(_as_float(order.get("qty"), 0.0))
        side = str(order.get("side") or "buy").lower()
        fill_price = _fill_price(order, price_book)
        notional = round(_as_float(order.get("notional"), qty * fill_price), 2)
        slippage = _slippage_bps(order)
        latency = _mode_latency_ms(order)
        quality = _execution_quality(order)
        venues.add(str(order.get("broker") or order.get("mode") or "internal"))

        row = strategy_rows.setdefault(
            strategy_id,
            {
                "strategy_id": strategy_id,
                "strategy_name": strategy.get("name") or ("Manual Flow" if strategy_id == "manual" else strategy_id),
                "symbol": strategy.get("symbol") or symbol,
                "orders_count": 0,
                "buy_orders": 0,
                "sell_orders": 0,
                "realized_pnl": 0.0,
                "gross_notional": 0.0,
                "wins": 0,
                "losses": 0,
                "capital_used": 0.0,
                "avg_execution_quality": 0.0,
                "avg_slippage_bps": 0.0,
                "regime_tag": regime,
            },
        )
        row["orders_count"] += 1
        row["gross_notional"] = round(row["gross_notional"] + notional, 2)
        row["capital_used"] = round(max(row["capital_used"], notional), 2)
        row["buy_orders"] += 1 if side == "buy" else 0
        row["sell_orders"] += 1 if side == "sell" else 0
        row["avg_execution_quality"] += quality
        row["avg_slippage_bps"] += slippage

        bucket_key = f"{strategy_id}:{symbol}"
        lot = lots.setdefault(bucket_key, {"qty": 0.0, "avg_cost": 0.0})
        realized = 0.0
        if side == "buy":
            new_qty = lot["qty"] + qty
            if new_qty > 0:
                lot["avg_cost"] = ((lot["qty"] * lot["avg_cost"]) + (qty * fill_price)) / new_qty
            lot["qty"] = new_qty
        else:
            close_qty = min(lot["qty"], qty)
            realized = round((fill_price - lot["avg_cost"]) * close_qty, 2)
            lot["qty"] = max(0.0, lot["qty"] - close_qty)
            if lot["qty"] == 0:
                lot["avg_cost"] = 0.0
            row["wins"] += 1 if realized > 0 else 0
            row["losses"] += 1 if realized < 0 else 0

        row["realized_pnl"] = round(row["realized_pnl"] + realized, 2)
        realized_total += realized
        total_quality += quality
        total_slippage += slippage

        exe_key = str(order.get("broker") or order.get("mode") or "internal")
        exe = execution_buckets.setdefault(
            exe_key,
            {
                "execution_venue": exe_key,
                "orders_count": 0,
                "filled_notional": 0.0,
                "avg_slippage_bps": 0.0,
                "avg_latency_ms": 0.0,
                "avg_execution_quality": 0.0,
            },
        )
        exe["orders_count"] += 1
        exe["filled_notional"] = round(exe["filled_notional"] + notional, 2)
        exe["avg_slippage_bps"] += slippage
        exe["avg_latency_ms"] += latency
        exe["avg_execution_quality"] += quality

        sym = symbol_rows.setdefault(symbol, {"symbol": symbol, "gross_notional": 0.0, "realized_pnl": 0.0, "orders_count": 0})
        sym["gross_notional"] = round(sym["gross_notional"] + notional, 2)
        sym["realized_pnl"] = round(sym["realized_pnl"] + realized, 2)
        sym["orders_count"] += 1

        trade_rows.append(
            {
                "trade_id": order.get("order_id") or f"trade_{idx:04d}",
                "timestamp": _event_time(order),
                "strategy_id": strategy_id,
                "strategy_name": row["strategy_name"],
                "symbol": symbol,
                "side": side,
                "qty": qty,
                "fill_price": round(fill_price, 4),
                "notional": notional,
                "realized_pnl": realized,
                "slippage_bps": slippage,
                "latency_ms": latency,
                "execution_quality": quality,
                "venue": exe_key,
                "regime_tag": regime,
            }
        )

    for row in strategy_rows.values():
        count = max(1, row["orders_count"])
        row["avg_execution_quality"] = round(row["avg_execution_quality"] / count, 2)
        row["avg_slippage_bps"] = round(row["avg_slippage_bps"] / count, 2)
        row["win_rate_pct"] = round((row["wins"] / max(1, row["sell_orders"])) * 100, 2) if row["sell_orders"] else 0.0
        row["pnl_per_notional_bps"] = round((row["realized_pnl"] / row["gross_notional"]) * 10000, 2) if row["gross_notional"] else 0.0
        row["promotion_signal"] = "promote" if row["realized_pnl"] > 0 and row["avg_execution_quality"] >= 80 else ("review" if row["realized_pnl"] >= 0 else "retire")

    for row in execution_buckets.values():
        count = max(1, row["orders_count"])
        row["avg_slippage_bps"] = round(row["avg_slippage_bps"] / count, 2)
        row["avg_latency_ms"] = round(row["avg_latency_ms"] / count, 2)
        row["avg_execution_quality"] = round(row["avg_execution_quality"] / count, 2)

    strategy_list = sorted(strategy_rows.values(), key=lambda r: (r["realized_pnl"], r["avg_execution_quality"]), reverse=True)
    execution_list = sorted(execution_buckets.values(), key=lambda r: r["filled_notional"], reverse=True)
    symbol_list = sorted(symbol_rows.values(), key=lambda r: r["gross_notional"], reverse=True)
    portfolio = _portfolio_context(state)
    avg_quality = round(total_quality / max(1, len(orders)), 2)
    avg_slippage = round(total_slippage / max(1, len(orders)), 2)
    active_strategies = len([s for s in (state.get("strategies") or {}).get("strategies", []) if s.get("enabled") and s.get("status") == "running" and not s.get("deleted")])
    top_strategy = strategy_list[0] if strategy_list else None

    return {
        "mission": "QNT30418",
        "generated_at": now_iso(),
        "summary": {
            "regime_tag": regime,
            "orders_analyzed": len(orders),
            "strategies_analyzed": len(strategy_list),
            "active_strategies": active_strategies,
            "realized_pnl": round(realized_total, 2),
            "execution_quality_avg": avg_quality,
            "slippage_bps_avg": avg_slippage,
            "venues_used": len(venues),
            "top_strategy": top_strategy["strategy_name"] if top_strategy else None,
            **portfolio,
            "capital_efficiency_pct": round((realized_total / portfolio["used_capital"]) * 100, 2) if portfolio["used_capital"] else 0.0,
        },
        "strategy_attribution": strategy_list,
        "execution_attribution": {
            "venues": execution_list,
            "recent_trades": list(reversed(trade_rows[-25:])),
        },
        "portfolio_attribution": {
            **portfolio,
            "contribution_by_symbol": symbol_list,
        },
        "trade_attribution": list(reversed(trade_rows[-100:])),
        "investor_brief": {
            "headline": f"Regime {regime} · {len(orders)} orders analyzed · realized PnL {round(realized_total, 2)}",
            "best_strategy": top_strategy,
            "capital_efficiency_pct": round((realized_total / portfolio["used_capital"]) * 100, 2) if portfolio["used_capital"] else 0.0,
        },
    }
