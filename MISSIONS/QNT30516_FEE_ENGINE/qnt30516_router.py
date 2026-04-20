from fastapi import APIRouter
from pydantic import BaseModel


class FeeCalcRequest(BaseModel):
    fund_id: str
    nav: float
    pnl: float


def build_qnt30516_router(engine):
    router = APIRouter(tags=["QNT30516 Fees"])

    @router.post("/api/fees/calculate")
    def calculate(payload: FeeCalcRequest):
        return engine.calculate_fees(payload.fund_id, payload.nav, payload.pnl)

    @router.get("/api/fees")
    def fees():
        return engine.get_ledger()

    return router
