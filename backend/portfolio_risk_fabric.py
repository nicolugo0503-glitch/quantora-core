import math
from datetime import datetime, timezone

def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')

DEFAULT_LIMITS = {
    "gross_notional_limit": 500000.0,
    "net_notional_limit": 250000.0,
    "single_symbol_limit": 100000.0,
    "market_limits": {
        "equities": 250000.0,
        "crypto": 100000.0,
        "forex": 150000.0,
        "futures": 150000.0,
    },
    "max_correlated_group_exposure": 180000.0,
    "max_leverage_proxy": 2.5,
}

CORRELATION_GROUPS = {
    "AAPL": "mega_cap_tech",
    "MSFT": "mega_cap_tech",
    "NVDA": "mega_cap_tech",
    "META": "mega_cap_tech",
    "AMZN": "mega_cap_tech",
    "TSLA": "high_beta_growth",
    "SPY": "index_beta",
    "QQQ": "index_beta",
    "BTCUSD": "crypto_beta",
    "ETHUSD": "crypto_beta",
    "EURUSD": "usd_fx",
    "USDJPY": "usd_fx",
    "ES1!": "us_index_futures",
    "NQ1!": "us_index_futures",
}

def default_portfolio_risk_state():
    return {
        "enabled": True,
        "last_updated_at": None,
        "last_snapshot_at": None,
        "last_netting_at": None,
        "limits": DEFAULT_LIMITS.copy(),
        "positions": {},
        "hedges": [],
        "risk_metrics": {
            "gross_notional": 0.0,
            "net_notional": 0.0,
            "largest_symbol_notional": 0.0,
            "portfolio_leverage_proxy": 0.0,
            "hedge_coverage_ratio": 0.0,
        },
        "market_exposure": {},
        "correlation_exposure": {},
        "alerts": [],
        "telemetry": {
            "snapshots_built": 0,
            "netting_runs": 0,
            "limit_breaches": 0,
            "hedges_recorded": 0,
        },
    }

def portfolio_risk_state_view(state):
    state = state or default_portfolio_risk_state()
    for k, v in default_portfolio_risk_state().items():
        if k not in state:
            state[k] = v
    for k, v in DEFAULT_LIMITS.items():
        state["limits"].setdefault(k, v)
    state["limits"].setdefault("market_limits", DEFAULT_LIMITS["market_limits"].copy())
    state.setdefault("positions", {})
    state.setdefault("hedges", [])
    state.setdefault("alerts", [])
    state.setdefault("market_exposure", {})
    state.setdefault("correlation_exposure", {})
    state.setdefault("risk_metrics", default_portfolio_risk_state()["risk_metrics"].copy())
    state.setdefault("telemetry", default_portfolio_risk_state()["telemetry"].copy())
    return state

def _safe_float(v, d=0.0):
    try:
        return float(v)
    except Exception:
        return d

def _group_for_symbol(symbol):
    return CORRELATION_GROUPS.get((symbol or "").upper(), "uncategorized")

def upsert_exposure(state, *, symbol, market="equities", side="long", qty=0.0, mark_price=0.0, fx_rate=1.0, beta=1.0, strategy_id=None, hedge_tag=None):
    state = portfolio_risk_state_view(state)
    symbol = (symbol or "").upper()
    market = (market or "equities").lower()
    side = (side or "long").lower()
    qty = abs(_safe_float(qty))
    mark_price = max(_safe_float(mark_price, 0.0), 0.0)
    fx_rate = max(_safe_float(fx_rate, 1.0), 0.000001)
    beta = _safe_float(beta, 1.0)
    signed_qty = qty if side in ("long", "buy") else -qty
    notional_usd = round(signed_qty * mark_price * fx_rate, 2)
    gross_notional_usd = round(abs(qty * mark_price * fx_rate), 2)
    state["positions"][symbol] = {
        "symbol": symbol,
        "market": market,
        "side": "long" if signed_qty >= 0 else "short",
        "qty": round(qty, 8),
        "signed_qty": round(signed_qty, 8),
        "mark_price": round(mark_price, 8),
        "fx_rate": round(fx_rate, 8),
        "beta": round(beta, 6),
        "notional_usd": notional_usd,
        "gross_notional_usd": gross_notional_usd,
        "strategy_id": strategy_id,
        "hedge_tag": hedge_tag,
        "correlation_group": _group_for_symbol(symbol),
        "updated_at": now_iso(),
    }
    state["last_updated_at"] = now_iso()
    return {"status": "upserted", "position": state["positions"][symbol]}

def build_risk_snapshot(state):
    state = portfolio_risk_state_view(state)
    positions = list(state["positions"].values())
    gross = round(sum(abs(_safe_float(p.get("notional_usd"))) for p in positions), 2)
    net = round(sum(_safe_float(p.get("notional_usd")) for p in positions), 2)
    largest_symbol = round(max([abs(_safe_float(p.get("notional_usd"))) for p in positions] or [0.0]), 2)
    market_exposure = {}
    corr_exposure = {}
    beta_adjusted_gross = 0.0
    hedge_gross = 0.0
    for p in positions:
        market = p.get("market", "unknown")
        grp = p.get("correlation_group", "uncategorized")
        market_exposure.setdefault(market, {"gross_notional_usd": 0.0, "net_notional_usd": 0.0, "symbols": 0})
        corr_exposure.setdefault(grp, {"gross_notional_usd": 0.0, "net_notional_usd": 0.0, "symbols": 0})
        market_exposure[market]["gross_notional_usd"] += abs(_safe_float(p.get("notional_usd")))
        market_exposure[market]["net_notional_usd"] += _safe_float(p.get("notional_usd"))
        market_exposure[market]["symbols"] += 1
        corr_exposure[grp]["gross_notional_usd"] += abs(_safe_float(p.get("notional_usd")))
        corr_exposure[grp]["net_notional_usd"] += _safe_float(p.get("notional_usd"))
        corr_exposure[grp]["symbols"] += 1
        beta_adjusted_gross += abs(_safe_float(p.get("notional_usd")) * _safe_float(p.get("beta", 1.0)))
        if p.get("hedge_tag"):
            hedge_gross += abs(_safe_float(p.get("notional_usd")))
    for bucket in list(market_exposure.values()) + list(corr_exposure.values()):
        bucket["gross_notional_usd"] = round(bucket["gross_notional_usd"], 2)
        bucket["net_notional_usd"] = round(bucket["net_notional_usd"], 2)
    leverage_proxy = round(beta_adjusted_gross / max(abs(net), 1.0), 4) if positions else 0.0
    hedge_coverage_ratio = round(min(1.0, hedge_gross / max(gross, 1.0)), 4) if gross else 0.0
    state["market_exposure"] = market_exposure
    state["correlation_exposure"] = corr_exposure
    state["risk_metrics"] = {
        "gross_notional": gross,
        "net_notional": net,
        "largest_symbol_notional": largest_symbol,
        "portfolio_leverage_proxy": leverage_proxy,
        "hedge_coverage_ratio": hedge_coverage_ratio,
    }
    state["last_snapshot_at"] = now_iso()
    state["telemetry"]["snapshots_built"] = int(state["telemetry"].get("snapshots_built", 0)) + 1
    return {
        "status": "ok",
        "generated_at": state["last_snapshot_at"],
        "risk_metrics": state["risk_metrics"],
        "market_exposure": market_exposure,
        "correlation_exposure": corr_exposure,
        "positions": positions,
    }

def net_cross_market_exposure(state):
    state = portfolio_risk_state_view(state)
    snap = build_risk_snapshot(state)
    market_exposure = snap["market_exposure"]
    offsets = []
    equities = market_exposure.get("equities", {}).get("net_notional_usd", 0.0)
    futures = market_exposure.get("futures", {}).get("net_notional_usd", 0.0)
    forex = market_exposure.get("forex", {}).get("net_notional_usd", 0.0)
    crypto = market_exposure.get("crypto", {}).get("net_notional_usd", 0.0)

    if equities and futures and (equities * futures) < 0:
        offsets.append({"pair": "equities_vs_futures", "offset_notional_usd": round(min(abs(equities), abs(futures)), 2)})
    if crypto and forex and (crypto * forex) < 0:
        offsets.append({"pair": "crypto_vs_forex", "offset_notional_usd": round(min(abs(crypto), abs(forex)) * 0.25, 2)})

    offset_total = round(sum(item["offset_notional_usd"] for item in offsets), 2)
    residual_net = round(abs(snap["risk_metrics"]["net_notional"]) - offset_total, 2)
    diversification_score = 100.0
    if snap["risk_metrics"]["gross_notional"] > 0:
        residual_ratio = residual_net / max(snap["risk_metrics"]["gross_notional"], 1.0)
        diversification_score = round(max(0.0, 100.0 - residual_ratio * 100.0), 2)

    result = {
        "status": "ok",
        "generated_at": now_iso(),
        "offsets": offsets,
        "offset_total_usd": offset_total,
        "residual_net_usd": residual_net,
        "diversification_score": diversification_score,
    }
    state["last_netting_at"] = result["generated_at"]
    state["telemetry"]["netting_runs"] = int(state["telemetry"].get("netting_runs", 0)) + 1
    return result

def evaluate_limits(state):
    state = portfolio_risk_state_view(state)
    snap = build_risk_snapshot(state)
    netting = net_cross_market_exposure(state)
    limits = state["limits"]
    breaches = []
    alerts = []

    gross = snap["risk_metrics"]["gross_notional"]
    net_abs = abs(snap["risk_metrics"]["net_notional"])
    largest = snap["risk_metrics"]["largest_symbol_notional"]
    leverage = snap["risk_metrics"]["portfolio_leverage_proxy"]

    if gross > limits["gross_notional_limit"]:
        breaches.append({"type": "gross_notional_limit", "actual": gross, "limit": limits["gross_notional_limit"]})
    if net_abs > limits["net_notional_limit"]:
        breaches.append({"type": "net_notional_limit", "actual": net_abs, "limit": limits["net_notional_limit"]})
    if largest > limits["single_symbol_limit"]:
        breaches.append({"type": "single_symbol_limit", "actual": largest, "limit": limits["single_symbol_limit"]})
    if leverage > limits["max_leverage_proxy"]:
        breaches.append({"type": "max_leverage_proxy", "actual": leverage, "limit": limits["max_leverage_proxy"]})

    for market, data in snap["market_exposure"].items():
        market_limit = limits.get("market_limits", {}).get(market)
        if market_limit and abs(data.get("gross_notional_usd", 0.0)) > market_limit:
            breaches.append({"type": f"{market}_market_limit", "actual": data.get("gross_notional_usd", 0.0), "limit": market_limit})

    for group, data in snap["correlation_exposure"].items():
        if data.get("gross_notional_usd", 0.0) > limits["max_correlated_group_exposure"]:
            breaches.append({"type": f"{group}_correlation_limit", "actual": data.get("gross_notional_usd", 0.0), "limit": limits["max_correlated_group_exposure"]})

    if netting["diversification_score"] < 35:
        alerts.append({"type": "low_diversification_score", "score": netting["diversification_score"]})
    if snap["risk_metrics"]["hedge_coverage_ratio"] < 0.1 and gross > 100000:
        alerts.append({"type": "low_hedge_coverage", "hedge_coverage_ratio": snap["risk_metrics"]["hedge_coverage_ratio"]})

    state["alerts"] = alerts + breaches
    if breaches:
        state["telemetry"]["limit_breaches"] = int(state["telemetry"].get("limit_breaches", 0)) + len(breaches)

    return {
        "status": "breach" if breaches else "ok",
        "evaluated_at": now_iso(),
        "breaches": breaches,
        "alerts": alerts,
        "risk_metrics": snap["risk_metrics"],
        "netting": netting,
    }

def portfolio_risk_summary(state):
    state = portfolio_risk_state_view(state)
    return {
        "enabled": state.get("enabled", True),
        "positions": len(state.get("positions", {})),
        "risk_metrics": state.get("risk_metrics", {}),
        "alerts": state.get("alerts", []),
        "last_snapshot_at": state.get("last_snapshot_at"),
        "last_netting_at": state.get("last_netting_at"),
        "telemetry": state.get("telemetry", {}),
    }
