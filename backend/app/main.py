from fastapi import FastAPI, APIRouter
import os
import requests

app = FastAPI()

alpaca_router = APIRouter()

ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

HEADERS = {
    "APCA-API-KEY-ID": ALPACA_API_KEY,
    "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY
}

@app.get("/health")
def health():
    return {"status": "ok"}

@alpaca_router.get("/alpaca/status")
def alpaca_status():
    try:
        r = requests.get(f"{ALPACA_BASE_URL}/v2/account", headers=HEADERS)
        return {
            "connected": r.status_code == 200,
            "status_code": r.status_code
        }
    except Exception as e:
        return {"connected": False, "error": str(e)}

@alpaca_router.get("/alpaca/account")
def alpaca_account():
    r = requests.get(f"{ALPACA_BASE_URL}/v2/account", headers=HEADERS)
    return r.json()

app.include_router(alpaca_router)
