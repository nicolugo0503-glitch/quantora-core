"""
Quantora Real Market Data Service
Stock data: Yahoo Finance chart API v8 (direct, browser headers) + Stooq fallback
Crypto data: CoinGecko free API (no key required)
"""
import io
import csv
import time
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import logging
import requests

logger = logging.getLogger(__name__)

# ─── HTTP session with browser headers ────────────────────────────────────────
_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
})

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
        if result is not None:
            with _cache_lock:
                _cache[key] = (result, now + ttl)
        return result
    except Exception as e:
        logger.warning(f"Market data fetch failed [{key}]: {e}")
        with _cache_lock:
            if key in _cache:
                return _cache[key][0]
        return None

# ─── Yahoo Finance chart API ───────────────────────────────────────────────────
def _yf_chart(symbol: str) -> Optional[dict]:
    """
    Fetch price via Yahoo Finance v8 chart API with browser headers.
    Returns {"price": float, "prev": float} or None on failure.
    """
    for base in ["https://query1.finance.yahoo.com", "https://query2.finance.yahoo.com"]:
        try:
            url = f"{base}/v8/finance/chart/{symbol}"
            params = {"interval": "1d", "range": "5d", "includePrePost": "false"}
            r = _SESSION.get(url, params=params, timeout=12)
            if r.status_code == 429:
                logger.debug(f"Yahoo rate-limited for {symbol}")
                continue
            r.raise_for_status()
            data = r.json()
            result = data.get("chart", {}).get("result")
            if not result:
                continue
            meta = result[0].get("meta", {})
            price = (meta.get("regularMarketPrice") or
                     meta.get("previousClose") or 0.0)
            prev  = (meta.get("previousClose") or
                     meta.get("chartPreviousClose") or
                     meta.get("regularMarketPreviousClose") or price)
            if price > 0:
                return {"price": float(price), "prev": float(prev)}
        except Exception as e:
            logger.debug(f"yf_chart {base} {symbol}: {e}")
    return None

def _stooq_price(symbol: str) -> Optional[dict]:
    """Fallback: fetch last 2 closing prices from Stooq (free, no auth)."""
    try:
        to_d   = datetime.now(timezone.utc)
        from_d = to_d - timedelta(days=10)
        sym_s  = symbol.replace("-", ".").lower()
        url = (
            f"https://stooq.com/q/d/l/?s={sym_s}.us"
            f"&d1={from_d.strftime('%Y%m%d')}&d2={to_d.strftime('%Y%m%d')}&i=d"
        )
        r = _SESSION.get(url, timeout=12)
        r.raise_for_status()
        text = r.text.strip()
        if not text or "No data" in text:
            return None
        rows = list(csv.DictReader(io.StringIO(text)))
        if len(rows) < 1:
            return None
        price = float(rows[-1]["Close"])
        prev  = float(rows[-2]["Close"]) if len(rows) >= 2 else price
        return {"price": price, "prev": prev}
    except Exception as e:
        logger.debug(f"stooq {symbol}: {e}")
    return None

def _get_quote_data(symbol: str) -> Optional[dict]:
    """Try Yahoo chart API, then Stooq."""
    d = _yf_chart(symbol)
    if d:
        return d
    return _stooq_price(symbol)

# ─── Public API ────────────────────────────────────────────────────────────────
def get_stock_quote(symbol: str) -> dict:
    def fetch():
        d = _get_quote_data(symbol)
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
        results = []
        for sym in symbols:
            d = _get_quote_data(sym)
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
        try:
            import yfinance as yf
            t = yf.Ticker(symbol)
            hist = t.history(period=period, interval=interval)
            if hist.empty:
                return []
            rows = []
            for ts, row in hist.iterrows():
                rows.append({
                    "date": ts.strftime("%Y-%m-%d") if interval == "1d" else ts.isoformat(),
                    "open":   round(float(row["Open"]),   4),
                    "high":   round(float(row["High"]),   4),
                    "low":    round(float(row["Low"]),    4),
                    "close":  round(float(row["Close"]),  4),
                    "volume": int(row["Volume"]),
                })
            return rows
        except Exception as e:
            logger.warning(f"Historical data failed for {symbol}: {e}")
            return []
    return _cached(f"hist:{symbol}:{period}:{interval}", ttl=300, fn=fetch) or []

# ─── CoinGecko ─────────────────────────────────────────────────────────────────
_COINGECKO_BASE = "https://api.coingecko.com/api/v3"
_COIN_MAP = {
    "BTC": "bitcoin",     "ETH": "ethereum",   "BNB": "binancecoin",
    "SOL": "solana",      "ADA": "cardano",    "XRP": "ripple",
    "DOGE": "dogecoin",   "AVAX": "avalanche-2","MATIC": "matic-network",
    "DOT": "polkadot",    "LINK": "chainlink",  "UNI": "uniswap",
    "LTC": "litecoin",    "BCH": "bitcoin-cash","ATOM": "cosmos",
}

def get_crypto_prices(symbols: Optional[List[str]] = None) -> List[dict]:
    if symbols is None:
        symbols = ["BTC", "ETH", "SOL", "BNB", "ADA", "XRP", "DOGE", "AVAX"]
    coin_ids = [_COIN_MAP.get(s.upper(), s.lower()) for s in symbols]
    ids_str  = ",".join(coin_ids)

    def fetch():
        url = (
            f"{_COINGECKO_BASE}/simple/price?ids={ids_str}&vs_currencies=usd"
            "&include_24hr_change=true&include_market_cap=true&include_24hr_vol=true"
        )
        resp = _SESSION.get(url, timeout=15)
        if resp.status_code == 429:
            raise Exception("CoinGecko rate limited")
        resp.raise_for_status()
        data = resp.json()
        results = []
        for sym, coin_id in zip(symbols, coin_ids):
            d = data.get(coin_id, {})
            price    = d.get("usd", 0.0)
            chg_pct  = d.get("usd_24h_change", 0.0)
            chg      = price * chg_pct / 100 if price else 0.0
            results.append({
                "symbol":     sym.upper(),
                "price":      round(float(price),   6),
                "change":     round(float(chg),     6),
                "change_pct": round(float(chg_pct), 4),
                "market_cap": d.get("usd_market_cap", 0),
                "volume_24h": d.get("usd_24h_vol", 0),
                "source":     "coingecko",
                "timestamp":  datetime.now(timezone.utc).isoformat(),
            })
        return results

    return _cached(f"crypto:{ids_str}", ttl=120, fn=fetch) or [
        {"symbol": s.upper(), "price": 0.0, "change": 0.0, "change_pct": 0.0,
         "source": "unavailable", "timestamp": datetime.now(timezone.utc).isoformat()}
        for s in symbols
    ]

def get_market_overview() -> dict:
    index_syms  = ["SPY", "QQQ", "DIA", "IWM"]
    tech_syms   = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]
    fin_syms    = ["JPM", "GS", "BAC"]
    crypto_syms = ["BTC", "ETH", "SOL", "BNB", "XRP"]

    indices    = get_multiple_quotes(index_syms)
    tech       = get_multiple_quotes(tech_syms)
    financials = get_multiple_quotes(fin_syms)
    crypto     = get_crypto_prices(crypto_syms)

    all_eq  = indices + tech + financials
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
    if 870 <= m < 1260:   return "OPEN"
    if 840 <= m < 870:    return "PRE-MARKET"
    if 1260 <= m < 1440:  return "AFTER-HOURS"
    return "CLOSED"

def _fallback_quote(symbol: str) -> dict:
    return {
        "symbol": symbol.upper(), "price": 0.0, "change": 0.0,
        "change_pct": 0.0, "volume": 0, "market_cap": 0,
        "source": "unavailable",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "error": "Data temporarily unavailable",
    }
