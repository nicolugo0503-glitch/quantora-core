import os
import requests
from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path

app = FastAPI(title="Quantora Alpaca Fix V2", version="2.0.0")

BASE_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = BASE_DIR / "frontend"

def alpaca_headers():
    return {
        "APCA-API-KEY-ID": os.getenv("ALPACA_API_KEY", ""),
        "APCA-API-SECRET-KEY": os.getenv("ALPACA_SECRET_KEY", ""),
    }

def alpaca_base_url():
    return os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets").rstrip("/")

@app.get("/health")
def health():
    return {"status": "ok", "service": "quantora-core", "layer": "alpaca-fix-v2"}

@app.get("/alpaca/status")
def alpaca_status():
    key = os.getenv("ALPACA_API_KEY")
    secret = os.getenv("ALPACA_SECRET_KEY")
    base = alpaca_base_url()

    if not key or not secret:
        return {
            "connected": False,
            "error": "Missing ALPACA_API_KEY or ALPACA_SECRET_KEY",
            "base_url": base,
        }

    try:
        r = requests.get(f"{base}/v2/account", headers=alpaca_headers(), timeout=15)
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
    key = os.getenv("ALPACA_API_KEY")
    secret = os.getenv("ALPACA_SECRET_KEY")
    base = alpaca_base_url()

    if not key or not secret:
        return JSONResponse(
            {"error": "Missing ALPACA_API_KEY or ALPACA_SECRET_KEY", "base_url": base},
            status_code=400,
        )

    r = requests.get(f"{base}/v2/account", headers=alpaca_headers(), timeout=15)
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
        "message": "Quantora Alpaca Fix V2 live",
        "health": "/health",
        "alpaca_status": "/alpaca/status",
    }
