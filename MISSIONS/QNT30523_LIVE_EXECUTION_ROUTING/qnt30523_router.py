
from fastapi import APIRouter
from pydantic import BaseModel

class ExecRequest(BaseModel):
    orders: list
    live: bool = False

def build_qnt30523_router(engine):
    r = APIRouter(tags=["QNT30523 Execution"])

    @r.post("/api/execution/run")
    def run_exec(req: ExecRequest):
        return engine.execute_orders(req.orders, req.live)

    @r.get("/api/execution/history")
    def hist():
        return engine.get_executions()

    return r
