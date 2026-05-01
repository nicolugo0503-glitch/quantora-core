"""
Quantora Real Dashboard Router
Exposes /api/live/* endpoints backed by real market data (yfinance + CoinGecko).
These are the endpoints that power the production Quantora dashboard.
"""
from __future__ import annotations

import asyncio
from functools import partial
from typing import List, Optional

from fastapi import APIRouter, Query

# Import market data service (path relative to backend/app/)
try:
    from backend.app.services.market_data import (
        get_stock_quote,
        get_multiple_quotes,
        get_historical,
        get_crypto_prices,
        get_market_overview,
        _get_market_status,
    )
except ImportError:
    # Fallback for local dev when running from backend/app/
    from services.market_data import (  # type: ignore
        get_stock_quote,
        get_multiple_quotes,
        get_historical,
        get_crypto_prices,
        get_market_overview,
        _get_market_status,
    )

router = APIRouter(prefix="/api/live", tags=["live-market-data"])


def _run_sync(fn, *args, **kwargs):
    """Run a synchronous function in a thread executor to avoid blocking the event loop."""
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(None, partial(fn, *args, **kwargs))


# ─── Market overview ──────────────────────────────────────────────────────────

@router.get("/overview")
async def live_overview():
    """Full market overview: indices, tech, financials, crypto, top movers."""
    return await _run_sync(get_market_overview)


@router.get("/status")
async def market_status():
    """Return current US market session status."""
    return {"status": _get_market_status()}


# ─── Equities ─────────────────────────────────────────────────────────────────

@router.get("/quote/{symbol}")
async def quote(symbol: str):
    """Real-time quote for a single stock/ETF symbol."""
    return await _run_sync(get_stock_quote, symbol.upper())


@router.get("/quotes")
async def quotes(symbols: str = Query(..., description="Comma-separated symbols, e.g. AAPL,MSFT,GOOGL")):
    """Real-time quotes for multiple symbols (max 20)."""
    sym_list = [s.strip().upper() for s in symbols.split(",") if s.strip()][:20]
    return await _run_sync(get_multiple_quotes, sym_list)


@router.get("/history/{symbol}")
async def history(
    symbol: str,
    period: str = Query("1mo", description="1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max"),
    interval: str = Query("1d", description="1m, 5m, 15m, 30m, 1h, 1d, 1wk, 1mo"),
):
    """OHLCV price history for a symbol."""
    return await _run_sync(get_historical, symbol.upper(), period, interval)


# ─── Crypto ───────────────────────────────────────────────────────────────────

@router.get("/crypto")
async def crypto(
    symbols: str = Query(
        "BTC,ETH,SOL,BNB,ADA,XRP,DOGE,AVAX",
        description="Comma-separated crypto symbols",
    )
):
    """Real-time crypto prices from CoinGecko (free, no API key)."""
    sym_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    return await _run_sync(get_crypto_prices, sym_list)


# ─── Portfolio simulation ─────────────────────────────────────────────────────

@router.get("/portfolio/demo")
async def demo_portfolio():
    """
    Returns a realistic paper-trading portfolio valued with live prices.
    This is a demo portfolio — swap with real broker data when credentials are configured.
    """
    holdings = [
        {"symbol": "AAPL", "shares": 50},
        {"symbol": "MSFT", "shares": 30},
        {"symbol": "NVDA", "shares": 20},
        {"symbol": "GOOGL", "shares": 10},
        {"symbol": "SPY", "shares": 25},
        {"symbol": "QQQ", "shares": 15},
    ]
    symbols = [h["symbol"] for h in holdings]
    quotes_data = await _run_sync(get_multiple_quotes, symbols)
    price_map = {q["symbol"]: q for q in quotes_data}

    total_value = 0.0
    total_cost = 100_000.0  # demo cost basis
    positions = []
    for h in holdings:
        q = price_map.get(h["symbol"], {})
        price = q.get("price", 0.0)
        value = price * h["shares"]
        total_value += value
        positions.append({
            "symbol": h["symbol"],
            "shares": h["shares"],
            "price": price,
            "value": round(value, 2),
            "change_pct": q.get("change_pct", 0.0),
            "change_today": round(price * h["shares"] * q.get("change_pct", 0.0) / 100, 2),
        })

    total_pnl = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost else 0.0
    return {
        "portfolio_value": round(total_value, 2),
        "total_cost": total_cost,
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round(total_pnl_pct, 4),
        "cash": 10_000.0,
        "positions": positions,
        "mode": "PAPER_TRADING",
    }


# ─── Sector / index snapshot ──────────────────────────────────────────────────

@router.get("/sectors")
async def sectors():
    """Sector ETF snapshot (XLK, XLF, XLE, XLV, XLY, XLP, XLI, XLB, XLU, XLRE)."""
    sector_etfs = ["XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLI", "XLB", "XLU", "XLRE"]
    sector_names = {
        "XLK": "Technology", "XLF": "Financials", "XLE": "Energy",
        "XLV": "Healthcare", "XLY": "Consumer Disc.", "XLP": "Consumer Staples",
        "XLI": "Industrials", "XLB": "Materials", "XLU": "Utilities", "XLRE": "Real Estate",
    }
    quotes_data = await _run_sync(get_multiple_quotes, sector_etfs)
    for q in quotes_data:
        q["sector_name"] = sector_names.get(q["symbol"], q["symbol"])
    return quotes_data


@router.get("/indices")
async def indices():
    """Major US market indices via ETF proxies."""
    return await _run_sync(get_multiple_quotes, ["SPY", "QQQ", "DIA", "IWM", "^VIX"])
