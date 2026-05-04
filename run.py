"""
Quantora Financial Intelligence OS â Production Entry Point
===========================================================
This file is the single entry-point used by Railway (and any other host).
It imports the existing FastAPI app from backend/app/main.py, then:
  1. Adds permissive CORS for production
  2. Mounts the /frontend directory as static files at /ui
  3. Wires up the real live-market-data router at /api/live/*
  4. Runs state initialization on startup
  5. Exposes /health for Railway health-checks
  6. Serves the world-class landing page at /
  7. Stripe billing: webhook, checkout sessions, customer portal
  8. Rate limiting: Free (60 req/min), Pro (600 req/min), Enterprise (6000 req/min)

Start command: uvicorn run:app --host 0.0.0.0 --port $PORT
"""
import os
import sys
import time
import hmac
import hashlib
import logging
import asyncio
import secrets
from pathlib import Path
from typing import Optional
from collections import defaultdict

# ââ Path setup ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("quantora.run")

# ââ Environment âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
STRIPE_SECRET_KEY       = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET   = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRO_PRICE_ID     = os.getenv("STRIPE_PRO_PRICE_ID", "")
STRIPE_ENT_PRICE_ID     = os.getenv("STRIPE_ENT_PRICE_ID", "")
APP_URL                 = os.getenv("APP_URL", "https://web-production-fe9f5.up.railway.app")
API_MASTER_KEY          = os.getenv("API_MASTER_KEY", secrets.token_urlsafe(32))

# ââ Import the main FastAPI app âââââââââââââââââââââââââââââââââââââââââââââââ
from fastapi import FastAPI
app = FastAPI(
    title="Quantora Financial Intelligence OS",
    description="Real-time financial intelligence platform",
    version="4.0.0",
)
logger.info("✅ FastAPI app initialized (clean instance, no backend lifespan)")

# ââ FastAPI / Starlette imports âââââââââââââââââââââââââââââââââââââââââââââââ
from fastapi import Request, HTTPException, Header, Depends
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

# ââ CORS ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.info("â CORS configured (allow *)")

# âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
#  RATE LIMITING
#  In-process token-bucket per (api_key OR IP), no Redis required.
#  Tier limits (requests / 60 s window):
#    free       â   60
#    pro        â  600
#    enterprise â 6000
# âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

TIER_LIMITS = {"free": 60, "pro": 600, "enterprise": 6000}

# In-memory store: key â {"tokens": float, "last_refill": float, "tier": str}
_rate_store: dict = defaultdict(lambda: None)

def _get_bucket(client_id: str, tier: str) -> dict:
    limit = TIER_LIMITS.get(tier, 60)
    bucket = _rate_store[client_id]
    now = time.monotonic()
    if bucket is None:
        bucket = {"tokens": float(limit), "last_refill": now, "tier": tier, "limit": limit}
        _rate_store[client_id] = bucket
    else:
        # Refill tokens proportional to elapsed time (token bucket)
        elapsed = now - bucket["last_refill"]
        refill = elapsed * (limit / 60.0)  # tokens per second = limit/60
        bucket["tokens"] = min(float(limit), bucket["tokens"] + refill)
        bucket["last_refill"] = now
        bucket["limit"] = limit
        bucket["tier"] = tier
    return bucket

def _check_rate(client_id: str, tier: str) -> tuple[bool, dict]:
    """Returns (allowed, headers_dict)."""
    bucket = _get_bucket(client_id, tier)
    limit = bucket["limit"]
    remaining = max(0, int(bucket["tokens"]) - 1)
    if bucket["tokens"] >= 1.0:
        bucket["tokens"] -= 1.0
        return True, {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Tier": tier,
        }
    reset_in = int((1.0 - bucket["tokens"]) / (limit / 60.0)) + 1
    return False, {
        "X-RateLimit-Limit": str(limit),
        "X-RateLimit-Remaining": "0",
        "X-RateLimit-Tier": tier,
        "Retry-After": str(reset_in),
    }

# ââ API-key â tier lookup (in-memory, upgraded by Stripe webhook) âââââââââââââ
# Structure: { api_key: {"tier": str, "customer_id": str, "email": str} }
_api_keys: dict = {}

# Optionally bootstrap a dev key from env
_dev_key = os.getenv("DEV_API_KEY", "")
if _dev_key:
    _api_keys[_dev_key] = {"tier": "pro", "customer_id": "dev", "email": "dev@quantora.ai"}

def _resolve_client(request: Request) -> tuple[str, str]:
    """Return (client_id, tier) for rate limiting."""
    auth = request.headers.get("Authorization", "")
    api_key = ""
    if auth.startswith("Bearer "):
        api_key = auth[7:].strip()
    elif auth.startswith("ApiKey "):
        api_key = auth[7:].strip()
    # Also check X-Api-Key header
    if not api_key:
        api_key = request.headers.get("X-Api-Key", "").strip()

    if api_key and api_key in _api_keys:
        info = _api_keys[api_key]
        return api_key, info["tier"]
    # Fallback: IP-based free tier
    ip = request.client.host if request.client else "unknown"
    return f"ip:{ip}", "free"

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Apply rate limiting to all /api/* routes."""
    SKIP_PATHS = {"/health", "/", "/docs", "/redoc", "/openapi.json"}

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        # Only rate-limit API paths
        if not path.startswith("/api/"):
            return await call_next(request)
        # Skip Stripe webhook (raw body needed, no key expected)
        if path == "/api/billing/webhook":
            return await call_next(request)

        client_id, tier = _resolve_client(request)
        allowed, rl_headers = _check_rate(client_id, tier)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": f"Too many requests. Your tier: {tier}. Upgrade at {APP_URL}/pricing",
                    "upgrade_url": f"{APP_URL}/pricing",
                },
                headers=rl_headers,
            )
        response = await call_next(request)
        for k, v in rl_headers.items():
            response.headers[k] = v
        return response

app.add_middleware(RateLimitMiddleware)
logger.info("â Rate limiting middleware registered (free/pro/enterprise)")

# âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
#  STRIPE BILLING
# âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

def _stripe_available() -> bool:
    try:
        import stripe  # noqa: F401
        return bool(STRIPE_SECRET_KEY)
    except ImportError:
        return False

# ââ /api/billing/create-checkout âââââââââââââââââââââââââââââââââââââââââââââ
@app.post("/api/billing/create-checkout", tags=["billing"])
async def create_checkout(request: Request):
    """
    Create a Stripe Checkout Session.
    Body: { "plan": "pro" | "enterprise", "email": "user@example.com" }
    Returns: { "url": "https://checkout.stripe.com/..." }
    """
    if not _stripe_available():
        raise HTTPException(503, "Stripe not configured. Set STRIPE_SECRET_KEY.")
    import stripe
    stripe.api_key = STRIPE_SECRET_KEY

    body = await request.json()
    plan  = body.get("plan", "pro")
    email = body.get("email", "")

    price_id = STRIPE_ENT_PRICE_ID if plan == "enterprise" else STRIPE_PRO_PRICE_ID
    if not price_id:
        raise HTTPException(400, f"STRIPE_{plan.upper()}_PRICE_ID not set in environment.")

    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            customer_email=email or None,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=f"{APP_URL}/dashboard?upgrade=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{APP_URL}/pricing?upgrade=cancelled",
            metadata={"plan": plan},
        )
        return JSONResponse({"url": session.url, "session_id": session.id})
    except stripe.error.StripeError as e:
        logger.error(f"Stripe checkout error: {e}")
        raise HTTPException(500, str(e))

# ââ /api/billing/portal âââââââââââââââââââââââââââââââââââââââââââââââââââââââ
@app.post("/api/billing/portal", tags=["billing"])
async def billing_portal(request: Request):
    """
    Create a Stripe Customer Portal session for subscription management.
    Body: { "customer_id": "cus_xxx" }
    Returns: { "url": "https://billing.stripe.com/..." }
    """
    if not _stripe_available():
        raise HTTPException(503, "Stripe not configured.")
    import stripe
    stripe.api_key = STRIPE_SECRET_KEY

    body = await request.json()
    customer_id = body.get("customer_id", "")
    if not customer_id:
        raise HTTPException(400, "customer_id required")

    try:
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=f"{APP_URL}/dashboard",
        )
        return JSONResponse({"url": session.url})
    except stripe.error.StripeError as e:
        raise HTTPException(500, str(e))

# ââ /api/billing/webhook ââââââââââââââââââââââââââââââââââââââââââââââââââââââ
@app.post("/api/billing/webhook", tags=["billing"])
async def stripe_webhook(request: Request):
    """
    Stripe webhook endpoint. Set your webhook URL in Stripe Dashboard to:
      https://<your-domain>/api/billing/webhook
    Handles: checkout.session.completed, customer.subscription.updated/deleted
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if STRIPE_WEBHOOK_SECRET:
        if not _stripe_available():
            raise HTTPException(503, "Stripe not configured.")
        import stripe
        stripe.api_key = STRIPE_SECRET_KEY
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
        except stripe.error.SignatureVerificationError:
            logger.warning("Stripe webhook signature verification failed")
            raise HTTPException(400, "Invalid signature")
    else:
        # Dev mode: no signature check
        import json
        event = json.loads(payload)

    etype = event.get("type", "")
    data  = event.get("data", {}).get("object", {})
    logger.info(f"Stripe webhook: {etype}")

    if etype == "checkout.session.completed":
        _handle_checkout_complete(data)
    elif etype in ("customer.subscription.updated", "customer.subscription.created"):
        _handle_subscription_update(data)
    elif etype == "customer.subscription.deleted":
        _handle_subscription_deleted(data)

    return JSONResponse({"received": True})

def _handle_checkout_complete(session: dict):
    customer_id   = session.get("customer", "")
    customer_email = session.get("customer_email", "") or session.get("customer_details", {}).get("email", "")
    plan = session.get("metadata", {}).get("plan", "pro")
    tier = "enterprise" if plan == "enterprise" else "pro"
    api_key = _provision_api_key(customer_id, customer_email, tier)
    logger.info(f"â New subscription: {customer_email} â {tier} (key: {api_key[:8]}â¦)")

def _handle_subscription_update(sub: dict):
    customer_id = sub.get("customer", "")
    status = sub.get("status", "")
    # Find existing key for this customer and update tier
    if status in ("active", "trialing"):
        plan = sub.get("metadata", {}).get("plan", "pro")
        tier = "enterprise" if plan == "enterprise" else "pro"
        for key, info in _api_keys.items():
            if info.get("customer_id") == customer_id:
                info["tier"] = tier
                logger.info(f"Updated key tier â {tier} for customer {customer_id}")
                return
        _provision_api_key(customer_id, "", tier)
    elif status in ("canceled", "unpaid", "past_due"):
        _downgrade_to_free(customer_id)

def _handle_subscription_deleted(sub: dict):
    customer_id = sub.get("customer", "")
    _downgrade_to_free(customer_id)

def _provision_api_key(customer_id: str, email: str, tier: str) -> str:
    # Check if customer already has a key
    for key, info in _api_keys.items():
        if info.get("customer_id") == customer_id:
            info["tier"] = tier
            if email:
                info["email"] = email
            return key
    # Issue new key
    new_key = f"qnt_{tier[:3]}_{secrets.token_urlsafe(24)}"
    _api_keys[new_key] = {"tier": tier, "customer_id": customer_id, "email": email}
    return new_key

def _downgrade_to_free(customer_id: str):
    for key, info in _api_keys.items():
        if info.get("customer_id") == customer_id:
            info["tier"] = "free"
            logger.info(f"Downgraded customer {customer_id} â free")
            return

# ââ /api/billing/status âââââââââââââââââââââââââââââââââââââââââââââââââââââââ
@app.get("/api/billing/status", tags=["billing"])
async def billing_status(request: Request):
    """Return current subscription tier for the calling API key."""
    client_id, tier = _resolve_client(request)
    is_key = not client_id.startswith("ip:")
    info = _api_keys.get(client_id, {}) if is_key else {}
    return JSONResponse({
        "tier": tier,
        "authenticated": is_key,
        "email": info.get("email", ""),
        "limits": {
            "requests_per_minute": TIER_LIMITS.get(tier, 60),
        },
        "upgrade_url": f"{APP_URL}/pricing" if tier == "free" else None,
    })

# ââ /api/billing/issue-key (admin) âââââââââââââââââââââââââââââââââââââââââââ
@app.post("/api/billing/issue-key", tags=["billing"])
async def issue_api_key(request: Request, x_master_key: Optional[str] = Header(None)):
    """
    Admin endpoint: manually provision an API key.
    Requires X-Master-Key header matching API_MASTER_KEY env var.
    Body: { "email": "...", "tier": "pro"|"enterprise", "customer_id": "..." }
    """
    if not x_master_key or x_master_key != API_MASTER_KEY:
        raise HTTPException(403, "Invalid master key")
    body = await request.json()
    email       = body.get("email", "")
    tier        = body.get("tier", "pro")
    customer_id = body.get("customer_id", f"manual_{secrets.token_hex(8)}")
    new_key = _provision_api_key(customer_id, email, tier)
    return JSONResponse({"api_key": new_key, "tier": tier, "email": email})

logger.info("â Stripe billing endpoints registered (/api/billing/*)")

# âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
#  EXISTING ROUTERS
# âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ


# ââ Static file serving âââââââââââââââââââââââââââââââââââââââââââââââââââââââ
from fastapi.staticfiles import StaticFiles

frontend_dir = BASE_DIR / "frontend"
if frontend_dir.exists():
    try:
        pass
    except Exception:
        pass
import urllib.request as _ur
import json as _jn
_REVEAL='<script>(function(){function rev(e){e.style.opacity="";e.style.transform="";e.classList.add("visible");}function sR(){var v=window.innerHeight+500;document.querySelectorAll(".reveal").forEach(function(e){if(e.getBoundingClientRect().top<v)rev(e);});}if("IntersectionObserver"in window){var ro=new IntersectionObserver(function(entries){entries.forEach(function(x){if(x.isIntersecting)rev(x.target);});},{threshold:0,rootMargin:"200px 0px 0px 0px"});document.querySelectorAll(".reveal").forEach(function(e){ro.observe(e);});}setTimeout(sR,50);window.addEventListener("scroll",sR,{passive:true});function rC(el){if(el._d)return;el._d=1;var t=parseInt(el.dataset.val||0),d=1800,t0=null;(function s(ts){if(!t0)t0=ts;var p=Math.min((ts-t0)/d,1),e2=1-Math.pow(1-p,3);el.textContent=Math.round(t*e2);if(p<1)requestAnimationFrame(s);else el.textContent=t;})(performance.now());}function cC(){var v=window.innerHeight+200;document.querySelectorAll(".js-counter").forEach(function(el){var r=el.getBoundingClientRect();if(r.top<v&&r.top>-500)rC(el);});}setTimeout(cC,150);window.addEventListener("scroll",cC,{passive:true});})();</script>'
_TICKER='<script>(function(){var M={"BTC/USD":"BTC-USD","ETH/USD":"ETH-USD","GOLD":"GC=F","WTI":"CL=F","EURUSD":"EURUSD=X","GBPUSD":"GBPUSD=X","VIX":"^VIX"};function fmt(p){return p>=1000?"$"+p.toLocaleString("en-US",{minimumFractionDigits:2,maximumFractionDigits:2}):p>=1?"$"+p.toFixed(2):"$"+p.toFixed(4);}function upd(data){document.querySelectorAll(".ticker-item").forEach(function(item){var s=item.querySelector(".ti-sym");if(!s)return;var sym=s.textContent.trim();var k=M[sym]||sym;var d=data[k];if(!d||!d.price)return;var pp=item.querySelector(".ti-price");var cc=item.querySelector(".ti-chg");if(pp)pp.textContent=fmt(d.price);if(cc){cc.textContent=(d.change>=0?"+":"")+d.change.toFixed(2)+"%";cc.className="ti-chg "+(d.change>=0?"pos":"neg");}});}function go(){fetch("/api/prices").then(function(r){return r.json();}).then(upd).catch(function(){});}setTimeout(go,800);setInterval(go,30000);})();</script>'
@app.get("/",response_class=HTMLResponse)
async def serve_index():
    with open("frontend/index.html","r",encoding="utf-8") as f:
        html=f.read()
    return html.replace("</body>",_REVEAL+_TICKER+"\n</body>")
_SYMS="AAPL,NVDA,TSLA,MSFT,GOOGL,META,SPY,QQQ,GC=F,CL=F,BTC-USD,ETH-USD,EURUSD=X,GBPUSD=X,^VIX"
@app.get("/api/prices")
async def get_prices():
    try:
        import yfinance as yf
        syms=["AAPL","NVDA","TSLA","MSFT","GOOGL","META","SPY","QQQ","GC=F","CL=F","BTC-USD","ETH-USD","EURUSD=X","GBPUSD=X","^VIX"]
        out={}
        for s in syms:
            try:
                t=yf.Ticker(s)
                fi=t.fast_info
                price=float(fi.last_price or fi.previous_close or 0)
                prev=float(fi.previous_close or price or 1)
                change=round(((price-prev)/prev*100) if prev else 0,4)
                out[s]={"price":round(price,4),"change":change}
            except Exception:
                out[s]={"price":0,"change":0}
        return out
    except Exception as ex:
        return {"error":str(ex)}

@app.get("/pricing", response_class=HTMLResponse, tags=["pages"])
def pricing_page():
    p = frontend_dir / "pricing.html"
    if p.exists():
        return HTMLResponse(content=p.read_text(encoding="utf-8"))
    return RedirectResponse("/ui/pricing.html")

# ââ Dashboard page ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
@app.get("/dashboard", response_class=HTMLResponse, tags=["pages"])
def dashboard_page():
    p = frontend_dir / "dashboard.html"
    if p.exists():
        return HTMLResponse(content=p.read_text(encoding="utf-8"))
    return RedirectResponse("/ui/dashboard.html")

# ââ Health endpoint âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
@app.get("/health", tags=["system"])
def health():
    return JSONResponse({
        "status": "ok",
        "service": "Quantora Financial Intelligence OS",
        "stripe": _stripe_available(),
        "rate_limiting": True,
        "active_api_keys": len(_api_keys),
    })

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
  <span class="live" id="mktstatus">â¬¤ Loading market statusâ¦</span>
  <span id="mkttime">â</span>
  <span>Real data: Yahoo Finance + CoinGecko</span>
</div>
<div class="main">
  <h2>â¡ Quantora Financial Intelligence OS</h2>
  <p style="color:var(--muted);font-size:0.9rem;margin-bottom:2rem;">
    Visit <a href="/pricing" style="color:var(--accent);">/pricing</a> to get an API key,
    or <a href="/dashboard" style="color:var(--accent);">/dashboard</a> to access your workspace.
    Full API docs at <a href="/docs" style="color:var(--accent);">/docs</a>.
  </p>
</div>
<footer>Quantora Financial Intelligence OS &nbsp;Â·&nbsp; Real market data via Yahoo Finance &amp; CoinGecko</footer>
<script>
const BASE = window.location.origin;
async function loadStatus() {
  try {
    const r = await fetch(BASE + '/api/live/status');
    const d = await r.json();
    const el = document.getElementById('mktstatus');
    const isOpen = d.status === 'OPEN';
    el.textContent = (isOpen ? 'â¬¤ US Market OPEN' : 'â¯ US Market ' + d.status);
    el.style.color = isOpen ? 'var(--green)' : 'var(--muted)';
  } catch(e) {}
  document.getElementById('mkttime').textContent = new Date().toUTCString();
}
loadStatus();
setInterval(loadStatus, 30000);
</script>
</body>
</html>"""
