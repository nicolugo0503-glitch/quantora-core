
from fastapi import APIRouter
from pydantic import BaseModel

class Strat(BaseModel):
    name: str
    creator: str

class Alloc(BaseModel):
    strategy_id: int
    amount: float

def build_qnt30527_router(engine):
    r = APIRouter(tags=["QNT30527 Marketplace"])

    @r.post("/api/marketplace/strategy")
    def strat(s: Strat):
        return engine.register_strategy(s.name, s.creator)

    @r.post("/api/marketplace/allocate")
    def alloc(a: Alloc):
        return engine.allocate_capital(a.strategy_id, a.amount)

    @r.get("/api/marketplace/state")
    def state():
        return engine.get_state()

    return r
