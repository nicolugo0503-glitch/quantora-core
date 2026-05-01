"""
Quantora Production Entry Point — run.py
Wraps the existing app with CORS, live data routes, static files, and startup.
Railway start command: uvicorn run:app --host 0.0.0.0 --port $PORT --workers 1
"""
from __future__ import annotations
import asyncio
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Import main app (with safe fallback) ──────────────────────────────────────
try:
    from backend.app.main import app
    logger.info("Main app imported successfully")
    _main_imported = True
except Exception as e:
    logger.warning(f"Main app import failed ({e}) — using minimal fallback app")
    from fastapi import FastAPI
    app = FastAPI(title="Quantora Financial Intelligence OS", version="1.0.0")
    _main_imported = False

# ── CORS ──────────────────────────────────────────────────────────────────────
try:
    from starlette.middleware.cors import CORSMiddleware
    app.middleware_stack = None
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info("CORS middleware added")
except Exception as e:
    logger.warning(f"CORS middleware warning: {e}")

# ── Live market data router ───────────────────────────────────────────────────
try:
    from backend.app.real_dashboard_router import router as live_router
    app.include_router(live_router)
    logger.info("Live market data router mounted at /api/live/*")
except Exception as e:
    logger.warning(f"Live router not loaded: {e}")

# ── Static files ──────────────────────────────────────────────────────────────
try:
    from fastapi.staticfiles import StaticFiles
    if os.path.isdir("frontend"):
        app.mount("/ui", StaticFiles(directory="frontend", html=True), name="ui")
        logger.info("Frontend mounted at /ui/")
except Exception as e:
    logger.warning(f"Static files not mounted: {e}")

# ── Health check ──────────────────────────────────────────────────────────────
from fastapi.responses import JSONResponse, HTMLResponse

@app.get("/health")
def health():
    return JSONResponse({"status": "ok", "main_app": _main_imported})

# ── Landing page ──────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return HTMLResponse(content=_landing_html())

def _landing_html() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Quantora Financial Intelligence OS</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0e1a;color:#e2e8f0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;min-height:100vh}
.hdr{background:linear-gradient(135deg,#1a1f35 0%,#0d1117 100%);padding:40px;border-bottom:1px solid #1e3a5f}
h1{font-size:2.5rem;background:linear-gradient(90deg,#00d4ff,#7b2fff);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.sub{color:#64748b;margin-top:8px;font-size:1.1rem}
.ticker{background:#0d1117;padding:12px 40px;border-bottom:1px solid #1e2d3d;font-family:monospace;font-size:.85rem;overflow:hidden;white-space:nowrap}
.up{color:#10b981}.dn{color:#ef4444}
.main{padding:40px;max-width:1200px;margin:0 auto}
.badge{display:inline-block;padding:4px 12px;border-radius:20px;font-size:.75rem;font-weight:700;margin-bottom:20px}
.open{background:#052e16;color:#10b981;border:1px solid #10b981}
.closed{background:#1a0000;color:#ef4444;border:1px solid #ef4444}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px;margin-top:30px}
.card{background:#111827;border:1px solid #1e2d3d;border-radius:12px;padding:24px;transition:border-color .2s}
.card:hover{border-color:#00d4ff}
.card h3{color:#00d4ff;margin-bottom:8px}
.card p{color:#94a3b8;font-size:.9rem}
.card a{display:inline-block;margin-top:12px;color:#7b2fff;text-decoration:none;font-weight:600}
</style>
</head>
<body>
<div class="hdr">
  <h1>&#9889; Quantora Financial Intelligence OS</h1>
  <div class="sub">Real-time market intelligence &middot; Paper trading &middot; AI-powered analysis</div>
</div>
<div class="ticker" id="ticker">Loading market data&hellip;</div>
<div class="main">
  <div id="st"></div>
  <div class="grid">
    <div class="card"><h3>&#128202; Live Market Data</h3><p>Real-time quotes via Yahoo Finance &amp; CoinGecko &mdash; no API key required.</p><a href="/api/live/overview">View Overview &rarr;</a></div>
    <div class="card"><h3>&#128200; Crypto Prices</h3><p>BTC, ETH, SOL, BNB, ADA, XRP and more &mdash; live from CoinGecko.</p><a href="/api/live/crypto">View Crypto &rarr;</a></div>
    <div class="card"><h3>&#127974; Demo Portfolio</h3><p>Paper-trading portfolio with live prices. $100K starting capital.</p><a href="/api/live/portfolio/demo">View Portfolio &rarr;</a></div>
    <div class="card"><h3>&#128209; Sector ETFs</h3><p>All 10 SPDR sector ETFs &mdash; XLK, XLF, XLE, XLV and more.</p><a href="/api/live/sectors">View Sectors &rarr;</a></div>
    <div class="card"><h3>&#128203; API Docs</h3><p>Full interactive Swagger documentation for all endpoints.</p><a href="/docs">Open Docs &rarr;</a></div>
    <div class="card"><h3>&#127917; Intelligence Panels</h3><p>Access all Quantora intelligence panels and dashboards.</p><a href="/ui/">Open Panels &rarr;</a></div>
  </div>
</div>
<script>
const BASE=window.location.origin;
async function loadTicker(){
  try{
    const r=await fetch(BASE+'/api/live/quotes?symbols=SPY,QQQ,AAPL,MSFT,NVDA');
    const data=await r.json();
    if(!Array.isArray(data))return;
    document.getElementById('ticker').innerHTML=data.map(q=>{
      const up=q.change_pct>=0;
      return '<span class="'+(up?'up':'dn')+'">'+q.symbol+' $'+Number(q.price||0).toFixed(2)+' '+(up?'&#9650;':'&#9660;')+Math.abs(q.change_pct||0).toFixed(2)+'%</span>&nbsp;&nbsp;&nbsp;';
    }).join('');
  }catch(e){document.getElementById('ticker').textContent='Market data loading…';}
}
async function loadStatus(){
  try{
    const r=await fetch(BASE+'/api/live/status');
    const d=await r.json();
    const isOpen=d.status&&d.status.includes('OPEN');
    document.getElementById('st').innerHTML='<span class="badge '+(isOpen?'open':'closed')+'">'+(d.status||'UNKNOWN')+'</span>';
  }catch(e){}
}
loadTicker();loadStatus();setInterval(loadTicker,30000);
</script>
</body>
</html>"""

# ── Startup hook ──────────────────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup():
    try:
        from backend.app.startup import initialize_state
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, initialize_state)
        logger.info("State initialization complete")
    except Exception as e:
        logger.warning(f"State init skipped: {e}")
