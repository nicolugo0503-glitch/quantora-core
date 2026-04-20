
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import uuid, math

app = FastAPI(title="QNT30411 Performance Engine")

TRADES = []
EQUITY = 10000.0

class Trade(BaseModel):
    symbol: str
    pnl: float

@app.post("/performance/trade")
def add_trade(t: Trade):
    global EQUITY
    trade_id = str(uuid.uuid4())
    TRADES.append({"id":trade_id,"symbol":t.symbol,"pnl":t.pnl})
    EQUITY += t.pnl
    return {"status":"ok","equity":EQUITY}

@app.get("/performance/summary")
def summary():
    if not TRADES:
        return {"equity":EQUITY,"pnl":0,"sharpe":0,"win_rate":0}
    pnls=[t["pnl"] for t in TRADES]
    total=sum(pnls)
    wins=len([p for p in pnls if p>0])
    mean= sum(pnls)/len(pnls)
    std = math.sqrt(sum([(p-mean)**2 for p in pnls])/len(pnls)) if len(pnls)>1 else 0
    sharpe = (mean/std) if std>0 else 0
    return {
        "equity":EQUITY,
        "pnl":total,
        "sharpe":round(sharpe,2),
        "win_rate":round(wins/len(pnls),2)
    }
