from __future__ import annotations
from typing import Dict, List
from datetime import datetime

def _now():
    return datetime.utcnow().isoformat() + "Z"

def empty_state() -> Dict:
    return {
        "treasury_balance": 0.0,
        "investor_capital": [],
        "cash_movements": [],
        "fund_accounts": []
    }

def fund_summary(state: Dict) -> Dict:
    investors = state.get("investor_capital", [])
    inflows = sum(float(x.get("amount", 0)) for x in investors if x.get("status") == "active")
    pending = sum(float(x.get("amount", 0)) for x in investors if x.get("status") == "pending")
    withdrawals = sum(abs(float(x.get("amount", 0))) for x in state.get("cash_movements", []) if x.get("type") == "withdrawal")
    deposits = sum(float(x.get("amount", 0)) for x in state.get("cash_movements", []) if x.get("type") == "deposit")
    return {
        "timestamp": _now(),
        "treasury_balance": round(float(state.get("treasury_balance", 0.0)), 2),
        "active_investor_capital": round(inflows, 2),
        "pending_investor_capital": round(pending, 2),
        "deposits_total": round(deposits, 2),
        "withdrawals_total": round(withdrawals, 2),
        "net_capital_flow": round(deposits - withdrawals, 2),
        "active_investor_count": sum(1 for x in investors if x.get("status") == "active"),
        "pending_investor_count": sum(1 for x in investors if x.get("status") == "pending"),
        "fund_accounts_count": len(state.get("fund_accounts", [])),
    }

def add_investor_commitment(state: Dict, investor_name: str, amount: float, currency: str = "USD", status: str = "pending") -> Dict:
    rec = {
        "commitment_id": f"inv_{len(state.get('investor_capital', [])) + 1:04d}",
        "investor_name": investor_name,
        "amount": round(float(amount), 2),
        "currency": currency,
        "status": status,
        "created_at": _now(),
    }
    state.setdefault("investor_capital", []).append(rec)
    return rec

def record_cash_movement(state: Dict, movement_type: str, amount: float, note: str = "") -> Dict:
    signed_amount = round(float(amount), 2)
    rec = {
        "movement_id": f"mov_{len(state.get('cash_movements', [])) + 1:04d}",
        "type": movement_type,
        "amount": signed_amount,
        "note": note,
        "created_at": _now(),
    }
    state.setdefault("cash_movements", []).append(rec)
    if movement_type == "deposit":
        state["treasury_balance"] = round(float(state.get("treasury_balance", 0.0)) + signed_amount, 2)
    elif movement_type == "withdrawal":
        state["treasury_balance"] = round(float(state.get("treasury_balance", 0.0)) - abs(signed_amount), 2)
    return rec

def create_fund_account(state: Dict, name: str, strategy_scope: str = "general", base_currency: str = "USD") -> Dict:
    rec = {
        "fund_account_id": f"fund_{len(state.get('fund_accounts', [])) + 1:04d}",
        "name": name,
        "strategy_scope": strategy_scope,
        "base_currency": base_currency,
        "created_at": _now(),
    }
    state.setdefault("fund_accounts", []).append(rec)
    return rec
