"""
Quantora Production Entry Point — run.py
Railway start command: uvicorn run:app --host 0.0.0.0 --port $PORT --workers 1
"""
from __future__ import annotations
import asyncio
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Import main app ──────────────────────────────────────────────────────────
try:
    from backend.app.main import app
    logger.info("Main app imported successfully")
    _main_imported = True
except Exception as e:
    logger.warning(f"Main app import failed ({e}) — using minimal fallback app")
    from fastapi import FastAPI
    app = FastAPI(title="Quantora Financial Intelligence OS", version="1.0.0")
    _main_imported = False

# ── CORS ─────────────────────────────────────────────────────────────────────
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

# ── API URL shim middleware (fixes localhost:8010 in all frontend panels) ─────
try:
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request as StarletteRequest
    from starlette.responses import Response as StarletteResponse

    _SHIM = (
        b"<script>"
        b"(function(){"
        b"var _f=window.fetch;"
        b"window.fetch=function(u,o){"
        b"if(typeof u==='string')u=u.replace(/https?:\\/\\/localhost:\\d+/g,window.location.origin);"
        b"return _f.call(this,u,o);};"
        b"var _x=XMLHttpRequest.prototype.open;"
        b"XMLHttpRequest.prototype.open=function(m,u){"
        b"if(typeof u==='string')u=u.replace(/https?:\\/\\/localhost:\\d+/g,window.location.origin);"
        b"return _x.apply(this,arguments);};"
        b"})();"
        b"</script>"
    )

    class ApiShimMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: StarletteRequest, call_next):
            response = await call_next(request)
            ct = response.headers.get("content-type", "")
            if "text/html" in ct:
                body = b""
                async for chunk in response.body_iterator:
                    body += chunk
                if b"</head>" in body:
                    body = body.replace(b"</head>", _SHIM + b"</head>", 1)
                elif b"<body" in body:
                    idx = body.index(b"<body")
                    end = body.index(b">", idx)
                    body = body[: end + 1] + _SHIM + body[end + 1 :]
                else:
                    body = _SHIM + body
                headers = dict(response.headers)
                headers["content-length"] = str(len(body))
                return StarletteResponse(
                    content=body,
                    status_code=response.status_code,
                    headers=headers,
                    media_type="text/html",
                )
            return response

    app.middleware_stack = None
    app.add_middleware(ApiShimMiddleware)
    logger.info("API URL shim middleware added (localhost → dynamic origin)")
except Exception as e:
    logger.warning(f"Shim middleware not loaded: {e}")

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
        app.mount("/ui", StaticFiles(directory="frontend", html= True), name="ui")
        logger.info("Frontend mounted at /ui/")
except Exception as e:
    logger.warning(f"Static files not mounted: {e}")

# ── Health check ─────────────────────────────────────────────────────────────────
from fastapi.responses import JSONResponse, HTMLResponse

@app.get("/health")
def health():
    return JSONResponse({(��]\Ȏ���ȋ�XZ[��\���XZ[��[\ܝY��\��[ۈ�������JB���8� 8� ]]�\�[H8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� 8� �[\ܝ��\�����[]L�\���K\�X�\���Xܙ]�\���X�[YH\��KXX�\��K��ۈ\�ڛ��[\ܝ�\�M�\�؍�����H�\�\H[\ܝ�\]Y\�\�ԙ\B����H�\�ses import JSONResponse as _JR
from pydantic import BaseModel as _BM

_DB_PATH = _os.path.join(_os.path.dirname(__file__), "quantora_users.db")
_JWT_SECRET = _os.environ.get("JWT_SECRET", "quantora-intelligence-os-secret-key-2024")
_JWT_ALG = b'{"alg":"HS256","typ":"JWT"}'

def _db():
    c = _sq.connect(_DB_PATH); c.row_factory = _sq.Row; return c

def _init_db():
    c = _db()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        plan TEXT DEFAULT 'starter',
        created_at INTEGER DEFAULT (CAST(strftime('%s','now') AS INTEGER))
    )""")
    c.commit(); c.close()

_init_db()

def _hash_pw(pw: str) -> str:
    salt = _sec.token_hex(16)
    h = _hl.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 200000)
    return salt + ":" + h.hex()

def _verify_pw(pw: str, stored: str) -> bool:
    try:
        salt, h = stored.split(":")
        return _hl.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 200000).hex() == h
    except Exception:
        return False

def _make_token(email: str) -> str:
    header = _b64.urlsafe_b64encode(_JWT_ALG).rstrip(b"=").decode()
    payload = _jn.dumps({"sub": email, "exp": int(_tm.time()) + 86400 * 30})
    body = _b64.urlsafe_b64encode(payload.encode()).rstrip(b"=").decode()
    sig_input = f"{header}.{body}".encode()
    sig = _b64.urlsafe_b64encode(
        _hm.new(_JWT_SECRET.encode(), sig_input, _hl.sha256).digest()
    ).rstrip(b"=").decode()
    return f"{header}.{body}.{sig}"

def _decode_token(token: str):
    try:
        h, b, s = token.split(".")
        expected = _b64.urlsafe_b64encode(
            _hm.new(_JWT_SECRET.encode(), f"{h}.{b}".encode(), _hl.sha256).digest()
        ).rstrip(b"=").decode()
        if s != expected: return None
        payload = _jn.loads(_b64.urlsafe_b64decode(b + "=="))
        if payload.get("exp", 0) < _tm.time(): return None
        return payload.get("sub")
    except Exception:
        return None

class _RegReq(_BM):
    name: str
    email: str
    password: str
    plan: str = "starter"

class _LoginReq(_BM):
    email: str
    password: str

@app.post("/auth/register")
async def auth_register(req: _RegReq):
    if not req.email or not req.password or not req.name:
        return _JR({"error": "All fields are required."}, status_code=400)
    if len(req.password) < 8:
        return _JR({"error": "Password must be at least 8 characters."}, status_code=400)
    try:
        c = _db()
        if c.execute("SELECT id FROM users WHERE email=?", (req.email.lower(),)).fetchone():
            c.close(); return _JR({"error": "Email already registered. Please sign in."}, status_code=400)
        c.execute("INSERT INTO users (email, name, password_hash, plan) VALUES (?,?,?,?)",
                  (req.email.lower(), req.name.strip(), _hash_pw(req.password), req.plan))
        c.commit(); c.close()
        token = _make_token(req.email.lower())
        return {"token": token, "email": req.email.lower(), "name": req.name.strip(), "plan": req.plan}
    except Exception as e:
        return _JR({"error": str(e)}, status_code=500)

@app.post("/auth/login")
async def auth_login(req: _LoginReq):
    try:
        c = _db()
        user = c.execute("SELECT * FROM users WHERE email=?", (req.email.lower(),)).fetchone()
        c.close()
        if not user or not _verify_pw(req.password, user["password_hash"]):
            return _JR({"error": "Invalid email or password."}, status_code=401)
        token = _make_token(req.email.lower())
        return {"token": token, "email": user["email"], "name": user["name"], "plan": user["plan"]}
    except Exception as e:
        return _JR({"error": str(e)}, status_code=500)

@app.get("/auth/me")
async def auth_me(request: _Req):
    auth = request.headers.get("Authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else ""
    email = _decode_token(token)
    if not email:
        return _JR({"error": "Unauthorized"}, status_code=401)
    c = _db()
    user = c.execute("SELECT email, name, plan, created_at FROM users WHERE email=?", (email,)).fetchone()
    c.close()
    if not user:
        return _JR({"error": "User not found"}, status_code=404)
    return {"email": user["email"], "name": user["name"], "plan": user["plan"], "created_at": user["created_at"]}

@app.get("/login")
def login_page():
    p = _os.path.join(_os.path.dirname(__file__), "frontend", "login.html")
    try:
        with open(p, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        from fastapi.responses import RedirectResponse
      2 return RedirectResponse(url="/signup")

@app.get("/signup")
def signup_page():
    p = _os.path.join(_os.path.dirname(__file__), "frontend", "signup.html")
    try:
        with open(p, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/")

# ── Pricing page ───────────────────────────────────────────────────────────────
@app.get("/pricing")
def pricing():
    pricing_path = _os.path.join(_os.path.dirname(__file__), "frontend", "pricing.html")
    try:
        with open(pricing_path, "r", encoding="utf-8") as f:
            content = f.read()
        return HTMLResponse(content=content)
    except FileNotFoundError:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/ui/")

# ── Landing page ──────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return HTMLResponse(content=_landing_html())

def _landing_html() -> str:
    return r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Quantora — Financial Intelligence OS</title>
<style>
  :root {
    --bg: #050a14;
    --bg2: #0a1020;
    --bg3: #0d1528;
    --card: #0f1a2e;
    --border: #1a2d4a;
    --border2: #1e3a5f;
    --cyan: #00d4ff;
    --purple: #7b2fff;
    --green: #10b981;
    --red: #ef4444;
    --gold: #f59e0b;
    --text: #e2e8f0;
    --muted: #64748b;
    --dim: #94a3b8;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html { scroll-behavior: smooth; }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', sans-serif;
    min-height: 100vh;
    overflow-x: hidden;
  }

  /* ── HEADER ── */
  .header {
    background: linear-gradient(180deg, #0a0f1e 0%, var(--bg) 100%);
    border-bottom: 1px solid var(--border2);
    padding: 0 40px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 64px;
    position: sticky;
    top: 0;
    z-index: 100;
    backdrop-filter: blur(12px);
  }
  .logo {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .logo-icon {
    width: 36px; height: 36px;
    background: linear-gradient(135deg, var(--cyan), var(--purple));
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 18px;
  }
  .logo-text {
    font-size: 1.3rem;
    font-weight: 800;
    background: linear-gradient(90deg, var(--cyan), var(--purple));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -0.5px;
  }
  .logo-version {
    font-size: 0.65rem;
    color: var(--muted);
    font-weight: 600;
    margin-top: 2px;
    letter-spacing: 1px;
  }
  .header-right {
    display: flex;
    align-items: center;
    gap: 16px;
  }
  .status-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: var(--green);
    box-shadow: 0 0 8px var(--green);
    animation: pulse 2s infinite;
  }
  @keyframes pulse {
    0%,100% { opacity: 1; } 50% { opacity: 0.4; }
  }
  .status-label { font-size: 0.8rem; color: var(--green); font-weight: 600; }
  .nav-btn {
    padding: 7px 16px;
    border-radius: 6px;
    font-size: 0.8rem;
    font-weight: 600;
    text-decoration: none;
    transition: all 0.2s;
    border: 1px solid transparent;
  }
  .nav-btn-ghost {
    color: var(--dim);
    border-color: var(--border);
  }
  .nav-btn-ghost:hover { color: var(--cyan); border-color: var(--cyan); }
  .nav-btn-primary {
    background: linear-gradient(135deg, var(--cyan), var(--purple));
    color: #fff;
  }
  .nav-btn-primary:hover { opacity: 0.85; }

  /* ── TICKER ── */
  .ticker-bar {
    background: var(--bg2);
    border-bottom: 1px solid var(--border);
    padding: 0;
    height: 38px;
    overflow: hidden;
    display: flex;
    align-items: center;
    position: relative;
  }
  .ticker-label {
    background: linear-gradient(90deg, var(--cyan), var(--purple));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 0.7rem;
    font-weight: 900;
    letter-spacing: 2px;
    padding: 0 16px;
    white-space: nowrap;
    border-right: 1px solid var(--border);
    height: 100%;
    display: flex;
    align-items: center;
  }
  .ticker-scroll {
    display: flex;
    animation: scroll 40s linear infinite;
    padding-left: 40px;
    gap: 40px;
    align-items: center;
  }
  .ticker-scroll:hover { animation-play-state: paused; }
  @keyframes scroll {
    0% { transform: translateX(0); }
    100% { transform: translateX(-50%); }
  }
  .tick-item { font-family: 'SF Mono', 'Fira Code', monospace; font-size: 0.78rem; white-space: nowrap; }
  .tick-sym { color: #fff; font-weight: 700; margin-right: 6px; }
  .tick-price { color: var(--dim); margin-right: 4px; }
  .up { color: var(--green); }
  .dn { color: var(--red); }

  /* ── HERO ── */
  .hero {
    background: linear-gradient(135deg, var(--bg3) 0%, var(--bg) 100%);
    padding: 60px 40px 40px;
    text-align: center;
    position: relative;
    overflow: hidden;
  }
  .hero::before {
    content: '';
    position: absolute;
    top: -100px; left: 50%;
    transform: translateX(-50%);
    width: 600px; height: 300px;
    background: radial-gradient(ellipse, rgba(0,212,255,0.08) 0%, transparent 70%);
    pointer-events: none;
  }
  .hero-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 16px;
    border: 1px solid var(--border2);
    border-radius: 20px;
    font-size: 0.75rem;
    color: var(--cyan);
    font-weight: 600;
    letter-spacing: 1px;
    margin-bottom: 24px;
    background: rgba(0,212,255,0.05);
  }
  .hero h1 {
    font-size: 3.2rem;
    font-weight: 900;
    letter-spacing: -1.5px;
    line-height: 1.1;
    margin-bottom: 16px;
    background: linear-gradient(90deg, #fff 0%, var(--cyan) 50%, var(--purple) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  .hero p {
    font-size: 1.15rem;
    color: var(--dim);
    max-width: 640px;
    margin: 0 auto 36px;
    line-height: 1.6;
  }
  .hero-btns {
    display: flex;
    gap: 16px;
    justify-content: center;
    flex-wrap: wrap;
  }
  .btn-lg {
    padding: 14px 32px;
    border-radius: 10px;
    font-size: 1rem;
    font-weight: 700;
    text-decoration: none;
    transition: all 0.2s;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    border: none;
    cursor: pointer;
  }
  .btn-primary {
    background: linear-gradient(135deg, var(--cyan), var(--purple));
    color: #fff;
    box-shadow: 0 0 30px rgba(0,212,255,0.25);
  }
  .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 8px 40px rgba(0,212,255,0.35); }
  .btn-outline {
    background: transparent;
    color: var(--text);
    border: 1px solid var(--border2);
  }
  .btn-outline:hover { border-color: var(--cyan); color: var(--cyan); }

  /* ── MARKET STATUS BAR ── */
  .market-bar {
    background: var(--bg2);
    border-top: 1px solid var(--border);
    border-bottom: 1px solid var(--border);
    padding: 20px 40px;
    display: flex;
    gap: 0;
    align-items: stretch;
    overflow-x: auto;
  }
  .mstat {
    flex: 1;
    min-width: 140px;
    padding: 0 24px;
    border-right: 1px solid var(--border);
    text-align: center;
  }
  .mstat:first-child { padding-left: 0; }
  .mstat:last-child { border-right: none; }
  .mstat-label { font-size: 0.7rem; color: var(--muted); font-weight: 600; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 6px; }
  .mstat-value { font-size: 1.3rem; font-weight: 800; font-family: 'SF Mono', monospace; }
  .mstat-sub { font-size: 0.72rem; margin-top: 3px; }

  /* ── MAIN CONTENT ── */
  .main { padding: 40px; max-width: 1400px; margin: 0 auto; }

  /* ── SECTION TITLE ── */
  .section-title {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .section-title::after { content: ''; flex: 1; height: 1px; background: var(--border); }

  /* ── LIVE MARKET GRID ── */
  .market-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 12px;
    margin-bottom: 40px;
  }
  .mcard {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px;
    cursor: pointer;
    transition: all 0.2s;
  }
  .mcard:hover { border-color: var(--cyan); background: #121e34; }
  .mcard-sym { font-size: 0.75rem; font-weight: 800; color: var(--muted); letter-spacing: 1px; }
  .mcard-name { font-size: 0.78rem; color: var(--dim); margin-top: 2px; }
  .mcard-price { font-size: 1.4rem; font-weight: 800; font-family: 'SF Mono', monospace; margin-top: 8px; }
  .mcard-chg { font-size: 0.82rem; font-weight: 700; margin-top: 4px; }
  .mcard-vol { font-size: 0.7rem; color: var(--muted); margin-top: 6px; }

  /* ── FEATURES GRID ── */
  .features-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 20px;
    margin-bottom: 40px;
  }
  .fcard {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 24px;
    text-decoration: none;
    color: inherit;
    transition: all 0.2s;
    display: block;
    position: relative;
    overflow: hidden;
  }
  .fcard::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--cyan), var(--purple));
    transform: scaleX(0);
    transform-origin: left;
    transition: transform 0.3s;
  }
  .fcard:hover { border-color: var(--border2); transform: translateY(-3px); box-shadow: 0 12px 40px rgba(0,0,0,0.4); }
  .fcard:hover::before { transform: scaleX(1); }
  .fcard-icon { font-size: 2rem; margin-bottom: 12px; }
  .fcard-title { font-size: 1rem; font-weight: 700; color: #fff; margin-bottom: 6px; }
  .fcard-desc { font-size: 0.85rem; color: var(--dim); line-height: 1.5; }
  .fcard-tag {
    display: inline-block;
    margin-top: 14px;
    padding: 3px 10px;
    border-radius: 4px;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.5px;
  }
  .tag-live { background: rgba(16,185,129,0.15); color: var(--green); border: 1px solid rgba(16,185,129,0.3); }
  .tag-ai { background: rgba(123,47,255,0.15); color: #a78bfa; border: 1px solid rgba(123,47,255,0.3); }
  .tag-new { background: rgba(0,212,255,0.1); color: var(--cyan); border: 1px solid rgba(0,212,255,0.3); }
  .tag-pro { background: rgba(245,158,11,0.1); color: var(--gold); border: 1px solid rgba(245,158,11,0.3); }

  /* ── PORTFOLIO PANEL ── */
  .portfolio-panel {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 28px;
    margin-bottom: 40px;
  }
  .portfolio-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
  }
  .portfolio-title { font-size: 1rem; font-weight: 700; }
  .portfolio-badge {
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 700;
    background: rgba(16,185,129,0.1);
    color: var(--green);
    border: 1px solid rgba(16,185,129,0.3);
  }
  .portfolio-stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 20px;
  }
  .pstat { text-align: center; }
  .pstat-label { font-size: 0.7rem; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }
  .pstat-value { font-size: 1.8rem; font-weight: 900; font-family: 'SF Mono', monospace; margin-top: 6px; }
  .pstat-sub { font-size: 0.78rem; color: var(--muted); margin-top: 4px; }

  /* ── API STATUS ── */
  .api-status {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    margin-bottom: 40px;
  }
  .api-chip {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 14px;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 8px;
    font-size: 0.78rem;
  }
  .api-chip-dot { width: 6px; height: 6px; border-radius: 50%; }
  .chip-ok .api-chip-dot { background: var(--green); box-shadow: 0 0 6px var(--green); }
  .chip-warn .api-chip-dot { background: var(--gold); }
  .chip-err .api-chip-dot { background: var(--red); }
  .api-chip-name { color: var(--dim); font-weight: 600; }

  /* ── FOOTER ── */
  .footer {
    background: var(--bg2);
    border-top: 1px solid var(--border);
    padding: 40px;
    text-align: center;
    color: var(--muted);
    font-size: 0.82rem;
  }
  .footer a { color: var(--cyan); text-decoration: none; }
  .footer-logo {
    font-size: 1.4rem;
    font-weight: 900;
    background: linear-gradient(90deg, var(--cyan), var(--purple));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 12px;
  }

  /* ── SPINNER ── */
  .spin { display: inline-block; animation: spin 1s linear infinite; }
  @keyframes spin { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }
  .skeleton { background: linear-gradient(90deg, var(--border) 25%, var(--border2) 50%, var(--border) 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite; border-radius: 4px; }
  @keyframes shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
</style>
</head>
<body>

<!-- HEADER -->
<header class="header">
  <div class="logo">
    <div class="logo-icon">⚡</div>
    <div>
      <div class="logo-text">QUANTORA</div>
      <div class="logo-version">FINANCIAL INTELLIGENCE OS v2.0</div>
    </div>
  </div>
  <div class="header-right">
    <div class="status-dot"></div>
    <span class="status-label">LIVE</span>
    <a href="/pricing" class="nav-btn nav-btn-ghost">Pricing</a>
    <a href="/docs" class="nav-btn nav-btn-ghost">API Docs</a>
    <a href="/ui/" class="nav-btn nav-btn-ghost">Panels</a>
    <a href="/login" class="nav-btn nav-btn-ghost" id="navSignIn">Sign In</a>
    <a href="/signup" class="nav-btn nav-btn-primary" id="navGetStarted">Get Started →</a>
  </div>
</header>

<!-- TICKER -->
<div class="ticker-bar">
  <div class="ticker-label">LIVE</div>
  <div class="ticker-scroll" id="tickerScroll">
    <span class="tick-item"><span class="tick-sym">SPY</span><span class="tick-price">$—</span><span class="up">▲ —%</span></span>
    <span class="tick-item"><span class="tick-sym">QQQ</span><span class="tick-price">$—</span><span class="up">▲ —%</span></span>
    <span class="tick-item"><span class="tick-sym">AAPL</span><span class="tick-price">$—</span><span class="up">▲ —%</span></span>
    <span class="tick-item"><span class="tick-sym">MSFT</span><span class="tick-price">$—</span><span class="up">▲ —%</span></span>
    <span class="tick-item"><span class="tick-sym">NVDA</span><span class="tick-price">$—</span><span class="up">▲ —%</span></span>
    <span class="tick-item"><span class="tick-sym">TSLA</span><span class="tick-price">$—</span><span class="up">▲ —%</span></span>
    <span class="tick-item"><span class="tick-sym">BTC</span><span class="tick-price">$—</span><span class="up">▲ —%</span></span>
    <span class="tick-item"><span class="tick-sym">ETH</span><span class="tick-price">$—</span><span class="up">▲ —%</span></span>
    <span class="tick-item"><span class="tick-sym">SPY</span><span class="tick-price">$—</span><span class="up">▲ —%</span></span>
    <span class="tick-item"><span class="tick-sym">QQQ</span><span class="tick-price">$—</span><span class="up">▲ —%</span></span>
    <span class="tick-item"><span class="tick-sym">AAPL</span><span class="tick-price">$—</span><span class="up">▲ —%</span></span>
    <span class="tick-item"><span class="tick-sym">NVDA</span><span class="tick-price">$—</span><span class="up">▲ —%</span></span>
    <span class="tick-item"><span class="tick-sym">BTC</span><span class="tick-price">$—</span><span class="up">▲ —%</span></span>
    <span class="tick-item"><span class="tick-sym">ETH</span><span class="tick-price">$—</span><span class="up">▲ —%</span></span>
  </div>
</div>

<!-- HERO -->
<section class="hero">
  <div class="hero-badge">
    <span class="status-dot"></span>
    INSTITUTIONAL-GRADE INTELLIGENCE PLATFORM
  </div>
  <h1>Your Edge in Every<br>Market Condition</h1>
  <p>Real-time stock &amp; crypto intelligence, AI-powered signals, paper trading, risk management — all in one platform. Built for serious traders.</p>
  <div class="hero-btns">
    <a href="/ui/" class="btn-lg btn-primary">⚡ Launch Platform</a>
    <a href="/api/live/overview" class="btn-lg btn-outline">📊 Live Market Data</a>
  </div>
</section>

<!-- MARKET STATUS BAR -->
<div class="market-bar">
  <div class="mstat">
    <div class="mstat-label">Market Status</div>
    <div class="mstat-value" id="mktStatus"><span class="skeleton" style="width:80px;height:20px;display:inline-block"></span></div>
    <div class="mstat-sub" id="mktTime" style="color:var(--muted)">—</div>
  </div>
  <div class="mstat">
    <div class="mstat-label">S&amp;P 500 ETF</div>
    <div class="mstat-value up" id="spyVal">$—</div>
    <div class="mstat-sub" id="spyChg">—</div>
  </div>
  <div class="mstat">
    <div class="mstat-label">Nasdaq ETF</div>
    <div class="mstat-value up" id="qqqVal">$—</div>
    <div class="mstat-sub" id="qqqChg">—</div>
  </div>
  <div class="mstat">
    <div class="mstat-label">Bitcoin</div>
    <div class="mstat-value up" id="btcVal">$—</div>
    <div class="mstat-sub" id="btcChg">—</div>
  </div>
  <div class="mstat">
    <div class="mstat-label">Portfolio</div>
    <div class="mstat-value" id="portVal" style="color:var(--cyan)">$—</div>
    <div class="mstat-sub" style="color:var(--green)">Paper Trading</div>
  </div>
  <div class="mstat">
    <div class="mstat-label">24h Crypto Vol</div>
    <div class="mstat-value" id="cryptoVol" style="color:var(--purple)">$—</div>
    <div class="mstat-sub" style="color:var(--muted)">Global</div>
  </div>
</div>

<!-- MAIN -->
<div class="main">

  <!-- LIVE MARKET QUOTES -->
  <div class="section-title">Live Market Quotes</div>
  <div class="market-grid" id="marketGrid">
    <!-- Filled by JS -->
    <div class="mcard"><div class="skeleton" style="height:80px"></div></div>
    <div class="mcard"><div class="skeleton" style="height:80px"></div></div>
    <div class="mcard"><div class="skeleton" style="height:80px"></div></div>
    <div class="mcard"><div class="skeleton" style="height:80px"></div></div>
    <div class="mcard"><div class="skeleton" style="height:80px"></div></div>
    <div class="mcard"><div class="skeleton" style="height:80px"></div></div>
  </div>

  <!-- PORTFOLIO OVERVIEW -->
  <div class="portfolio-panel">
    <div class="portfolio-header">
      <div class="portfolio-title">📋 Paper Trading Portfolio</div>
      <div class="portfolio-badge">✓ ACTIVE — PAPER MODE</div>
    </div>
    <div class="portfolio-stats">
      <div class="pstat">
        <div class="pstat-label">Total Capital</div>
        <div class="pstat-value" id="totalCap" style="color:var(--cyan)">$100,000</div>
        <div class="pstat-sub">Starting balance</div>
      </div>
      <div class="pstat">
        <div class="pstat-label">Available</div>
        <div class="pstat-value" id="availCap" style="color:var(--green)">$—</div>
        <div class="pstat-sub">Cash reserve</div>
      </div>
      <div class="pstat">
        <div class="pstat-label">Deployed</div>
        <div class="pstat-value" id="allocCap" style="color:var(--purple)">$—</div>
        <div class="pstat-sub">In positions</div>
      </div>
      <div class="pstat">
        <div class="pstat-label">Total P&amp;L</div>
        <div class="pstat-value" id="totalPnl" style="color:var(--gold)">$—</div>
        <div class="pstat-sub">Unrealized</div>
      </div>
      <div class="pstat">
        <div class="pstat-label">Risk Mode</div>
        <div class="pstat-value" style="font-size:1.1rem;color:var(--green)">✓ SAFE</div>
        <div class="pstat-sub">Kill switch: OFF</div>
      </div>
    </div>
  </div>

  <!-- API STATUS -->
  <div class="section-title">System Status</div>
  <div class="api-status" id="apiStatus">
    <div class="api-chip chip-ok"><div class="api-chip-dot"></div><span class="api-chip-name">API Server</span></div>
    <div class="api-chip" id="chipMarket"><div class="api-chip-dot" style="background:var(--muted)"></div><span class="api-chip-name">Market Data</span></div>
    <div class="api-chip" id="chipCrypto"><div class="api-chip-dot" style="background:var(--muted)"></div><span class="api-chip-name">CoinGecko</span></div>
    <div class="api-chip" id="chipOperator"><div class="api-chip-dot" style="background:var(--muted)"></div><span class="api-chip-name">Operator Core</span></div>
    <div class="api-chip chip-ok"><div class="api-chip-dot"></div><span class="api-chip-name">Risk Engine</span></div>
    <div class="api-chip chip-ok"><div class="api-chip-dot"></div><span class="api-chip-name">State Manager</span></div>
  </div>

  <!-- PLATFORM FEATURES -->
  <div class="section-title" style="margin-top:16px">Platform Modules</div>
  <div class="features-grid">

    <a class="fcard" href="/ui/">
      <div class="fcard-icon">🖥️</div>
      <div class="fcard-title">Intelligence Panels</div>
      <div class="fcard-desc">537 live panels covering every dimension of market analysis — from macro to micro, fundamental to technical.</div>
      <span class="fcard-tag tag-live">537 PANELS</span>
    </a>

    <a class="fcard" href="/api/live/overview">
      <div class="fcard-icon">📡</div>
      <div class="fcard-title">Market Overview API</div>
      <div class="fcard-desc">Real-time market breadth, indices, sector performance, and macro conditions. Updated every 30 seconds.</div>
      <span class="fcard-tag tag-live">LIVE DATA</span>
    </a>

    <a class="fcard" href="/api/live/crypto">
      <div class="fcard-icon">₿</div>
      <div class="fcard-title">Crypto Intelligence</div>
      <div class="fcard-desc">BTC, ETH, SOL, BNB, ADA, XRP live prices with 24h change, volume, and market cap from CoinGecko.</div>
      <span class="fcard-tag tag-live">LIVE PRICES</span>
    </a>

    <a class="fcard" href="/api/live/quotes?symbols=AAPL,MSFT,NVDA,TSLA,AMZN,GOOGL">
      <div class="fcard-icon">📊</div>
      <div class="fcard-title">Equity Quotes</div>
      <div class="fcard-desc">Real-time stock quotes for any ticker via Yahoo Finance. Batch queries supported. No API key required.</div>
      <span class="fcard-tag tag-live">REAL-TIME</span>
    </a>

    <a class="fcard" href="/api/live/sectors">
      <div class="fcard-icon">🏛️</div>
      <div class="fcard-title">Sector ETF Tracker</div>
      <div class="fcard-desc">All 10 SPDR sector ETFs tracked in real-time. Identify rotating capital flows and sector momentum.</div>
      <span class="fcard-tag tag-ai">FLOW ANALYSIS</span>
    </a>

    <a class="fcard" href="/api/live/portfolio/demo">
      <div class="fcard-icon">💼</div>
      <div class="fcard-title">Paper Portfolio</div>
      <div class="fcard-desc">$100,000 simulated portfolio with live mark-to-market pricing. Track P&amp;L, exposure, and risk metrics.</div>
      <span class="fcard-tag tag-new">PAPER TRADING</span>
    </a>

    <a class="fcard" href="/operator/summary">
      <div class="fcard-icon">🎯</div>
      <div class="fcard-title">Operator Console</div>
      <div class="fcard-desc">Institutional-grade operator cockpit with full execution state, risk controls, and broker management.</div>
      <span class="fcard-tag tag-pro">OPERATOR ONLY</span>
    </a>

    <a class="fcard" href="/docs">
      <div class="fcard-icon">📖</div>
      <div class="fcard-title">Full API Documentation</div>
      <div class="fcard-desc">Interactive Swagger UI for all 50+ endpoints. Test live, view schemas, integrate with your stack.</div>
      <span class="fcard-tag tag-new">SWAGGER UI</span>
    </a>

    <a class="fcard" href="/api/live/gainers">
      <div class="fcard-icon">🚀</div>
      <div class="fcard-title">Movers &amp; Gainers</div>
      <div class="fcard-desc">Today's top gainers, losers, and most active stocks. Spot momentum before the crowd.</div>
      <span class="fcard-tag tag-live">LIVE MOVERS</span>
    </a>

    <a class="fcard" href="/pricing">
      <div class="fcard-icon">💎</div>
      <div class="fcard-title">Plans &amp; Pricing</div>
      <div class="fcard-desc">Starter free forever. Pro Trader $49/mo. Institutional $299/mo. All plans include real-time data and API access.</div>
      <span class="fcard-tag" style="background:rgba(245,158,11,0.15);color:#f59e0b;border-color:rgba(245,158,11,0.3)">VIEW PLANS</span>
    </a>

  </div>

</div>

<!-- FOOTER -->
<footer class="footer">
  <div class="footer-logo">QUANTORA</div>
  <p>Financial Intelligence OS &mdash; Built for Institutions. Used by Traders.</p>
  <p style="margin-top:8px">
    <a href="/pricing">Pricing</a> &middot;
    <a href="/signup">Sign Up</a> &middot;
    <a href="/login">Sign In</a> &middot;
    <a href="/docs">API Docs</a> &middot;
    <a href="/health">Health</a> &middot;
    <a href="/operator/health">Operator</a> &middot;
    <a href="/ui/">Panels</a>
  </p>
  <p style="margin-top:16px;color:#2d3f55">Paper trading only. Not financial advice. For informational purposes.</p>
</footer>

<script>
const B = window.location.origin;

// ── Auth nav update ──────────────────────────────────────────────────────────
(function() {
  const token = localStorage.getItem('q_token');
  const user = (() => { try { return JSON.parse(localStorage.getItem('q_user')||'null'); } catch(e){return null;} })();
  const signInBtn = document.getElementById('navSignIn');
  const getStartedBtn = document.getElementById('navGetStarted');
  if (token && user && signInBtn && getStartedBtn) {
    signInBtn.textContent = user.name ? user.name.split(' ')[0] : 'Account';
    signInBtn.href = '/auth/me';
    getStartedBtn.textContent = '⚡ Dashboard →';
    getStartedBtn.href = '/ui/';
  }
})();

function fmt(n, decimals=2) {
  if (n == null || isNaN(n)) return '—';
  return Number(n).toLocaleString('en-US', {minimumFractionDigits: decimals, maximumFractionDigits: decimals});
}
function fmtBig(n) {
  if (!n) return '—';
  if (n >= 1e12) return '$' + (n/1e12).toFixed(2) + 'T';
  if (n >= 1e9) return '$' + (n/1e9).toFixed(2) + 'B';
  if (n >= 1e6) return '$' + (n/1e6).toFixed(2) + 'M';
  return '$' + fmt(n);
}
function chgHtml(pct) {
  if (pct == null) return '<span style="color:var(--muted)">—</span>';
  const up = pct >= 0;
  return `<span class="${up?'up':'dn'}">${up?'▲':'▼'} ${Math.abs(pct).toFixed(2)}%</span>`;
}

// ── Ticker ─────────────────────────────────────────────────────────────────
async function loadTicker() {
  try {
    const syms = ['SPY','QQQ','AAPL','MSFT','NVDA','TSLA','AMZN','GOOGL'];
    const r = await fetch(`${B}/api/live/quotes?symbols=${syms.join(',')}`);
    const data = await r.json();
    if (!Array.isArray(data)) return;

    let cryptoExtra = [];
    try {
      const cr = await fetch(`${B}/api/live/crypto`);
      const cd = await cr.json();
      const coins = cd.coins || cd;
      if (Array.isArray(coins)) {
        cryptoExtra = coins.slice(0,4).map(c => ({
          symbol: c.symbol?.toUpperCase(),
          price: c.price_usd || c.price,
          change_pct: c.change_24h_pct || c.change_pct,
        }));
      }
    } catch(e) {}

    const all = [...data, ...cryptoExtra];
    const html = [...all,...all].map(q => {
      const up = (q.change_pct||0) >= 0;
      return `<span class="tick-item"><span class="tick-sym">${q.symbol}</span><span class="tick-price">$${fmt(q.price)}</span><span class="${up?'up':'dn'}">${up?'▲':'▼'}${Math.abs(q.change_pct||0).toFixed(2)}%</span></span>`;
    }).join('');
    document.getElementById('tickerScroll').innerHTML = html;
  } catch(e) {}
}

// ── Market Status ───────────────────────────────────────────────────────────
async function loadStatus() {
  try {
    const r = await fetch(`${B}/api/live/status`);
    const d = await r.json();
    const s = d.status || 'UNKNOWN';
    const el = document.getElementById('mktStatus');
    const isOpen = s.includes('OPEN');
    const isAfter = s.includes('AFTER') || s.includes('PRE');
    el.innerHTML = `<span style="color:${isOpen?'var(--green)':isAfter?'var(--gold)':'var(--red)'}">${s}</span>`;
    document.getElementById('mktTime').textContent = new Date().toLocaleTimeString('en-US', {timeZone:'America/New_York'}) + ' ET';
  } catch(e) {
    document.getElementById('mktStatus').textContent = 'CLOSED';
  }
}

// ── Market Quotes ────────────────────────────────────────────────────────────
const STOCK_META = {
  SPY:  {name:'S&P 500 ETF'},   QQQ:  {name:'Nasdaq 100 ETF'},
  AAPL: {name:'Apple Inc.'},    MSFT: {name:'Microsoft'},
  NVDA: {name:'Nvidia Corp.'},  TSLA: {name:'Tesla Inc.'},
  AMZN: {name:'Amazon.com'},    GOOGL:{name:'Alphabet Inc.'},
  META: {name:'Meta Platforms'}, JPM: {name:'JPMorgan Chase'},
};

async function loadMarket() {
  try {
    const syms = Object.keys(STOCK_META);
    const r = await fetch(`${B}/api/live/quotes?symbols=${syms.join(',')}`);
    const data = await r.json();
    if (!Array.isArray(data)) return;

    // Update market bar
    const spy = data.find(q=>q.symbol==='SPY');
    const qqq = data.find(q=>q.symbol==='QQQ');
    if (spy) {
      document.getElementById('spyVal').textContent = `$${fmt(spy.price)}`;
      document.getElementById('spyChg').innerHTML = chgHtml(spy.change_pct);
    }
    if (qqq) {
      document.getElementById('qqqVal').textContent = `$${fmt(qqq.price)}`;
      document.getElementById('qqqChg').innerHTML = chgHtml(qqq.change_pct);
    }

    // Update market grid
    const grid = document.getElementById('marketGrid');
    grid.innerHTML = data.map(q => {
      const up = (q.change_pct||0) >= 0;
      const meta = STOCK_META[q.symbol] || {};
      return `<div class="mcard" onclick="window.open('${B}/api/live/quotes?symbols=${q.symbol}','_blank')">
        <div class="mcard-sym">${q.symbol}</div>
        <div class="mcard-name">${meta.name||q.name||''}</div>
        <div class="mcard-price" style="color:${up?'var(--green)':'var(--red)'}">$${fmt(q.price)}</div>
        <div class="mcard-chg ${up?'up':'dn'}">${up?'▲':'▼'} ${Math.abs(q.change_pct||0).toFixed(2)}%</div>
        <div class="mcard-vol">Vol: ${q.volume ? fmtBig(q.volume).replace('$','') : '—'}</div>
      </div>`;
    }).join('');
    document.getElementById('chipMarket').className = 'api-chip chip-ok';
    document.getElementById('chipMarket').querySelector('.api-chip-dot').style.boxShadow = '0 0 6px var(--green)';
  } catch(e) {
    document.getElementById('chipMarket').className = 'api-chip chip-err';
  }
}

// ── Crypto ─────────────────────────────────────────────────────────────────
async function loadCrypto() {
  try {
    const r = await fetch(`${B}/api/live/crypto`);
    const d = await r.json();
    const coins = d.coins || d;
    if (!Array.isArray(coins)) return;
    const btc = coins.find(c=>c.symbol==='btc'||c.symbol==='BTC');
    if (btc) {
      document.getElementById('btcVal').textContent = `$${fmt(btc.price_usd||btc.price,0)}`;
      document.getElementById('btcChg').innerHTML = chgHtml(btc.change_24h_pct||btc.change_pct);
    }
    // Crypto vol
    const totalVol = coins.reduce((s,c)=>s+(c.volume_24h_usd||c.volume_24h||0),0);
    document.getElementById('cryptoVol').textContent = fmtBig(totalVol);
    document.getElementById('chipCrypto').className = 'api-chip chip-ok';
    document.getElementById('chipCrypto').querySelector('.api-chip-dot').style.boxShadow = '0 0 6px var(--green)';
  } catch(e) {
    document.getElementById('chipCrypto').className = 'api-chip chip-err';
  }
}

// ── Portfolio / Operator ────────────────────────────────────────────────────
async function loadPortfolio() {
  try {
    const r = await fetch(`${B}/operator/summary`);
    const d = await r.json();
    const cap = d.capital || {};
    const bal = cap.balance ?? cap.total_capital ?? 100000;
    const avail = cap.available ?? cap.cash_reserve ?? bal;
    const alloc = cap.allocated ?? cap.deployed_capital ?? 0;
    const pnl = (d.performance||{}).daily_pnl_value ?? 0;
    document.getElementById('totalCap').textContent = `$${fmt(bal,0)}`;
    document.getElementById('availCap').textContent = `$${fmt(avail,0)}`;
    document.getElementById('allocCap').textContent = `$${fmt(alloc,0)}`;
    document.getElementById('portVal').textContent = `$${fmt(bal,0)}`;
    document.getElementById('totalPnl').textContent = `${pnl>=0?'+':''}$${fmt(pnl,2)}`;
    document.getElementById('totalPnl').style.color = pnl>=0?'var(--green)':'var(--red)';
    document.getElementById('chipOperator').className = 'api-chip chip-ok';
    document.getElementById('chipOperator').querySelector('.api-chip-dot').style.boxShadow = '0 0 6px var(--green)';
  } catch(e) {
    document.getElementById('chipOperator').className = 'api-chip chip-err';
    // Fallback: show defaults
    document.getElementById('totalCap').textContent = '$100,000';
    document.getElementById('availCap').textContent = '$100,000';
    document.getElementById('allocCap').textContent = '$0';
    document.getElementById('totalPnl').textContent = '$0.00';
  }
}

// ── Init ───────────────────────────────────────────────────────────────────
async function init() {
  await Promise.all([loadTicker(), loadStatus(), loadMarket(), loadCrypto(), loadPortfolio()]);
}

init();
setInterval(loadTicker, 30000);
setInterval(loadStatus, 60000);
setInterval(loadMarket, 30000);
setInterval(loadCrypto, 30000);
setInterval(loadPortfolio, 60000);
</script>
</body>
</html>"""

# ── Startup hook ───────────────────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup():
    try:
        from backend.app.startup import initialize_state
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, initialize_state)
        logger.info("State initialization complete")
    except Exception as e:
        logger.warning(f"State init skipped: {e}")


# ==============================================================================
# BILLING, RATE-LIMITING & DASHBOARD — appended to run.py
# ==============================================================================

# ── DB migration: add billing columns ─────────────────────────────────────────
def _billing_migrate():
    c = _db()
    for col, tdef in [("stripe_customer_id", "TEXT"), ("stripe_subscription_id", "TEXT")]:
        try:
            c.execute(f"ALTER TABLE users ADD COLUMN {col} {tdef}")
            c.commit()
        except Exception:
            pass
    c.close()

_billing_migrate()

# ── Stripe API helpers (pure stdlib — no stripe package needed) ───────────────
import urllib.request as _urr
import urllib.parse   as _urp

_STRIPE_SK        = _os.environ.get("STRIPE_SECRET_KEY",       "")
_STRIPE_WHS       = _os.environ.get("STRIPE_WEBHOOK_SECRET",   "")
_STRIPE_CORE_PRICE = _os.environ.get("STRIPE_CORE_PRICE_ID",   "")
_STRIPE_PRO_PRICE  = _os.environ.get("STRIPE_PRO_PRICE_ID",    "")
_STRIPE_EXEC_PRICE = _os.environ.get("STRIPE_EXEC_PRICE_ID",   "")
_STRIPE_PK        = _os.environ.get("STRIPE_PUBLISHABLE_KEY",  "")
_APP_URL          = _os.environ.get("APP_URL", "https://web-production-fe9f5.up.railway.app")

PLAN_ORDER = {"starter": 0, "core": 1, "pro": 2, "execution": 3, "firm": 4, "institutional": 5}
PLAN_PRICES = {
    "core":      _STRIPE_CORE_PRICE,
    "pro":       _STRIPE_PRO_PRICE,
    "execution": _STRIPE_EXEC_PRICE,
}

def _stripe_req(method: str, path: str, data: dict | None = None) -> dict:
    url  = f"https://api.stripe.com/v1{path}"
    body = _urp.urlencode(data or {}).encode() if data else None
    req  = _urr.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Bearer {_STRIPE_SK}")
    if body:
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with _urr.urlopen(req, timeout=10) as resp:
            return _jn.loads(resp.read())
    except _urr.HTTPError as exc:
        try:
            return {"error": _jn.loads(exc.read()).get("error", {"message": str(exc)})}
        except Exception:
            return {"error": {"message": str(exc)}}
    except Exception as exc:
        return {"error": {"message": str(exc)}}

def _stripe_verify_sig(payload: bytes, sig_header: str, secret: str) -> bool:
    try:
        t = ""; sigs: list[str] = []
        for part in sig_header.split(","):
            k, _, v = part.partition("=")
            if k == "t": t = v
            elif k == "v1": sigs.append(v)
        if not t: return False
        signed   = f"{t}.{payload.decode()}".encode()
        expected = _hm.new(secret.encode(), signed, _hl.sha256).hexdigest()
        return expected in sigs
    except Exception:
        return False

def _get_or_create_stripe_customer(email: str, name: str) -> str | None:
    c   = _db()
    row = c.execute("SELECT stripe_customer_id FROM users WHERE email=?", (email,)).fetchone()
    c.close()
    if row and row["stripe_customer_id"]:
        return row["stripe_customer_id"]
    result = _stripe_req("POST", "/customers", {"email": email, "name": name})
    if "error" in result: return None
    cid = result["id"]
    c   = _db()
    c.execute("UPDATE users SET stripe_customer_id=? WHERE email=?", (cid, email))
    c.commit(); c.close()
    return cid

# ── Rate limiting (in-memory, per-IP) ─────────────────────────────────────────
import time as _rltime
_rl_buckets: dict = {}

def _rate_ok(key: str, limit: int = 10, window: int = 60) -> bool:
    now    = _rltime.time()
    bucket = [t for t in _rl_buckets.get(key, []) if now - t < window]
    if len(bucket) >= limit:
        _rl_buckets[key] = bucket
        return False
    bucket.append(now)
    _rl_buckets[key] = bucket
    return True

from starlette.middleware.base import BaseHTTPMiddleware as _BMH2
from starlette.responses import JSONResponse as _JR2

class _RateLimitMW(_BMH2):
    async def dispatch(self, request, call_next):
        if request.url.path in ("/auth/login", "/auth/register"):
            ip = (request.client.host if request.client else "unknown") or "unknown"
            if not _rate_ok(f"auth:{ip}", limit=10, window=60):
                return _JR2({"error": "Too many requests. Please wait a minute."}, status_code=429)
        return await call_next(request)

try:
    app.middleware_stack = None
    app.add_middleware(_RateLimitMW)
    logger.info("Rate limiting middleware active (10 auth req/min/IP)")
except Exception as _e:
    logger.warning(f"Rate limit middleware skipped: {_e}")

# ── Billing endpoints ─────────────────────────────────────────────────────────

class _CheckoutBody(_BM):
    plan: str
    annual: bool = False

@app.post("/billing/checkout")
async def billing_checkout(body: _CheckoutBody, request: _Req):
    if not _STRIPE_SK:
        return _JR({"error": "Billing not yet configured. Contact support."}, status_code=503)
    auth  = request.headers.get("Authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else ""
    email = _decode_token(token)
    if not email:
        return _JR({"error": "Unauthorized"}, status_code=401)

    plan     = body.plan.lower().strip()
    price_id = PLAN_PRICES.get(plan)
    if not price_id:
        return _JR({"error": f"Plan '{plan}' is not available via checkout. Contact sales."}, status_code=400)

    c    = _db()
    user = c.execute("SELECT name, plan FROM users WHERE email=?", (email,)).fetchone()
    c.close()
    if not user:
        return _JR({"error": "User not found."}, status_code=404)
    if PLAN_ORDER.get(user["plan"], 0) >= PLAN_ORDER.get(plan, 0):
        return _JR({"error": f"Already on {user['plan']} or higher."}, status_code=400)

    cid = _get_or_create_stripe_customer(email, user["name"])
    if not cid:
        return _JR({"error": "Failed to create billing account."}, status_code=500)

    session = _stripe_req("POST", "/checkout/sessions", {
        "customer":                cid,
        "mode":                    "subscription",
        "line_items[0][price]":    price_id,
        "line_items[0][quantity]": "1",
        "success_url":             f"{_APP_URL}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url":              f"{_APP_URL}/pricing",
        "metadata[plan]":          plan,
        "metadata[email]":         email,
        "allow_promotion_codes":   "true",
    })
    if "error" in session:
        return _JR({"error": session["error"]["message"]}, status_code=500)
    return {"url": session["url"]}

@app.get("/billing/success")
async def billing_success(session_id: str = ""):
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/dashboard?upgraded=1")

@app.post("/billing/webhook")
async def billing_webhook(request: _Req):
    payload = await request.body()
    sig     = request.headers.get("stripe-signature", "")
    if _STRIPE_WHS and not _stripe_verify_sig(payload, sig, _STRIPE_WHS):
        return _JR({"error": "Invalid signature"}, status_code=400)
    try:
        event = _jn.loads(payload)
    except Exception:
        return _JR({"error": "Bad payload"}, status_code=400)

    etype = event.get("type", "")
    obj   = event.get("data", {}).get("object", {})

    if etype == "checkout.session.completed":
        meta  = obj.get("metadata", {})
        email = meta.get("email", "").lower()
        plan  = meta.get("plan", "")
        sub   = obj.get("subscription", "")
        if email and plan:
            c = _db()
            c.execute("UPDATE users SET plan=?, stripe_subscription_id=? WHERE email=?",
                      (plan, sub, email))
            c.commit(); c.close()
            logger.info(f"Webhook upgrade: {email} → {plan}")

    elif etype in ("customer.subscription.deleted", "customer.subscription.updated"):
        status = obj.get("status", "")
        cid    = obj.get("customer", "")
        if etype == "customer.subscription.deleted" or status in ("canceled", "unpaid", "past_due"):
            c = _db()
            c.execute(
                "UPDATE users SET plan='starter', stripe_subscription_id=NULL WHERE stripe_customer_id=?",
                (cid,)
            )
            c.commit(); c.close()
            logger.info(f"Webhook downgrade: customer {cid} → starter")

    return {"received": True}

@app.post("/billing/portal")
async def billing_portal(request: _Req):
    if not _STRIPE_SK:
        return _JR({"error": "Billing not configured."}, status_code=503)
    auth  = request.headers.get("Authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else ""
    email = _decode_token(token)
    if not email:
        return _JR({"error": "Unauthorized"}, status_code=401)
    c   = _db()
    row = c.execute("SELECT stripe_customer_id FROM users WHERE email=?", (email,)).fetchone()
    c.close()
    cid = row["stripe_customer_id"] if row else None
    if not cid:
        return _JR({"error": "No active subscription found."}, status_code=404)
    portal = _stripe_req("POST", "/billing_portal/sessions", {
        "customer":   cid,
        "return_url": f"{_APP_URL}/dashboard",
    })
    if "error" in portal:
        return _JR({"error": portal["error"]["message"]}, status_code=500)
    return {"url": portal["url"]}

class _ContactBody(_BM):
    name: str
    email: str
    org: str = ""
    tier: str = "firm"
    message: str = ""

@app.post("/billing/contact")
async def billing_contact(body: _ContactBody):
    logger.info(f"Sales inquiry: {body.tier} from {body.email} ({body.org}) — {body.message[:100]}")
    return {"received": True, "message": "Thank you. We will be in touch within 24 hours."}

@app.get("/billing/plans")
async def billing_plans():
    return {"plans": [
        {"id":"core",      "name":"Quantora Core",        "price":79,    "price_display":"$79/mo",    "highlighted":False, "cta":"Start with Core"},
        {"id":"pro",       "name":"Quantora Pro",         "price":199,   "price_display":"$199/mo",   "highlighted":False, "cta":"Upgrade to Pro"},
        {"id":"execution", "name":"Quantora Execution",   "price":499,   "price_display":"$499/mo",   "highlighted":True,  "cta":"Start Execution"},
        {"id":"firm",      "name":"Quantora Firm",        "price":2500,  "price_display":"$2,500/mo", "highlighted":False, "cta":"Contact Sales"},
        {"id":"institutional","name":"Quantora Institutional","price":None,"price_display":"Custom",  "highlighted":False, "cta":"Request Proposal"},
    ]}

@app.get("/billing/config")
async def billing_config():
    """Return public Stripe key for frontend use."""
    return {"publishable_key": _STRIPE_PK, "configured": bool(_STRIPE_SK)}

# ── Dashboard page ─────────────────────────────────────────────────────────────
@app.get("/dashboard")
def dashboard_page():
    p = _os.path.join(_os.path.dirname(__file__), "frontend", "dashboard.html")
    try:
        with open(p, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/ui/")
