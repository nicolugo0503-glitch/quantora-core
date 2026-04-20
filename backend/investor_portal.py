from __future__ import annotations
from datetime import datetime

def _now():
    return datetime.utcnow().isoformat() + "Z"

def capital_statement(investor_name: str, committed: float, treasury_balance: float, status: str = "active") -> dict:
    nav = round(float(committed) * 1.0325, 2)
    pnl = round(nav - float(committed), 2)
    return {
        "timestamp": _now(),
        "investor_name": investor_name,
        "status": status,
        "committed_capital": round(float(committed), 2),
        "estimated_nav": nav,
        "estimated_pnl": pnl,
        "treasury_reference_balance": round(float(treasury_balance), 2),
        "statement_currency": "USD",
    }

def investor_portal_summary() -> dict:
    return {
        "timestamp": _now(),
        "portal_status": "ready",
        "active_investors": 1,
        "available_reports": [
            "capital_statement",
            "fund_summary",
            "cash_movements"
        ]
    }
