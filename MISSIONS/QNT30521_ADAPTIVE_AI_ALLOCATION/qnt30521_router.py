
from fastapi import APIRouter
from pydantic import BaseModel

class Perf(BaseModel):
    asset: str
    pnl: float

class Capital(BaseModel):
    capital: float

def build_qnt30521_router(engine):
    r = APIRouter(tags=["QNT30521 AI"])

    @r.post("/api/ai/update")
    def update(p: Perf):
        return engine.update_performance(p.asset, p.pnl)

    @r.post("/api/ai/allocate")
    def alloc(c: Capital):
        return engine.adaptive_allocate(c.capital)

    @r.get("/api/ai/state")
    def state():
        return engine.get_state()

    return r
