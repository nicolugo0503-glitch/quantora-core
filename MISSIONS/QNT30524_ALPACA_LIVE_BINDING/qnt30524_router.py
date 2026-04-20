
from fastapi import APIRouter
from pydantic import BaseModel

class OrderRequest(BaseModel):
    orders: list

def build_qnt30524_router(engine):
    r = APIRouter(tags=["QNT30524 Alpaca"])

    @r.post("/api/alpaca/execute")
    def exec_orders(req: OrderRequest):
        return engine.execute_live(req.orders)

    @r.get("/api/alpaca/history")
    def hist():
        return engine.get_history()

    return r
