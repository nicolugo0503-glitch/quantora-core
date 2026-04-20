# QNT30514 — Capital Calls + Redemption Workflow
# Additive mission module only. No existing core files modified.

from datetime import datetime, timezone
from typing import Dict, Any, List


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


class QNT30514CapitalWorkflowEngine:
    def __init__(self) -> None:
        self.capital_calls: List[Dict[str, Any]] = []
        self.redemption_requests: List[Dict[str, Any]] = []
        self.last_summary: Dict[str, Any] = {}

    def create_capital_call(
        self,
        fund_id: str,
        investor_id: str,
        amount: float,
        due_date: str = "",
        note: str = "",
    ) -> Dict[str, Any]:
        row = {
            "timestamp": _ts(),
            "workflow_type": "capital_call",
            "status": "pending",
            "fund_id": fund_id,
            "investor_id": investor_id,
            "amount": round(float(amount), 2),
            "due_date": due_date,
            "note": note,
        }
        self.capital_calls.append(row)
        self.capital_calls = self.capital_calls[-1000:]
        return row

    def fulfill_capital_call(self, index: int) -> Dict[str, Any]:
        if index < 0 or index >= len(self.capital_calls):
            return {"ok": False, "error": "capital call index out of range"}
        self.capital_calls[index]["status"] = "fulfilled"
        self.capital_calls[index]["fulfilled_at"] = _ts()
        return {"ok": True, "row": self.capital_calls[index]}

    def create_redemption_request(
        self,
        fund_id: str,
        investor_id: str,
        amount: float,
        note: str = "",
    ) -> Dict[str, Any]:
        row = {
            "timestamp": _ts(),
            "workflow_type": "redemption",
            "status": "pending",
            "fund_id": fund_id,
            "investor_id": investor_id,
            "amount": round(float(amount), 2),
            "note": note,
        }
        self.redemption_requests.append(row)
        self.redemption_requests = self.redemption_requests[-1000:]
        return row

    def approve_redemption(self, index: int) -> Dict[str, Any]:
        if index < 0 or index >= len(self.redemption_requests):
            return {"ok": False, "error": "redemption index out of range"}
        self.redemption_requests[index]["status"] = "approved"
        self.redemption_requests[index]["approved_at"] = _ts()
        return {"ok": True, "row": self.redemption_requests[index]}

    def reject_redemption(self, index: int, reason: str = "") -> Dict[str, Any]:
        if index < 0 or index >= len(self.redemption_requests):
            return {"ok": False, "error": "redemption index out of range"}
        self.redemption_requests[index]["status"] = "rejected"
        self.redemption_requests[index]["rejected_at"] = _ts()
        self.redemption_requests[index]["rejection_reason"] = reason
        return {"ok": True, "row": self.redemption_requests[index]}

    def get_workflow_summary(self, fund_id: str = "") -> Dict[str, Any]:
        calls = self.capital_calls
        reds = self.redemption_requests

        if fund_id:
            calls = [r for r in calls if r.get("fund_id") == fund_id]
            reds = [r for r in reds if r.get("fund_id") == fund_id]

        summary = {
            "timestamp": _ts(),
            "fund_id": fund_id,
            "capital_calls": calls[-200:],
            "redemptions": reds[-200:],
            "capital_call_pending_count": sum(1 for r in calls if r.get("status") == "pending"),
            "capital_call_fulfilled_count": sum(1 for r in calls if r.get("status") == "fulfilled"),
            "redemption_pending_count": sum(1 for r in reds if r.get("status") == "pending"),
            "redemption_approved_count": sum(1 for r in reds if r.get("status") == "approved"),
            "redemption_rejected_count": sum(1 for r in reds if r.get("status") == "rejected"),
        }
        self.last_summary = summary
        return summary
