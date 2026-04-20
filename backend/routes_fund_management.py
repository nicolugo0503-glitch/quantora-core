from fastapi import APIRouter
from .fund_management import empty_state, fund_summary, add_investor_commitment, record_cash_movement, create_fund_account

router = APIRouter()
_STATE = empty_state()

@router.get("/workspace/fund/summary")
def api_fund_summary():
    return fund_summary(_STATE)

@router.get("/workspace/fund/investors")
def api_fund_investors():
    return {"investors": _STATE.get("investor_capital", [])}

@router.post("/workspace/fund/investors/add")
def api_add_investor(payload: dict):
    rec = add_investor_commitment(
        _STATE,
        investor_name=payload.get("investor_name", "Unnamed Investor"),
        amount=float(payload.get("amount", 0)),
        currency=payload.get("currency", "USD"),
        status=payload.get("status", "pending"),
    )
    return {"status": "ok", "investor_commitment": rec, "summary": fund_summary(_STATE)}

@router.post("/workspace/fund/deposit")
def api_deposit(payload: dict):
    rec = record_cash_movement(_STATE, "deposit", float(payload.get("amount", 0)), payload.get("note", ""))
    return {"status": "ok", "movement": rec, "summary": fund_summary(_STATE)}

@router.post("/workspace/fund/withdraw")
def api_withdraw(payload: dict):
    rec = record_cash_movement(_STATE, "withdrawal", float(payload.get("amount", 0)), payload.get("note", ""))
    return {"status": "ok", "movement": rec, "summary": fund_summary(_STATE)}

@router.get("/workspace/fund/cash-movements")
def api_cash_movements():
    return {"cash_movements": _STATE.get("cash_movements", [])}

@router.post("/workspace/fund/accounts/create")
def api_create_fund_account(payload: dict):
    rec = create_fund_account(
        _STATE,
        name=payload.get("name", "General Fund Account"),
        strategy_scope=payload.get("strategy_scope", "general"),
        base_currency=payload.get("base_currency", "USD"),
    )
    return {"status": "ok", "fund_account": rec, "summary": fund_summary(_STATE)}

@router.get("/workspace/fund/accounts")
def api_fund_accounts():
    return {"fund_accounts": _STATE.get("fund_accounts", [])}
