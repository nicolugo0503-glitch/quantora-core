from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def default_broker_abstraction() -> Dict[str, Any]:
    return {
        "version": "30352",
        "default_broker": "alpaca",
        "default_market": "equities",
        "routing_policy": "best_available",
        "max_cross_market_allocation_pct": 35.0,
        "brokers": {
            "alpaca": {
                "broker_id": "alpaca",
                "enabled": True,
                "markets": ["equities", "crypto"],
                "live_supported": True,
                "paper_supported": True,
                "base_fee_bps": 0.8,
                "latency_ms": 95,
                "reliability_score": 0.985,
                "slippage_penalty_bps": 1.5,
                "notes": "primary live equities broker",
            },
            "sim-crypto": {
                "broker_id": "sim-crypto",
                "enabled": True,
                "markets": ["crypto"],
                "live_supported": False,
                "paper_supported": True,
                "base_fee_bps": 4.0,
                "latency_ms": 70,
                "reliability_score": 0.965,
                "slippage_penalty_bps": 3.8,
                "notes": "simulation venue for digital assets",
            },
            "sim-futures": {
                "broker_id": "sim-futures",
                "enabled": True,
                "markets": ["futures"],
                "live_supported": False,
                "paper_supported": True,
                "base_fee_bps": 2.2,
                "latency_ms": 88,
                "reliability_score": 0.972,
                "slippage_penalty_bps": 2.4,
                "notes": "simulation venue for futures expansion",
            },
            "sim-forex": {
                "broker_id": "sim-forex",
                "enabled": True,
                "markets": ["forex"],
                "live_supported": False,
                "paper_supported": True,
                "base_fee_bps": 1.3,
                "latency_ms": 62,
                "reliability_score": 0.978,
                "slippage_penalty_bps": 1.9,
                "notes": "simulation venue for fx expansion",
            },
        },
        "markets": {
            "equities": {
                "market_id": "equities",
                "enabled": True,
                "symbols": ["AAPL", "MSFT", "NVDA", "SPY", "TSLA"],
                "default_order_type": "limit",
                "session_profile": "cash",
                "risk_multiplier": 1.0,
            },
            "crypto": {
                "market_id": "crypto",
                "enabled": True,
                "symbols": ["BTCUSD", "ETHUSD", "SOLUSD"],
                "default_order_type": "limit",
                "session_profile": "24x7",
                "risk_multiplier": 1.25,
            },
            "futures": {
                "market_id": "futures",
                "enabled": True,
                "symbols": ["ES", "NQ", "CL"],
                "default_order_type": "limit",
                "session_profile": "extended",
                "risk_multiplier": 1.4,
            },
            "forex": {
                "market_id": "forex",
                "enabled": True,
                "symbols": ["EURUSD", "USDJPY", "GBPUSD"],
                "default_order_type": "market",
                "session_profile": "24x5",
                "risk_multiplier": 1.15,
            },
        },
        "portfolio_expansion": {
            "allocations": {
                "equities": 70.0,
                "crypto": 10.0,
                "futures": 10.0,
                "forex": 10.0,
            },
            "target_markets": ["equities", "crypto", "futures", "forex"],
            "last_expansion_at": None,
            "last_route_at": None,
        },
        "telemetry": {
            "routes_evaluated": 0,
            "routes_executed": 0,
            "rejected_routes": 0,
            "last_route_at": None,
            "last_best_broker": None,
            "recent_routes": [],
        },
    }


def broker_abstraction_state_view(data: Dict[str, Any] | None) -> Dict[str, Any]:
    base = default_broker_abstraction()
    current = data or {}
    for key, value in current.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            merged = dict(base[key])
            merged.update(value)
            base[key] = merged
        else:
            base[key] = value
    for broker_id, broker in default_broker_abstraction()["brokers"].items():
        base.setdefault("brokers", {}).setdefault(broker_id, broker)
    for market_id, market in default_broker_abstraction()["markets"].items():
        base.setdefault("markets", {}).setdefault(market_id, market)
    base.setdefault("telemetry", {}).setdefault("recent_routes", [])
    return base


def _allowed_brokers(state: Dict[str, Any], market: str, execution_mode: str) -> List[Dict[str, Any]]:
    items = []
    for broker in state.get("brokers", {}).values():
        if not broker.get("enabled"):
            continue
        if market not in broker.get("markets", []):
            continue
        if execution_mode == "live" and not broker.get("live_supported"):
            continue
        if execution_mode != "live" and not broker.get("paper_supported", True):
            continue
        items.append(broker)
    return items


def _score_broker(broker: Dict[str, Any], *, notional: float, urgency: str) -> float:
    urgency_penalty = {"patient": -0.25, "balanced": 0.0, "aggressive": 0.35}.get((urgency or "balanced").lower(), 0.0)
    notional_penalty = min(2.5, max(notional, 0.0) / 100000.0)
    fee = float(broker.get("base_fee_bps", 0.0))
    latency = float(broker.get("latency_ms", 0.0)) / 100.0
    slippage = float(broker.get("slippage_penalty_bps", 0.0)) / 2.5
    reliability = (1.0 - float(broker.get("reliability_score", 0.95))) * 40.0
    return round(fee + latency + slippage + reliability + urgency_penalty + notional_penalty, 4)


def broker_route_evaluate(
    state: Dict[str, Any],
    *,
    market: str,
    symbol: str,
    side: str,
    qty: float,
    execution_mode: str,
    urgency: str,
    preferred_broker: str | None = None,
) -> Dict[str, Any]:
    market = (market or state.get("default_market") or "equities").lower()
    execution_mode = (execution_mode or "paper").lower()
    qty = max(float(qty or 0.0), 0.0)
    market_cfg = state.get("markets", {}).get(market, {})
    risk_multiplier = float(market_cfg.get("risk_multiplier", 1.0))
    base_price_map = {
        "BTCUSD": 68000.0,
        "ETHUSD": 3400.0,
        "SOLUSD": 155.0,
        "ES": 5300.0,
        "NQ": 18500.0,
        "CL": 78.0,
        "EURUSD": 1.08,
        "USDJPY": 151.0,
        "GBPUSD": 1.27,
    }
    reference_price = float(base_price_map.get((symbol or "").upper(), 180.0 if market == "equities" else 100.0))
    notional = round(reference_price * qty, 2)
    candidates = []
    for broker in _allowed_brokers(state, market, execution_mode):
        route_score = _score_broker(broker, notional=notional, urgency=urgency)
        candidates.append({
            "broker_id": broker["broker_id"],
            "score": route_score,
            "fee_bps": float(broker.get("base_fee_bps", 0.0)),
            "latency_ms": int(broker.get("latency_ms", 0)),
            "reliability_score": float(broker.get("reliability_score", 0.95)),
            "slippage_penalty_bps": float(broker.get("slippage_penalty_bps", 0.0)),
            "market_supported": True,
        })
    candidates.sort(key=lambda x: x["score"])
    if preferred_broker:
        preferred = next((c for c in candidates if c["broker_id"] == preferred_broker), None)
        if preferred is not None:
            candidates.remove(preferred)
            candidates.insert(0, preferred)
    if not candidates:
        state.setdefault("telemetry", {}).setdefault("rejected_routes", 0)
        state["telemetry"]["rejected_routes"] += 1
        return {
            "status": "rejected",
            "reason": f"no broker available for market={market} mode={execution_mode}",
            "market": market,
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "notional": notional,
            "candidates": [],
        }
    best = candidates[0]
    state.setdefault("telemetry", {}).setdefault("routes_evaluated", 0)
    state["telemetry"]["routes_evaluated"] += 1
    state["telemetry"]["last_route_at"] = now_iso()
    state["telemetry"]["last_best_broker"] = best["broker_id"]
    route = {
        "status": "ok",
        "generated_at": now_iso(),
        "market": market,
        "market_profile": market_cfg,
        "symbol": (symbol or "").upper(),
        "side": (side or "buy").lower(),
        "qty": round(qty, 6),
        "reference_price": reference_price,
        "notional": notional,
        "execution_mode": execution_mode,
        "urgency": urgency,
        "risk_adjusted_notional": round(notional * risk_multiplier, 2),
        "selected_broker": best,
        "alternatives": candidates[1:4],
        "default_order_type": market_cfg.get("default_order_type", "limit"),
        "routing_policy": state.get("routing_policy", "best_available"),
    }
    state["telemetry"].setdefault("recent_routes", []).insert(0, route)
    state["telemetry"]["recent_routes"] = state["telemetry"]["recent_routes"][:50]
    return route


def broker_route_record_execution(state: Dict[str, Any], route: Dict[str, Any]) -> Dict[str, Any]:
    state.setdefault("telemetry", {}).setdefault("routes_executed", 0)
    state["telemetry"]["routes_executed"] += 1
    state["portfolio_expansion"]["last_route_at"] = now_iso()
    return {
        "status": "recorded",
        "broker_id": route.get("selected_broker", {}).get("broker_id"),
        "market": route.get("market"),
        "symbol": route.get("symbol"),
        "notional": route.get("notional"),
        "recorded_at": now_iso(),
    }


def broker_abstraction_summary(state: Dict[str, Any]) -> Dict[str, Any]:
    enabled_markets = [m for m, v in state.get("markets", {}).items() if v.get("enabled")]
    enabled_brokers = [b for b, v in state.get("brokers", {}).items() if v.get("enabled")]
    allocations = state.get("portfolio_expansion", {}).get("allocations", {})
    return {
        "enabled_markets": enabled_markets,
        "enabled_brokers": enabled_brokers,
        "market_count": len(enabled_markets),
        "broker_count": len(enabled_brokers),
        "default_broker": state.get("default_broker"),
        "default_market": state.get("default_market"),
        "cross_market_allocations": allocations,
        "routes_evaluated": int(state.get("telemetry", {}).get("routes_evaluated", 0)),
        "routes_executed": int(state.get("telemetry", {}).get("routes_executed", 0)),
        "last_best_broker": state.get("telemetry", {}).get("last_best_broker"),
    }


def market_upsert(state: Dict[str, Any], market_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    market_id = (market_id or payload.get("market_id") or "custom").lower()
    current = state.setdefault("markets", {}).get(market_id, {"market_id": market_id})
    current.update({k: v for k, v in payload.items() if v is not None})
    current["market_id"] = market_id
    state["markets"][market_id] = current
    return current


def broker_upsert(state: Dict[str, Any], broker_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    broker_id = (broker_id or payload.get("broker_id") or "custom").lower()
    current = state.setdefault("brokers", {}).get(broker_id, {"broker_id": broker_id})
    current.update({k: v for k, v in payload.items() if v is not None})
    current["broker_id"] = broker_id
    state["brokers"][broker_id] = current
    return current


def portfolio_expand(state: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    allocations = payload.get("allocations") or {}
    total = round(sum(float(v or 0.0) for v in allocations.values()), 2)
    expansion = state.setdefault("portfolio_expansion", {})
    if allocations:
        expansion["allocations"] = {str(k).lower(): round(float(v or 0.0), 2) for k, v in allocations.items()}
    if payload.get("target_markets"):
        expansion["target_markets"] = [str(x).lower() for x in payload.get("target_markets")]
    expansion["last_expansion_at"] = now_iso()
    return {
        "status": "updated",
        "allocations": expansion.get("allocations", {}),
        "target_markets": expansion.get("target_markets", []),
        "allocation_total": total,
        "within_policy": total <= 100.0,
        "updated_at": expansion.get("last_expansion_at"),
    }
