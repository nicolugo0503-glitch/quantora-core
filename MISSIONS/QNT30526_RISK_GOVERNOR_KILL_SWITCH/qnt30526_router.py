
from fastapi import APIRouter
from pydantic import BaseModel

class EvalReq(BaseModel):
    orders: list
    pnl: float = 0

def build_qnt30526_router(engine):
    r = APIRouter(tags=["QNT30526 Risk"])

    @r.post("/api/risk/evaluate")
    def eval(req: EvalReq):
        return engine.evaluate(req.orders, req.pnl)

    @r.post("/api/risk/kill")
    def kill():
        return engine.kill_switch()

    @r.post("/api/risk/reset")
    def reset():
        return engine.reset()

    @r.get("/api/risk/state")
    def state():
        return engine.get_state()

    return r
