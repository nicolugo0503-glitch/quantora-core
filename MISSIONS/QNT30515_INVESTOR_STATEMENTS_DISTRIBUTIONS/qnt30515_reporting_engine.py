
# QNT30515 — Investor Statements + Distribution Notices

from datetime import datetime, timezone
from typing import Dict, Any, List

def _ts():
    return datetime.now(timezone.utc).isoformat()

class QNT30515InvestorReportingEngine:
    def __init__(self):
        self.statements = []
        self.distributions = []

    def generate_statement(self, investor_id: str, fund_id: str, nav: float, pnl: float):
        row = {
            "timestamp": _ts(),
            "investor_id": investor_id,
            "fund_id": fund_id,
            "nav": nav,
            "pnl": pnl
        }
        self.statements.append(row)
        return row

    def create_distribution(self, investor_id: str, fund_id: str, amount: float):
        row = {
            "timestamp": _ts(),
            "investor_id": investor_id,
            "fund_id": fund_id,
            "amount": amount,
            "status": "pending"
        }
        self.distributions.append(row)
        return row

    def get_reports(self):
        return {
            "statements": self.statements[-100:],
            "distributions": self.distributions[-100:]
        }
