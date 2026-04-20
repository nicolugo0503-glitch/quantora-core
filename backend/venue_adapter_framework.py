
import math
from datetime import datetime, timezone

DEFAULT_SYMBOL_MAP = {
    "AAPL": {"equities": "AAPL", "crypto": "AAPL/USD", "forex": "AAPL_SYNTH", "futures": "AAPL.FUT"},
    "BTCUSD": {"crypto": "BTC/USD", "equities": "BTC-ETF", "forex": "BTCUSD", "futures": "BTC.FUT"},
    "ETHUSD": {"crypto": "ETH/USD", "equities": "ETH-ETF", "forex": "ETHUSD", "futures": "ETH.FUT"},
    "EURUSD": {"forex": "EUR/USD", "crypto": "EURUSD", "equities": "FXE", "futures": "6E"},
    "NQ": {"futures": "NQ", "equities": "QQQ", "crypto": "NQ_SYNTH", "forex": "NQ_SYNTH"},
}

DEFAULT_ORDER_SCHEMAS = {
    "alpaca": {"side_field": "side", "qty_field": "qty", "type_field": "type", "time_in_force_field": "time_in_force"},
    "binance": {"side_field": "side", "qty_field": "quantity", "type_field": "type", "time_in_force_field": "timeInForce"},
    "oanda": {"side_field": "units_sign", "qty_field": "units", "type_field": "type", "time_in_force_field": "timeInForce"},
    "ibkr": {"side_field": "action", "qty_field": "totalQuantity", "type_field": "orderType", "time_in_force_field": "tif"},
}

def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def default_venue_adapter_state():
    return {
        "enabled": True,
        "last_updated_at": None,
        "last_normalized_at": None,
        "last_schema_at": None,
        "last_market_data_at": None,
        "normalizations": 0,
        "schemas_prepared": 0,
        "market_snapshots": 0,
        "venue_registry": {
            "alpaca": {"venue_id": "alpaca", "asset_classes": ["equities", "crypto"], "latency_ms": 42, "status": "active"},
            "binance": {"venue_id": "binance", "asset_classes": ["crypto"], "latency_ms": 28, "status": "standby"},
            "oanda": {"venue_id": "oanda", "asset_classes": ["forex"], "latency_ms": 34, "status": "standby"},
            "ibkr": {"venue_id": "ibkr", "asset_classes": ["equities", "futures", "forex"], "latency_ms": 57, "status": "standby"},
        },
        "symbol_map": DEFAULT_SYMBOL_MAP.copy(),
        "order_schemas": DEFAULT_ORDER_SCHEMAS.copy(),
        "market_data": {
            "equities": {"default_source": "iex-sim", "top_of_book_latency_ms": 25},
            "crypto": {"default_source": "binance-sim", "top_of_book_latency_ms": 18},
            "forex": {"default_source": "oanda-sim", "top_of_book_latency_ms": 22},
            "futures": {"default_source": "cme-sim", "top_of_book_latency_ms": 20},
        },
        "telemetry": [],
    }

def venue_adapter_state_view(data):
    merged = default_venue_adapter_state()
    incoming = (data or {}).get("venue_adapter_framework", data or {})
    if isinstance(incoming, dict):
        for k, v in incoming.items():
            if isinstance(v, dict) and isinstance(merged.get(k), dict):
                merged[k].update(v)
            else:
                merged[k] = v
    return merged

def normalize_symbol(state, *, canonical_symbol, target_market="equities", venue_id=None):
    target_market = (target_market or "equities").lower()
    venue_id = (venue_id or "").lower() or None
    canonical = (canonical_symbol or "").upper().replace("/", "").replace("-", "")
    symbol_map = state.setdefault("symbol_map", {})
    mapping = symbol_map.get(canonical) or {target_market: canonical_symbol}
    normalized = mapping.get(target_market) or canonical_symbol
    state["last_normalized_at"] = now_iso()
    state["normalizations"] = int(state.get("normalizations") or 0) + 1
    event = {
        "timestamp": now_iso(),
        "type": "normalize_symbol",
        "canonical_symbol": canonical_symbol,
        "target_market": target_market,
        "venue_id": venue_id,
        "normalized_symbol": normalized,
    }
    state.setdefault("telemetry", []).insert(0, event)
    state["telemetry"] = state.get("telemetry", [])[:100]
    return {
        "status": "ok",
        "canonical_symbol": canonical_symbol,
        "target_market": target_market,
        "venue_id": venue_id,
        "normalized_symbol": normalized,
        "mapping": mapping,
    }

def prepare_order_schema(state, *, venue_id, symbol, side, qty, order_type="market", tif="day", price=None):
    venue_id = (venue_id or "alpaca").lower()
    schema = state.setdefault("order_schemas", {}).get(venue_id) or DEFAULT_ORDER_SCHEMAS["alpaca"]
    order = {
        schema["side_field"]: str(side or "buy").lower() if venue_id != "ibkr" else str(side or "BUY").upper(),
        schema["qty_field"]: round(float(qty or 0.0), 8),
        schema["type_field"]: str(order_type or "market").lower() if venue_id != "ibkr" else str(order_type or "MKT").upper(),
        schema["time_in_force_field"]: tif,
        "symbol": symbol,
    }
    if price not in (None, ""):
        order["limit_price"] = float(price)
    state["last_schema_at"] = now_iso()
    state["schemas_prepared"] = int(state.get("schemas_prepared") or 0) + 1
    event = {"timestamp": now_iso(), "type": "prepare_order_schema", "venue_id": venue_id, "symbol": symbol, "order_type": order_type}
    state.setdefault("telemetry", []).insert(0, event)
    state["telemetry"] = state.get("telemetry", [])[:100]
    return {
        "status": "ok",
        "venue_id": venue_id,
        "schema": schema,
        "normalized_order": order,
    }

def market_data_snapshot(state, *, symbol, market="equities", venue_id=None, mid_price=None, spread_bps=None, volatility_score=None):
    market = (market or "equities").lower()
    venue_id = (venue_id or state.get("market_data", {}).get(market, {}).get("default_source") or "sim").lower()
    seed = abs(hash(f"{symbol}:{market}:{venue_id}")) % 1000
    if mid_price in (None, ""):
        base_price = {"equities": 180.0, "crypto": 64000.0, "forex": 1.0825, "futures": 18650.0}.get(market, 100.0)
        mid_price = round(base_price * (1 + ((seed % 17) - 8) / 1000.0), 6)
    else:
        mid_price = float(mid_price)
    if spread_bps in (None, ""):
        spread_bps = round({"equities": 1.8, "crypto": 3.4, "forex": 1.2, "futures": 1.6}.get(market, 2.0) + (seed % 5) * 0.3, 2)
    else:
        spread_bps = float(spread_bps)
    if volatility_score in (None, ""):
        volatility_score = round(0.6 + ((seed % 9) * 0.17), 2)
    else:
        volatility_score = float(volatility_score)
    bid = round(mid_price * (1 - spread_bps / 20000.0), 6)
    ask = round(mid_price * (1 + spread_bps / 20000.0), 6)
    snapshot = {
        "timestamp": now_iso(),
        "symbol": symbol,
        "market": market,
        "venue_id": venue_id,
        "bid": bid,
        "ask": ask,
        "mid": round((bid + ask) / 2.0, 6),
        "spread_bps": spread_bps,
        "volatility_score": volatility_score,
        "latency_ms": int(state.get("market_data", {}).get(market, {}).get("top_of_book_latency_ms") or 25),
        "quality_score": max(0.0, round(100 - spread_bps * 5 - volatility_score * 8, 2)),
    }
    state["last_market_data_at"] = now_iso()
    state["market_snapshots"] = int(state.get("market_snapshots") or 0) + 1
    state.setdefault("telemetry", []).insert(0, {"timestamp": now_iso(), "type": "market_data_snapshot", "symbol": symbol, "market": market, "venue_id": venue_id})
    state["telemetry"] = state.get("telemetry", [])[:100]
    return {"status": "ok", "snapshot": snapshot}

def venue_register(state, *, venue_id, asset_classes=None, latency_ms=50, status="active"):
    venue_id = (venue_id or "").lower()
    if not venue_id:
        raise ValueError("venue_id required")
    venue = {
        "venue_id": venue_id,
        "asset_classes": list(asset_classes or ["equities"]),
        "latency_ms": int(latency_ms or 50),
        "status": status or "active",
        "updated_at": now_iso(),
    }
    state.setdefault("venue_registry", {})[venue_id] = venue
    state["last_updated_at"] = now_iso()
    return {"status": "registered", "venue": venue}

def venue_adapter_summary(state):
    venues = state.get("venue_registry", {})
    by_market = {}
    for venue in venues.values():
        for asset in venue.get("asset_classes", []):
            by_market[asset] = by_market.get(asset, 0) + 1
    return {
        "status": "ok",
        "venues_total": len(venues),
        "markets_covered": sorted(by_market.keys()),
        "coverage_counts": by_market,
        "last_updated_at": state.get("last_updated_at"),
        "last_normalized_at": state.get("last_normalized_at"),
        "last_market_data_at": state.get("last_market_data_at"),
        "normalizations": int(state.get("normalizations") or 0),
        "schemas_prepared": int(state.get("schemas_prepared") or 0),
        "market_snapshots": int(state.get("market_snapshots") or 0),
        "telemetry": state.get("telemetry", [])[:20],
    }
