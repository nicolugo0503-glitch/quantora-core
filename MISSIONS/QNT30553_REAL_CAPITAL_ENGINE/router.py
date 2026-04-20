
from fastapi import APIRouter
from .capital_engine import get_capital, deposit, withdraw

router = APIRouter()

@router.get("/capital")
def capital():
    return get_capital()

@router.post("/deposit")
def dep(payload: dict):
    return deposit(payload.get("amount",0))

@router.post("/withdraw")
def wd(payload: dict):
    return withdraw(payload.get("amount",0))
