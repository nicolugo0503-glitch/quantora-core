# QNT30518 — Onboarding + subscription router
# Additive mission module only. No existing core files modified.

from typing import Any, Dict

from fastapi import APIRouter
from pydantic import BaseModel


class OnboardingCreateRequest(BaseModel):
    investor_id: str
    investor_name: str
    email: str
    fund_id: str
    jurisdiction: str = ""
    status: str = "pending_review"


class OnboardingStatusRequest(BaseModel):
    index: int
    status: str
    note: str = ""


class SubscriptionCreateRequest(BaseModel):
    investor_id: str
    fund_id: str
    amount: float
    currency: str = "USD"
    source: str = "manual"


class WorkflowIndexRequest(BaseModel):
    index: int
    note: str = ""
    reason: str = ""


def build_qnt30518_router(engine: Any) -> APIRouter:
    router = APIRouter(tags=["QNT30518 Onboarding"])

    @router.post("/api/onboarding/create")
    def post_onboarding(payload: OnboardingCreateRequest) -> Dict[str, Any]:
        return engine.create_onboarding(
            investor_id=payload.investor_id,
            investor_name=payload.investor_name,
            email=payload.email,
            fund_id=payload.fund_id,
            jurisdiction=payload.jurisdiction,
            status=payload.status,
        )

    @router.post("/api/onboarding/status")
    def post_onboarding_status(payload: OnboardingStatusRequest) -> Dict[str, Any]:
        return engine.update_onboarding_status(
            index=payload.index,
            status=payload.status,
            note=payload.note,
        )

    @router.post("/api/subscription/request")
    def post_subscription_request(payload: SubscriptionCreateRequest) -> Dict[str, Any]:
        return engine.create_subscription_request(
            investor_id=payload.investor_id,
            fund_id=payload.fund_id,
            amount=payload.amount,
            currency=payload.currency,
            source=payload.source,
        )

    @router.post("/api/subscription/approve")
    def post_subscription_approve(payload: WorkflowIndexRequest) -> Dict[str, Any]:
        return engine.approve_subscription(index=payload.index, note=payload.note)

    @router.post("/api/subscription/reject")
    def post_subscription_reject(payload: WorkflowIndexRequest) -> Dict[str, Any]:
        return engine.reject_subscription(index=payload.index, reason=payload.reason)

    @router.get("/api/onboarding/summary")
    def get_summary(fund_id: str = "") -> Dict[str, Any]:
        return engine.get_summary(fund_id=fund_id)

    return router
