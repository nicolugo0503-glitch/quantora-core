"""
Quantora Real Market Data Service
Fetches live data from Yahoo Finance (yfinance) and CoinGecko (free, no API key).
Uses yf.download() for stock quotes — much more reliable than Ticker.info on hosted envs.
"""
import time
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

# ─── Simple in-memory cache ────────────────────────────────────────────────────
_cache: Dict[str, tuple] = {}
_cache_lock = threading.Lock()

def _cached(key: str, ttl: int, fn):
    now = time.time()
    with _cache_lock:
        if key in _cache:
            data, exp = _cache[key]
            if now < exp:
                return data
    try:
        result = fn()
        with _cache_lock:
            _cache[key] = (result, now + ttl)
        return result
    except Exception as e:
        logger.warning(f"Market data fetch failed [{key}]: {e}")
        with _cache_lock:
            if key in _cache:
                return _cache[key][0]
        return None

# ─── yfinance setup ────────────────────────────────────────────────────────────
_YF_AVAILABLE = False
try:
    import yfinance as yf
    _YF_AVAILABLE = True
    logger.info("yfinance loaded OK")
except ImportError:
    logger.warning("yfinance not installed — stock data unavailable")

def _download_quotes(symbols: List[str]) -> dict:
    """Use yf.download() (more stable than .info) to get close prices."""
    sym_str = " ".join(symbols)
    df = yf.download(sym_str, period="5d", interval="1d",
                     progress=False, auto_adjust=True)
    if df.empty:
        return {}
    close = df["Close"]
    result = {}
    for sym in symbols:
        try:
            if len(symbols) == 1:
                series = close.dropna()
            else:
                series = close[sym].dropna()
            if len(series) >= 2:
                result[sym] = {"price": float(series.iloc[-1]), "prev": float(series.iloc[-2])}
            elif len(series) == 1:
                p = float(series.iloc[-1])
                result[sym] = {"price": p, "prev": p}
        except Exception as e:
            logger.debug(f"_download_quotes skip {sym}: {e}")
    return result

def get_stock_quote(symbol: str) -> dict:
    def fetch():
        if not _YF_AVAILABLE:
            return _fallback_quote(symbol)
        data = _download_quotes([symbol])
        d = data.get(symbol)
        if not d:
            return _fallback_quote(symbol)
        price, prev = d["price"], d["prev"]
        chg = price - prev
        pct = (chg / prev * 100) if prev else 0.0
        return {
            "symbol": symbol.upper(), "price": round(price, 4),
            "change": round(chg, 4), "change_pct": round(pct, 4),
            "volume": 0, "market_cap": 0,
            "source": "yahoo_finance",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    return _cached(f"stock:{symbol}", ttl=120, fn=fetch) or _fallback_quote(symbol)

def get_multiple_quotes(symbols: List[str]) -> List[dict]:
    def fetch():
        if not _YF_AVAILABLE:
            return [_fallback_quote(s) for s in symbols]
        data = _download_quotes(symbols)
        results = []
        for sym in symbols:
            d = data.get(sym)
            if d:
                price, prev = d["price"], d["prev"]
                chg = price - prev
                pct = (chg / prev * 100) if prev else 0.0
                results.append({
                    "symbol": sym.upper(), "price": round(price, 4),
                    "change": round(chg, 4), "change_pct": round(pct, 4),
                    "volume": 0, "market_cap": 0,
                    "source": "yahoo_finance",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            else:
                results.append(_fallback_quote(sym))
        return results
    key = "multi:" + ",".join(sorted(symbols))
    return _cached(key, ttl=120, fn=fetch) or [_fallback_quote(s) for s in symbols]

def get_historical(symbol: str, period: str = "1mo", interval: str = "1d") -> List[dict]:
    def fetch():
        if not _YF_AVAILABLE:
            return []
        t = yf.Ticker(symbol)
        hist = t.history(period=period, interval=interval)
        if hist.empty:
            return []
        rows = []
        for ts, row in hist.iterrows():
            rows.append({
                "date": ts.strftime("%Y-%m-%d") if interval == "1d" else ts.isoformat(),
                "open": round(float(row["Open"]), 4),
                "high": round(float(row["High"]), 4),
                "low": round(float(row["Low"]), 4),
                "close": round(float(row["Close"]), 4),
                "volume": int(row["Volume"]),
            })
        return rows
    return _cached(f"hist:{symbol}:{period}:{interval}", ttl=300, fn=fetch) or []

# ─── CoinGecko ─────────────────────────────────────────────────────────────────
_COINGECKO_BASE = "https://api.coingecko.com/api/v3"
_COINGECKO_COIN_MAP = {
    "BTC": "bitcoin", "ETH": "ethereum", "BNB": "binancecoin",
    "SOL": "solana", "ADA": "cardano", "XRP": "ripple",
    "DOGE": "dogecoin", "AVAX": "avalanche-2", "MATIC": "matic-network",
    "DOT": "polkadot", "LINK": "chainlink", "UNI": "uniswap",
    "LTC": "litecoin", "BCH": "bitcoin-cash", "ATOM": "cosmos",
}

def get_crypto_prices(symbols: Optional[List[str]] = None) -> List[dict]:
    if symbols is None:
        symbols = ["BTC", "ETH", "SOL", "BNB", "ADA", "XRP", "DOGE", "AVAX"]
    coin_ids = [_COINGECKO_COIN_MAP.get(s.upper(), s.lower()) for s in symbols]
    ids_str = ",".join(coin_ids)

    def fetch():
        import requests as req
        headers = {"Accept": "application/json", "User-Agent": "Quantora/1.0"}
        url = (f"{_COINGECKO_BASE}/simple/price?ids={ids_str}&vs_currencies=usd"
               "&include_24hr_change=true&include_market_cap=true&include_24hr_vol=true")
        resp = req.get(url, timeout=15, headers=headers)
        if resp.status_code == 429:
            raise Exception("CoinGecko rate limited")
        resp.raise_for_status()
        data = resp.json()
        results = []
        for sym, coin_id in zip(symbols, coin_ids):
            d = data.get(coin_id, {})
            price = d.get("usd", 0.0)
            chg_pct = d.get("usd_24h_change", 0.0)
            chg = price * chg_pct / 100 if price else 0.0
            results.append({
                "symbol": sym.upper(), "price": round(float(price), 6),
                "change": round(float(chg), 6), "change_pct": round(float(chg_pct), 4),
                "market_cap": d.get("usd_market_cap", 0),
                "volume_24h": d.get("usd_24h_vol", 0),
                "source": "coingecko",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        return results

    return _cached(f"crypto:{ids_str}", ttl=120, fn=fetch) or [
        {"symbol": s.upper(), "price": 0.0, "change": 0.0, "change_pct": 0.0,
         "source": "unavailable", "timestamp": datetime.now(timezone.utc).isoformat()}
        for s in symbols
    ]

def get_market_overview() -> dict:
    index_symbols  = ["SPY", "QQQ", "DIA", "IWM", "VIX"]
    tech_symbols   = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]
    fin_symbols    = ["JPM", "GS", "BAC", "BRK-B"]
    crypto_symbols = ["BTC", "ETH", "SOL", "BNB", "XRP"]

    indices    = get_multiple_quotes(index_symbols)
    tech       = get_multiple_quotes(tech_symbols)
    financials = get_multiple_quotes(fin_symbols)
    crypto     = get_crypto_prices(crypto_symbols)

    all_eq = indices + tech + financials
    gainers = sorted([x for x in all_eq if x.get("change_pct", 0) > 0],
                     key=lambda x: x["change_pct"], reverse=True)[:5]
    losers  = sorted([x for x in all_eq if x.get("change_pct", 0) < 0],
                     key=lambda x: x["change_pct"])[:5]
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "market_status": _get_market_status(),
        "indices": indices, "tech_stocks": tech,
        "financial_stocks": financials, "crypto": crypto,
        "top_gainers": gainers, "top_losers": losers,
    }

def _get_market_status() -> str:
    now = datetime.now(timezone.utc)
    if now.weekday() >= 5:
        return "CLOSED (Weekend)"
    m = now.hour * 60 + now.minute
    if 870 <= m < 1260:
        return "OPEN"
    elif 840 <= m < 870:
        return "PRE-MARKET"
    elif 1260 <= m < 1440:
        return "AFTER-HOURS"
    return "CLOSED"

def _fallback_quote(symbol: str) -> dict:
    return {
        "symbol": symbol.upper(), "price": 0.0, "change": 0.0, "change_pct": 0.0,
        "volume": 0, "market_cap": 0, "source": "unavailable",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "error": "Data temporarily unavailable",
    }
