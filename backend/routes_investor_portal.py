from fastapi import APIRouter
from .investor_portal import investor_portal_summary, capital_statement

router = APIRouter()

@router.get("/workspace/investor/portal")
def api_investor_portal():
    return investor_portal_summary()

@router.get("/workspace/investor/statement")
def api_investor_statement():
    return capital_statement("Founding LP", 250000, 50000, "active")
