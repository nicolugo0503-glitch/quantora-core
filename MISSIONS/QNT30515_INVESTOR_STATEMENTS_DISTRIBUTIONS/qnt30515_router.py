from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any


class StatementRequest(BaseModel):
    investor_id: str
    fund_id: str
    nav: float
    pnl: float


class DistributionRequest(BaseModel):
    investor_id: str
    fund_id: str
    amount: float


def build_qnt30515_router(engine: Any):
    router = APIRouter(tags=["QNT30515 Reporting"])

    @router.post("/api/reports/statements/create")
    def create_statement(payload: StatementRequest):
        return engine.generate_statement(payload.investor_id, payload.fund_id, payload.nav, payload.pnl)

    @router.post("/api/reports/distributions/create")
    def create_distribution(payload: DistributionRequest):
        return engine.create_distribution(payload.investor_id, payload.fund_id, payload.amount)

    @router.get("/api/reports")
    def reports():
        return engine.get_reports()

    return router
