from fastapi import APIRouter
from pydantic import BaseModel

class Metrics(BaseModel):
    strategy_id: int
    pnl: float
    drawdown: float
    sharpe: float

class ScoreReq(BaseModel):
    strategy_id: int

class TopReq(BaseModel):
    n: int = 5

def build_qnt30528_router(engine):
    r = APIRouter(tags=["QNT30528 Scoring"])

    @r.post("/api/scoring/update")
    def update(m: Metrics):
        return engine.update_metrics(m.strategy_id, m.pnl, m.drawdown, m.sharpe)

    @r.post("/api/scoring/compute")
    def compute(s: ScoreReq):
        return engine.compute_score(s.strategy_id)

    @r.get("/api/scoring/rank")
    def rank():
        return engine.rank()

    @r.post("/api/scoring/top")
    def top(t: TopReq):
        return engine.top(t.n)

    @r.get("/api/scoring/state")
    def state():
        return engine.state()

    return r
