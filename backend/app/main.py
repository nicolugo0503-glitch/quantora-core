import os
import requests
from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path

app = FastAPI(title="Quantora Alpaca Fix V3", version="3.0.0")

BASE_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = BASE_DIR / "frontend"

def first_nonempty(*names):
    for name in names:
        value = os.getenv(name)
        if value and str(value).strip():
            return str(value).strip()
    return None

def alpaca_key():
    return first_nonempty("ALPACA_API_KEY", "APCA_API_KEY_ID", "ALPACA_KEY")

def alpaca_secret():
    return first_nonempty("ALPACA_SECRET_KEY", "APCA_API_SECRET_KEY", "ALPACA_SECRET")

def alpaca_base_url():
    return first_nonempty("ALPACA_BASE_URL") or "https://paper-api.alpaca.markets"

def alpaca_headers():
    return {
        "APCA-API-KEY-ID": alpaca_key() or "",
        "APCA-API-SECRET-KEY": alpaca_secret() or "",
    }

@app.get("/health")
def health():
    return {"status": "ok", "service": "quantora-core", "layer": "alpaca-fix-v3"}

@app.get("/debug/env")
def debug_env():
    visible = {
        "ALPACA_API_KEY": bool(os.getenv("ALPACA_API_KEY")),
        "ALPACA_SECRET_KEY": bool(os.getenv("ALPACA_SECRET_KEY")),
        "ALPACA_BASE_URL": bool(os.getenv("ALPACA_BASE_URL")),
        "APCA_API_KEY_ID": bool(os.getenv("APCA_API_KEY_ID")),
        "APCA_API_SECRET_KEY": bool(os.getenv("APCA_API_SECRET_KEY")),
        "resolved_key": bool(alpaca_key()),
        "resolved_secret": bool(alpaca_secret()),
        "resolved_base_url": alpaca_base_url(),
    }
    return visible

@app.get("/alpaca/status")
def alpaca_status():
    key = alpaca_key()
    secret = alpaca_secret()
    base = alpaca_base_url().rstrip("/")

    if not key or not secret:
        return {
            "connected": False,
            "error": "Missing Alpaca credentials in runtime environment",
            "base_url": base,
            "debug": {
                "ALPACA_API_KEY": bool(os.getenv("ALPACA_API_KEY")),
                "ALPACA_SECRET_KEY": bool(os.getenv("ALPACA_SECRET_KEY")),
                "APCA_API_KEY_ID": bool(os.getenv("APCA_API_KEY_ID")),
                "APCA_API_SECRET_KEY": bool(os.getenv("APCA_API_SECRET_KEY")),
            },
        }

    try:
        r = requests.get(f"{base}/v2/account", headers=alpaca_headers(), timeout=20)
        try:
            body = r.json()
        except Exception:
            body = {"raw": r.text[:500]}
        return {
            "connected": r.status_code == 200,
            "status_code": r.status_code,
            "base_url": base,
            "response": body,
        }
    except Exception as e:
        return {"connected": False, "base_url": base, "error": str(e)}

@app.get("/alpaca/account")
def alpaca_account():
    key = alpaca_key()
    secret = alpaca_secret()
    base = alpaca_base_url().rstrip("/")

    if not key or not secret:
        return JSONResponse(
            {
                "error": "Missing Alpaca credentials in runtime environment",
                "base_url": base,
                "debug": {
                    "ALPACA_API_KEY": bool(os.getenv("ALPACA_API_KEY")),
                    "ALPACA_SECRET_KEY": bool(os.getenv("ALPACA_SECRET_KEY")),
                    "APCA_API_KEY_ID": bool(os.getenv("APCA_API_KEY_ID")),
                    "APCA_API_SECRET_KEY": bool(os.getenv("APCA_API_SECRET_KEY")),
                },
            },
            status_code=400,
        )

    r = requests.get(f"{base}/v2/account", headers=alpaca_headers(), timeout=20)
    try:
        return JSONResponse(r.json(), status_code=r.status_code)
    except Exception:
        return JSONResponse({"raw": r.text[:1000]}, status_code=r.status_code)

@app.get("/")
def root():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return {
        "status": "ok",
        "message": "Quantora Alpaca Fix V3 live",
        "health": "/health",
        "debug_env": "/debug/env",
        "alpaca_status": "/alpaca/status",
    }
