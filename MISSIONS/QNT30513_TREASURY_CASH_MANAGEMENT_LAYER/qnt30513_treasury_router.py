# QNT30513 — Treasury router
# Additive mission module only. No existing core files modified.

from typing import Any, Dict

from fastapi import APIRouter
from pydantic import BaseModel


class TreasuryCashEventRequest(BaseModel):
    fund_id: str
    event_type: str
    amount: float
    note: str = ""


class TreasuryReserveRequest(BaseModel):
    fund_id: str
    amount: float
    note: str = ""


def build_qnt30513_router(engine: Any) -> APIRouter:
    router = APIRouter(tags=["QNT30513 Treasury"])

    @router.post("/api/treasury/cash-event")
    def post_cash_event(payload: TreasuryCashEventRequest) -> Dict[str, Any]:
        return engine.record_cash_event(
            fund_id=payload.fund_id,
            event_type=payload.event_type,
            amount=payload.amount,
            note=payload.note,
        )

    @router.post("/api/treasury/reserve")
    def post_reserve(payload: TreasuryReserveRequest) -> Dict[str, Any]:
        return engine.reserve_cash(
            fund_id=payload.fund_id,
            amount=payload.amount,
            note=payload.note or "treasury reserve",
        )

    @router.post("/api/treasury/release")
    def post_release(payload: TreasuryReserveRequest) -> Dict[str, Any]:
        return engine.release_reserved_cash(
            fund_id=payload.fund_id,
            amount=payload.amount,
            note=payload.note or "treasury release",
        )

    @router.get("/api/treasury/summary")
    def get_summary(fund_id: str = "") -> Dict[str, Any]:
        return engine.get_cash_summary(fund_id=fund_id)

    @router.get("/api/treasury/ledger")
    def get_ledger(fund_id: str = "", limit: int = 200) -> Dict[str, Any]:
        return {
            "rows": engine.get_cash_ledger(fund_id=fund_id, limit=limit),
            "limit": limit,
            "fund_id": fund_id,
        }

    return router
