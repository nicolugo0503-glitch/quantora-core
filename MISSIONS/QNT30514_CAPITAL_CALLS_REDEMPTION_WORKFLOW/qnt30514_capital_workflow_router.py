# QNT30514 — Capital workflow router
# Additive mission module only. No existing core files modified.

from typing import Any, Dict

from fastapi import APIRouter
from pydantic import BaseModel


class CapitalCallRequest(BaseModel):
    fund_id: str
    investor_id: str
    amount: float
    due_date: str = ""
    note: str = ""


class RedemptionRequest(BaseModel):
    fund_id: str
    investor_id: str
    amount: float
    note: str = ""


class WorkflowIndexRequest(BaseModel):
    index: int
    reason: str = ""


def build_qnt30514_router(engine: Any) -> APIRouter:
    router = APIRouter(tags=["QNT30514 Capital Workflow"])

    @router.post("/api/capital/call")
    def post_capital_call(payload: CapitalCallRequest) -> Dict[str, Any]:
        return engine.create_capital_call(
            fund_id=payload.fund_id,
            investor_id=payload.investor_id,
            amount=payload.amount,
            due_date=payload.due_date,
            note=payload.note,
        )

    @router.post("/api/capital/call/fulfill")
    def post_fulfill_capital_call(payload: WorkflowIndexRequest) -> Dict[str, Any]:
        return engine.fulfill_capital_call(payload.index)

    @router.post("/api/redemption/request")
    def post_redemption_request(payload: RedemptionRequest) -> Dict[str, Any]:
        return engine.create_redemption_request(
            fund_id=payload.fund_id,
            investor_id=payload.investor_id,
            amount=payload.amount,
            note=payload.note,
        )

    @router.post("/api/redemption/approve")
    def post_approve_redemption(payload: WorkflowIndexRequest) -> Dict[str, Any]:
        return engine.approve_redemption(payload.index)

    @router.post("/api/redemption/reject")
    def post_reject_redemption(payload: WorkflowIndexRequest) -> Dict[str, Any]:
        return engine.reject_redemption(payload.index, reason=payload.reason)

    @router.get("/api/capital/summary")
    def get_capital_summary(fund_id: str = "") -> Dict[str, Any]:
        return engine.get_workflow_summary(fund_id=fund_id)

    return router
