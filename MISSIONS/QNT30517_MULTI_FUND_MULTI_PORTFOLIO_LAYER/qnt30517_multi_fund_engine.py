# QNT30517 — Multi-Fund / Multi-Portfolio Layer
# Additive mission module only. No existing core files modified.

from datetime import datetime, timezone
from typing import Dict, Any, List


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


class QNT30517MultiFundEngine:
    def __init__(self) -> None:
        self.funds: List[Dict[str, Any]] = []
        self.portfolios: List[Dict[str, Any]] = []
        self.allocations: List[Dict[str, Any]] = []

    def create_fund(self, fund_id: str, name: str, base_currency: str = "USD", status: str = "active") -> Dict[str, Any]:
        row = {
            "timestamp": _ts(),
            "fund_id": fund_id,
            "name": name,
            "base_currency": base_currency,
            "status": status,
        }
        self.funds.append(row)
        self.funds = self.funds[-500:]
        return row

    def create_portfolio(self, portfolio_id: str, fund_id: str, name: str, mandate: str = "") -> Dict[str, Any]:
        row = {
            "timestamp": _ts(),
            "portfolio_id": portfolio_id,
            "fund_id": fund_id,
            "name": name,
            "mandate": mandate,
        }
        self.portfolios.append(row)
        self.portfolios = self.portfolios[-1000:]
        return row

    def set_portfolio_allocation(self, fund_id: str, portfolio_id: str, target_pct: float, note: str = "") -> Dict[str, Any]:
        row = {
            "timestamp": _ts(),
            "fund_id": fund_id,
            "portfolio_id": portfolio_id,
            "target_pct": round(float(target_pct), 4),
            "note": note,
        }
        self.allocations.append(row)
        self.allocations = self.allocations[-2000:]
        return row

    def get_funds(self) -> List[Dict[str, Any]]:
        return self.funds[-200:]

    def get_portfolios(self, fund_id: str = "") -> List[Dict[str, Any]]:
        rows = self.portfolios
        if fund_id:
            rows = [r for r in rows if r.get("fund_id") == fund_id]
        return rows[-500:]

    def get_allocations(self, fund_id: str = "") -> List[Dict[str, Any]]:
        rows = self.allocations
        if fund_id:
            rows = [r for r in rows if r.get("fund_id") == fund_id]
        return rows[-500:]

    def get_summary(self, fund_id: str = "") -> Dict[str, Any]:
        funds = self.get_funds()
        portfolios = self.get_portfolios(fund_id=fund_id)
        allocations = self.get_allocations(fund_id=fund_id)

        if fund_id:
            funds = [f for f in funds if f.get("fund_id") == fund_id]

        return {
            "timestamp": _ts(),
            "funds": funds,
            "portfolios": portfolios,
            "allocations": allocations,
            "fund_count": len(funds),
            "portfolio_count": len(portfolios),
            "allocation_count": len(allocations),
        }
