"""
Quantora Real Market Data Service
Fetches live data from Yahoo Finance (yfinance) and CoinGecko (free, no API key).
All functions are synchronous; wrap with asyncio.run_in_executor for async use.
"""
import time
import json
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

# ─── Simple in-memory cache ──────────────────────────────────────────────────
_cache: Dict[str, tuple] = {}  # key → (data, expires_at)
_cache_lock = threading.Lock()

def _cached(key: str, ttl: int, fn):
    """Return cached value or call fn() and cache result for ttl seconds."""
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
                return _cache[key][0]  # return stale on error
        return None


# ─── Yahoo Finance helpers ────────────────────────────────────────────────────
_YF_AVAILABLE = False
try:
    import yfinance as yf
    _YF_AVAILABLE = True
except ImportError:
    logger.warning("yfinance not installed – stock data unavailable")


def _yf_ticker_info(symbol: str) -> dict:
    if not _YF_AVAILABLE:
        return {}
    t = yf.Ticker(symbol)
    info = t.info or {}
    return info


def get_stock_quote(symbol: str) -> dict:
    """Return current quote for a stock/ETF symbol."""
    def fetch():
        if not _YF_AVAILABLE:
            return _fallback_quote(symbol)
        t = yf.Ticker(symbol)
        info = t.info or {}
        price = (
            info.get("currentPrice")
            or info.get("regularMarketPrice")
            or info.get("ask")
            or info.get("bid")
            or 0.0
        )
        prev = info.get("previousClose") or info.get("regularMarketPreviousClose") or price
        chg = price - prev
        pct = (chg / prev * 100) if prev else 0.0
        return {
            "symbol": symbol.upper(),
            "price": round(float(price), 4),
            "change": round(float(chg), 4),
            "change_pct": round(float(pct), 4),
            "volume": info.get("volume") or info.get("regularMarketVolume") or 0,
            "market_cap": info.get("marketCap") or 0,
            "pe_ratio": info.get("trailingPE") or None,
            "52w_high": info.get("fiftyTwoWeekHigh") or None,
            "52w_low": info.get("fiftyTwoWeekLow") or None,
            "sector": info.get("sector") or "N/A",
            "source": "yahoo_finance",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    return _cached(f"stock:{symbol}", ttl=60, fn=fetch) or _fallback_quote(symbol)


def get_multiple_quotes(symbols: List[str]) -> List[dict]:
    """Batch quote fetch for multiple symbols."""
    def fetch():
        if not _YF_AVAILABLE:
            return [_fallback_quote(s) for s in symbols]
        tickers = yf.Tickers(" ".join(symbols))
        results = []
        for sym in symbols:
            try:
                info = tickers.tickers[sym].info or {}
                price = (
                    info.get("currentPrice")
                    or info.get("regularMarketPrice")
                    or info.get("ask")
                    or 0.0
                )
                prev = info.get("previousClose") or info.get("regularMarketPreviousClose") or price
                chg = price - prev
                pct = (chg / prev * 100) if prev else 0.0
                results.append({
                    "symbol": sym.upper(),
                    "price": round(float(price), 4),
                    "change": round(float(chg), 4),
                    "change_pct": round(float(pct), 4),
                    "volume": info.get("volume") or 0,
                    "market_cap": info.get("marketCap") or 0,
                    "source": "yahoo_finance",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            except Exception as e:
                logger.warning(f"Quote fetch error for {sym}: {e}")
                results.append(_fallback_quote(sym))
        return results
    key = "multi:" + ",".join(sorted(symbols))
    return _cached(key, ttl=60, fn=fetch) or [_fallback_quote(s) for s in symbols]


def get_historical(symbol: str, period: str = "1mo", interval: str = "1d") -> List[dict]:
    """Return OHLCV history for a symbol."""
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


# ─── CoinGecko helpers ────────────────────────────────────────────────────────
_COINGECKO_BASE = "https://api.coingecko.com/api/v3"
_COINGECKO_COIN_MAP = {
    "BTC": "bitcoin", "ETH": "ethereum", "BNB": "binancecoin",
    "SOL": "solana", "ADA": "cardano", "XRP": "ripple",
    "DOGE": "dogecoin", "AVAX": "avalanche-2", "MATIC": "matic-network",
    "DOT": "polkadot", "LINK": "chainlink", "UNI": "uniswap",
    "LTC": "litecoin", "BCH": "bitcoin-cash", "ATOM": "cosmos",
}


def get_crypto_prices(symbols: Optional[List[str]] = None) -> List[dict]:
    """Fetch crypto prices from CoinGecko (free, no API key)."""
    if symbols is None:
        symbols = ["BTC", "ETH", "SOL", "BNB", "ADA", "XRP", "DOGE", "AVAX"]

    coin_ids = [_COINGECKO_COIN_MAP.get(s.upper(), s.lower()) for s in symbols]
    ids_str = ",".join(coin_ids)

    def fetch():
        import requests as req
        url = (
            f"{_COINGECKO_BASE}/simple/price"
            f"?ids={ids_str}&vs_currencies=usd"
            f"&include_24hr_change=true&include_market_cap=true&include_24hr_vol=true"
        )
        resp = req.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for sym, coin_id in zip(symbols, coin_ids):
            d = data.get(coin_id, {})
            price = d.get("usd", 0.0)
            chg_pct = d.get("usd_24h_change", 0.0)
            chg = price * chg_pct / 100 if price else 0.0
            results.append({
                "symbol": sym.upper(),
                "price": round(float(price), 6),
                "change": round(float(chg), 6),
                "change_pct": round(float(chg_pct), 4),
                "market_cap": d.get("usd_market_cap", 0),
                "volume_24h": d.get("usd_24h_vol", 0),
                "source": "coingecko",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        return results

    return _cached(f"crypto:{ids_str}", ttl=60, fn=fetch) or [
        {"symbol": s.upper(), "price": 0.0, "change": 0.0, "change_pct": 0.0, "source": "unavailable",
         "timestamp": datetime.now(timezone.utc).isoformat()}
        for s in symbols
    ]


def get_market_overview() -> dict:
    """Return a full market overview: indices + crypto + top movers."""
    index_symbols = ["SPY", "QQQ", "DIA", "IWM", "VIX"]
    tech_symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]
    fin_symbols = ["JPM", "GS", "BAC", "BRK-B"]
    crypto_symbols = ["BTC", "ETH", "SOL", "BNB", "XRP"]

    indices = get_multiple_quotes(index_symbols)
    tech = get_multiple_quotes(tech_symbols)
    financials = get_multiple_quotes(fin_symbols)
    crypto = get_crypto_prices(crypto_symbols)

    all_equities = indices + tech + financials
    gainers = sorted([x for x in all_equities if x.get("change_pct", 0) > 0],
                     key=lambda x: x.get("change_pct", 0), reverse=True)[:5]
    losers = sorted([x for x in all_equities if x.get("change_pct", 0) < 0],
                    key=lambda x: x.get("change_pct", 0))[:5]

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "market_status": _get_market_status(),
        "indices": indices,
        "tech_stocks": tech,
        "financial_stocks": financials,
        "crypto": crypto,
        "top_gainers": gainers,
        "top_losers": losers,
    }


def _get_market_status() -> str:
    """Return US market status based on UTC time."""
    now = datetime.now(timezone.utc)
    # US market: 9:30 AM – 4:00 PM ET = 14:30 – 21:00 UTC
    # Weekdays only
    if now.weekday() >= 5:
        return "CLOSED (Weekend)"
    hour = now.hour * 60 + now.minute
    if 870 <= hour < 1260:  # 14:30 – 21:00 UTC
        return "OPEN"
    elif 840 <= hour < 870:  # 14:00 – 14:30 UTC
        return "PRE-MARKET"
    elif 1260 <= hour < 1440:  # 21:00 – 24:00 UTC
        return "AFTER-HOURS"
    else:
        return "CLOSED"


# ─── Fallback data ────────────────────────────────────────────────────────────
def _fallback_quote(symbol: str) -> dict:
    return {
        "symbol": symbol.upper(),
        "price": 0.0,
        "change": 0.0,
        "change_pct": 0.0,
        "volume": 0,
        "market_cap": 0,
        "source": "unavailable",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "error": "Data temporarily unavailable",
    }
