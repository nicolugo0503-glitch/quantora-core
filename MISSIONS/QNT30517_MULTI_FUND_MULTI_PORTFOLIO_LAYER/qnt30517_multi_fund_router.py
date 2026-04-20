# QNT30517 — Multi-fund router
# Additive mission module only. No existing core files modified.

from typing import Any, Dict

from fastapi import APIRouter
from pydantic import BaseModel


class FundCreateRequest(BaseModel):
    fund_id: str
    name: str
    base_currency: str = "USD"
    status: str = "active"


class PortfolioCreateRequest(BaseModel):
    portfolio_id: str
    fund_id: str
    name: str
    mandate: str = ""


class AllocationSetRequest(BaseModel):
    fund_id: str
    portfolio_id: str
    target_pct: float
    note: str = ""


def build_qnt30517_router(engine: Any) -> APIRouter:
    router = APIRouter(tags=["QNT30517 Multi Fund"])

    @router.post("/api/multifund/fund")
    def post_fund(payload: FundCreateRequest) -> Dict[str, Any]:
        return engine.create_fund(
            fund_id=payload.fund_id,
            name=payload.name,
            base_currency=payload.base_currency,
            status=payload.status,
        )

    @router.post("/api/multifund/portfolio")
    def post_portfolio(payload: PortfolioCreateRequest) -> Dict[str, Any]:
        return engine.create_portfolio(
            portfolio_id=payload.portfolio_id,
            fund_id=payload.fund_id,
            name=payload.name,
            mandate=payload.mandate,
        )

    @router.post("/api/multifund/allocation")
    def post_allocation(payload: AllocationSetRequest) -> Dict[str, Any]:
        return engine.set_portfolio_allocation(
            fund_id=payload.fund_id,
            portfolio_id=payload.portfolio_id,
            target_pct=payload.target_pct,
            note=payload.note,
        )

    @router.get("/api/multifund/summary")
    def get_summary(fund_id: str = "") -> Dict[str, Any]:
        return engine.get_summary(fund_id=fund_id)

    return router
