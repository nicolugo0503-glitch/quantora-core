# QNT30513 — Treasury binding example
# Example only. Additive guidance, not auto-applied.

from fastapi import FastAPI

from MISSIONS.QNT30513_TREASURY_CASH_MANAGEMENT_LAYER.qnt30513_treasury_engine import QNT30513TreasuryEngine
from MISSIONS.QNT30513_TREASURY_CASH_MANAGEMENT_LAYER.qnt30513_treasury_router import build_qnt30513_router

app = FastAPI()

engine = QNT30513TreasuryEngine()
app.include_router(build_qnt30513_router(engine))
