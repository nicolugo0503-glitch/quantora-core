from fastapi import FastAPI
from pydantic import BaseModel
app = FastAPI(title="QNT30380 Regime-Aware Capital Allocation")
class Context(BaseModel):
    volatility: float
    execution_quality: float
    strategy_score: float
state = {"last_allocation": 0.5, "regime": "neutral"}
@app.get("/allocation/status")
def status():
    return state
@app.post("/allocation/decide")
def decide(ctx: Context):
    if ctx.volatility > 0.7:
        regime = "high_vol"; allocation = max(0.2, 1 - ctx.volatility)
    elif ctx.execution_quality < 0.4:
        regime = "poor_execution"; allocation = 0.3
    else:
        regime = "normal"; allocation = 0.5 + (ctx.strategy_score * 0.5)
    state["last_allocation"] = allocation; state["regime"] = regime
    return {"allocation": allocation, "regime": regime}
@app.post("/allocation/dispatch")
def dispatch():
    return {"status": "allocation dispatched", "state": state}
