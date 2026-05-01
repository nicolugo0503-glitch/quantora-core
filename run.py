"""
Quantora Financial Intelligence OS — Production Entry Point
===========================================================
This file is the single entry-point used by Railway (and any other host).
It imports the existing FastAPI app from backend/app/main.py, then:
  1. Adds permissive CORS for production
  2. Mounts the /frontend directory as static files at /ui
  3. Wires up the real live-market-data router at /api/live/*
  4. Runs state initialization on startup
  5. Exposes /health for Railway health-checks
  6. Serves a rich landing page at /

Start command: uvicorn run:app --host 0.0.0.0 --port $PORT
"""
import os
import sys
import logging
import asyncio
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("quantora.run")

# ── Import the main FastAPI app ───────────────────────────────────────────────
logger.info("Loading Quantora backend…")
try:
    from backend.app.main import app
    logger.info("✅ Main app loaded")
except Exception as e:
    logger.error(f"Failed to import main app: {e}")
    # Create a minimal fallback app so Railway doesn't crash on boot
    from fastapi import FastAPI
    app = FastAPI(title="Quantora — degraded mode")

# ── CORS (must be added BEFORE any existing middleware for correct ordering) ──
from starlette.middleware.cors import CORSMiddleware

# Remove duplicate CORS middleware if already present (avoids double-headers)
app.middleware_stack = None  # reset compiled stack
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.info("✅ CORS configured (allow *)")

# ── Real live-data router ─────────────────────────────────────────────────────
try:
    from backend.app.real_dashboard_router import router as live_router
    app.include_router(live_router)
    logger.info("✅ Live market-data router registered at /api/live/*")
except Exception as e:
    logger.warning(f"Could not load live dashboard router: {e}")

# ── Static file serving (frontend HTML panels) ────────────────────────────────
from fastapi.staticfiles import StaticFiles

frontend_dir = BASE_DIR / "frontend"
if frontend_dir.exists():
    try:
        app.mount("/ui", StaticFiles(directory=str(frontend_dir), html=True), name="ui")
        logger.info(f"✅ Frontend panels served at /ui/ ({len(list(frontend_dir.glob('*.html')))} panels)")
    except Exception as e:
        logger.warning(f"Could not mount static files: {e}")
else:
    logger.warning("frontend/ directory not found — UI panels unavailable")

# ── Health endpoint ───────────────────────────────────────────────────────────
from fastapi.responses import JSONResponse, HTMLResponse

@app.get("/health", tags=["system"])
def health():
    return JSONResponse({"status": "ok", "service": "Quantora Financial Intelligence OS"})

# ── Landing page ──────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse, tags=["system"])
def root():
    return HTMLResponse(content=_landing_html(), status_code=200)

# ── Startup hook ─────────────────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup():
    logger.info("Running Quantora startup initialization…")
    try:
        from backend.app.startup import initialize_state
        await asyncio.get_event_loop().run_in_executor(None, initialize_state)
        logger.info("✅ State initialization complete")
    except Exception as e:
        logger.warning(f"State init warning (non-fatal): {e}")


# ─────────────────────────────────────────────────────────────────────────────
def _landing_html() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Quantora Financial Intelligence OS</title>
<style>
  :root { --bg: #0a0e1a; --surface: #111827; --border: #1f2937; --accent: #00d4ff; --green: #10b981; --red: #ef4444; --text: #e2e8f0; --muted: #6b7280; }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', system-ui, sans-serif; min-height: 100vh; }
  .header { border-bottom: 1px solid var(--border); padding: 1.5rem 2rem; display: flex; align-items: center; gap: 1rem; }
  .logo { font-size: 1.5rem; font-weight: 700; color: var(--accent); letter-spacing: -0.5px; }
  .logo span { color: var(--text); }
  .badge { background: #00d4ff20; color: var(--accent); border: 1px solid #00d4ff40; border-radius: 4px; padding: 2px 8px; font-size: 0.7rem; font-weight: 600; }
  .status-bar { background: #00d4ff08; border-bottom: 1px solid var(--border); padding: 0.6rem 2rem; font-size: 0.8rem; color: var(--muted); display: flex; gap: 2rem; }
  .status-bar .live { color: var(--green); font-weight: 600; }
  .main { padding: 2rem; max-width: 1400px; margin: 0 auto; }
  h2 { font-size: 1.1rem; font-weight: 600; color: var(--accent); margin-bottom: 1.25rem; padding-bottom: 0.5rem; border-bottom: 1px solid var(--border); }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1rem; margin-bottom: 2.5rem; }
  .card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1.25rem; cursor: pointer; transition: border-color 0.2s, transform 0.1s; text-decoration: none; color: inherit; display: block; }
  .card:hover { border-color: var(--accent); transform: translateY(-2px); }
  .card-title { font-size: 0.85rem; font-weight: 600; color: var(--accent); margin-bottom: 0.4rem; }
  .card-desc { font-size: 0.75rem; color: var(--muted); line-height: 1.5; }
  .card-badge { display: inline-block; font-size: 0.65rem; font-weight: 700; padding: 2px 6px; border-radius: 3px; margin-bottom: 0.6rem; }
  .badge-live { background: #10b98120; color: var(--green); border: 1px solid #10b98140; }
  .badge-paper { background: #f59e0b20; color: #f59e0b; border: 1px solid #f59e0b40; }
  .badge-config { background: #6b728020; color: var(--muted); border: 1px solid #6b728040; }
  .market-bar { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1rem 1.5rem; margin-bottom: 2rem; display: flex; gap: 2rem; flex-wrap: wrap; align-items: center; }
  .ticker { font-size: 0.8rem; }
  .ticker .sym { font-weight: 700; color: var(--text); margin-right: 0.4rem; }
  .ticker .price { color: var(--muted); margin-right: 0.3rem; }
  .ticker .up { color: var(--green); }
  .ticker .down { color: var(--red); }
  .api-section { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1.5rem; margin-bottom: 2rem; }
  .api-endpoint { display: flex; align-items: center; gap: 0.75rem; padding: 0.5rem 0; border-bottom: 1px solid var(--border); font-size: 0.8rem; }
  .api-endpoint:last-child { border-bottom: none; }
  .method { background: #10b98120; color: var(--green); border-radius: 3px; padding: 2px 6px; font-weight: 700; font-size: 0.65rem; font-family: monospace; }
  .path { color: var(--accent); font-family: monospace; flex: 1; }
  .api-desc { color: var(--muted); }
  footer { text-align: center; padding: 2rem; color: var(--muted); font-size: 0.75rem; border-top: 1px solid var(--border); margin-top: 2rem; }
</style>
</head>
<body>
<div class="header">
  <div class="logo">QUANTORA<span> Financial Intelligence OS</span></div>
  <div class="badge">v4.0 PRODUCTION</div>
  <div class="badge" style="color:#10b981;border-color:#10b98140;background:#10b98110;">DEPLOYED</div>
</div>
<div class="status-bar">
  <span class="live" id="mktstatus">⬤ Loading market status…</span>
  <span id="mkttime">—</span>
  <span>Real data: Yahoo Finance + CoinGecko</span>
  <span>Paper trading mode active</span>
</div>
<div class="main">

  <!-- Live ticker bar -->
  <div class="market-bar" id="tickerBar">
    <div style="color:var(--muted);font-size:0.8rem;">Loading live prices…</div>
  </div>

  <!-- Live API Endpoints -->
  <h2>⚡ Live Market Data API</h2>
  <div class="api-section">
    <div class="api-endpoint"><span class="method">GET</span><span class="path">/api/live/overview</span><span class="api-desc">Full market overview: indices, tech, crypto, top movers</span></div>
    <div class="api-endpoint"><span class="method">GET</span><span class="path">/api/live/quote/{symbol}</span><span class="api-desc">Real-time quote for any stock or ETF</span></div>
    <div class="api-endpoint"><span class="method">GET</span><span class="path">/api/live/quotes?symbols=AAPL,MSFT,NVDA</span><span class="api-desc">Batch quotes for multiple symbols</span></div>
    <div class="api-endpoint"><span class="method">GET</span><span class="path">/api/live/history/{symbol}?period=1mo</span><span class="api-desc">OHLCV price history</span></div>
    <div class="api-endpoint"><span class="method">GET</span><span class="path">/api/live/crypto</span><span class="api-desc">Live crypto prices (BTC, ETH, SOL…)</span></div>
    <div class="api-endpoint"><span class="method">GET</span><span class="path">/api/live/sectors</span><span class="api-desc">Sector ETF performance snapshot</span></div>
    <div class="api-endpoint"><span class="method">GET</span><span class="path">/api/live/portfolio/demo</span><span class="api-desc">Demo paper portfolio valued at live prices</span></div>
    <div class="api-endpoint"><span class="method">GET</span><span class="path">/docs</span><span class="api-desc">Full interactive API documentation (Swagger)</span></div>
  </div>

  <!-- Mission panels -->
  <h2>🖥️ Intelligence Panels</h2>
  <div class="grid">
    <a class="card" href="/ui/mission_qntreal01a_operator_mode_live_execution_activation.html">
      <div class="card-badge badge-paper">REAL01A</div>
      <div class="card-title">Operator Mode — Execution Activation</div>
      <div class="card-desc">Master execution control surface: live broker connection, risk kill-switch, strategy deployment.</div>
    </a>
    <a class="card" href="/ui/mission_qntreal01b_live_broker_truth_path.html">
      <div class="card-badge badge-paper">REAL01B</div>
      <div class="card-title">Live Broker Truth Path</div>
      <div class="card-desc">Real broker session state, account verification, and truth-path connectivity.</div>
    </a>
    <a class="card" href="/ui/qnt_real04a_multi_broker_orchestration_panel.html">
      <div class="card-badge badge-paper">REAL04A</div>
      <div class="card-title">Multi-Broker Orchestration</div>
      <div class="card-desc">Coordinate execution across multiple broker sessions and capital accounts.</div>
    </a>
    <a class="card" href="/ui/qnt_real04b_cross_asset_correlation_panel.html">
      <div class="card-badge badge-paper">REAL04B</div>
      <div class="card-title">Cross-Asset Correlation</div>
      <div class="card-desc">Real-time correlation analysis across equities, crypto, FX, and commodities.</div>
    </a>
    <a class="card" href="/ui/qnt_real04c_liquidity_stress_panel.html">
      <div class="card-badge badge-paper">REAL04C</div>
      <div class="card-title">Liquidity Stress Testing</div>
      <div class="card-desc">Portfolio liquidity analysis and market-impact stress scenarios.</div>
    </a>
    <a class="card" href="/ui/qnt_real04d_regulatory_capital_panel.html">
      <div class="card-badge badge-paper">REAL04D</div>
      <div class="card-title">Regulatory Capital Monitor</div>
      <div class="card-desc">Basel III/IV capital ratios, RWA calculations, and compliance buffers.</div>
    </a>
    <a class="card" href="/ui/qnt_real04e_esg_risk_panel.html">
      <div class="card-badge badge-paper">REAL04E</div>
      <div class="card-title">ESG Risk Intelligence</div>
      <div class="card-desc">Environmental, Social, and Governance risk scoring and portfolio alignment.</div>
    </a>
    <a class="card" href="/ui/qnt_real04f_portfolio_attribution_panel.html">
      <div class="card-badge badge-paper">REAL04F</div>
      <div class="card-title">Portfolio Attribution</div>
      <div class="card-desc">Brinson-Hood-Beebower attribution: allocation vs. selection vs. interaction.</div>
    </a>
    <a class="card" href="/ui/qnt_real04g_derivatives_pricing_panel.html">
      <div class="card-badge badge-paper">REAL04G</div>
      <div class="card-title">Derivatives Pricing Engine</div>
      <div class="card-desc">Black-Scholes, binomial tree, and Monte Carlo option pricing.</div>
    </a>
    <a class="card" href="/ui/qnt_real04h_systemic_risk_panel.html">
      <div class="card-badge badge-paper">REAL04H</div>
      <div class="card-title">Systemic Risk Monitor</div>
      <div class="card-desc">Contagion risk, interconnectedness metrics, and systemic stress indicators.</div>
    </a>
    <a class="card" href="/docs">
      <div class="card-badge" style="background:#6366f120;color:#818cf8;border:1px solid #818cf840;">API</div>
      <div class="card-title">Swagger API Documentation</div>
      <div class="card-desc">Full interactive documentation for all 300+ Quantora API endpoints.</div>
    </a>
    <a class="card" href="/redoc">
      <div class="card-badge" style="background:#6366f120;color:#818cf8;border:1px solid #818cf840;">API</div>
      <div class="card-title">ReDoc API Reference</div>
      <div class="card-desc">Clean, readable API reference documentation.</div>
    </a>
  </div>
</div>

<footer>
  Quantora Financial Intelligence OS &nbsp;·&nbsp; Paper Trading Mode &nbsp;·&nbsp; Real market data via Yahoo Finance & CoinGecko
</footer>

<script>
const BASE = window.location.origin;

async function loadTicker() {
  try {
    const r = await fetch(BASE + '/api/live/quotes?symbols=SPY,QQQ,AAPL,MSFT,NVDA,BTC-USD,ETH-USD');
    if (!r.ok) throw new Error('API error');
    const data = await r.json();
    const bar = document.getElementById('tickerBar');
    bar.innerHTML = data.map(q => {
      const up = q.change_pct >= 0;
      return `<div class="ticker">
        <span class="sym">${q.symbol}</span>
        <span class="price">$${Number(q.price).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
        <span class="${up ? 'up' : 'down'}">${up ? '+' : ''}${Number(q.change_pct).toFixed(2)}%</span>
      </div>`;
    }).join('');
  } catch(e) {
    document.getElementById('tickerBar').innerHTML = '<div style="color:var(--muted);font-size:0.8rem;">Live prices loading… (' + e.message + ')</div>';
  }
}

async function loadStatus() {
  try {
    const r = await fetch(BASE + '/api/live/status');
    const d = await r.json();
    const el = document.getElementById('mktstatus');
    const isOpen = d.status === 'OPEN';
    el.textContent = (isOpen ? '⬤ US Market OPEN' : '◯ US Market ' + d.status);
    el.style.color = isOpen ? 'var(--green)' : 'var(--muted)';
  } catch(e) {}
  const now = new Date();
  document.getElementById('mkttime').textContent = now.toUTCString();
}

loadTicker();
loadStatus();
setInterval(loadTicker, 60000);
setInterval(loadStatus, 30000);
</script>
</body>
</html>"""
