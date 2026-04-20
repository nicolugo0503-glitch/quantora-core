# QNT30518 — Investor Onboarding + Subscription Workflow
# Additive mission module only. No existing core files modified.

from datetime import datetime, timezone
from typing import Dict, Any, List


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


class QNT30518InvestorOnboardingEngine:
    def __init__(self) -> None:
        self.onboarding_records: List[Dict[str, Any]] = []
        self.subscription_requests: List[Dict[str, Any]] = []

    def create_onboarding(
        self,
        investor_id: str,
        investor_name: str,
        email: str,
        fund_id: str,
        jurisdiction: str = "",
        status: str = "pending_review",
    ) -> Dict[str, Any]:
        row = {
            "timestamp": _ts(),
            "investor_id": investor_id,
            "investor_name": investor_name,
            "email": email,
            "fund_id": fund_id,
            "jurisdiction": jurisdiction,
            "status": status,
            "workflow_type": "onboarding",
        }
        self.onboarding_records.append(row)
        self.onboarding_records = self.onboarding_records[-1000:]
        return row

    def update_onboarding_status(self, index: int, status: str, note: str = "") -> Dict[str, Any]:
        if index < 0 or index >= len(self.onboarding_records):
            return {"ok": False, "error": "onboarding index out of range"}
        self.onboarding_records[index]["status"] = status
        self.onboarding_records[index]["status_updated_at"] = _ts()
        if note:
            self.onboarding_records[index]["note"] = note
        return {"ok": True, "row": self.onboarding_records[index]}

    def create_subscription_request(
        self,
        investor_id: str,
        fund_id: str,
        amount: float,
        currency: str = "USD",
        source: str = "manual",
    ) -> Dict[str, Any]:
        row = {
            "timestamp": _ts(),
            "investor_id": investor_id,
            "fund_id": fund_id,
            "amount": round(float(amount), 2),
            "currency": currency,
            "source": source,
            "status": "pending",
            "workflow_type": "subscription",
        }
        self.subscription_requests.append(row)
        self.subscription_requests = self.subscription_requests[-1000:]
        return row

    def approve_subscription(self, index: int, note: str = "") -> Dict[str, Any]:
        if index < 0 or index >= len(self.subscription_requests):
            return {"ok": False, "error": "subscription index out of range"}
        self.subscription_requests[index]["status"] = "approved"
        self.subscription_requests[index]["approved_at"] = _ts()
        if note:
            self.subscription_requests[index]["note"] = note
        return {"ok": True, "row": self.subscription_requests[index]}

    def reject_subscription(self, index: int, reason: str = "") -> Dict[str, Any]:
        if index < 0 or index >= len(self.subscription_requests):
            return {"ok": False, "error": "subscription index out of range"}
        self.subscription_requests[index]["status"] = "rejected"
        self.subscription_requests[index]["rejected_at"] = _ts()
        self.subscription_requests[index]["reason"] = reason
        return {"ok": True, "row": self.subscription_requests[index]}

    def get_summary(self, fund_id: str = "") -> Dict[str, Any]:
        onboardings = self.onboarding_records
        subscriptions = self.subscription_requests

        if fund_id:
            onboardings = [r for r in onboardings if r.get("fund_id") == fund_id]
            subscriptions = [r for r in subscriptions if r.get("fund_id") == fund_id]

        return {
            "timestamp": _ts(),
            "fund_id": fund_id,
            "onboardings": onboardings[-200:],
            "subscriptions": subscriptions[-200:],
            "onboarding_pending_count": sum(1 for r in onboardings if r.get("status") == "pending_review"),
            "onboarding_approved_count": sum(1 for r in onboardings if r.get("status") == "approved"),
            "subscription_pending_count": sum(1 for r in subscriptions if r.get("status") == "pending"),
            "subscription_approved_count": sum(1 for r in subscriptions if r.get("status") == "approved"),
            "subscription_rejected_count": sum(1 for r in subscriptions if r.get("status") == "rejected"),
        }
