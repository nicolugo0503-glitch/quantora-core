from fastapi import APIRouter
from pydantic import BaseModel

class AllocateRequest(BaseModel):
    fund_id: str
    capital: float
    signals: dict

def build_qnt30520_router(engine):
    router = APIRouter(tags=["QNT30520 Allocation"])

    @router.post("/api/allocation/run")
    def run_alloc(payload: AllocateRequest):
        return engine.allocate(payload.fund_id, payload.capital, payload.signals)

    @router.get("/api/allocation/decisions")
    def decisions():
        return engine.get_decisions()

    return router