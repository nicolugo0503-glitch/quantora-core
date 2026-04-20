# QNT30517 — Multi-fund binding example
# Example only. Additive guidance, not auto-applied.

from fastapi import FastAPI

from MISSIONS.QNT30517_MULTI_FUND_MULTI_PORTFOLIO_LAYER.qnt30517_multi_fund_engine import QNT30517MultiFundEngine
from MISSIONS.QNT30517_MULTI_FUND_MULTI_PORTFOLIO_LAYER.qnt30517_multi_fund_router import build_qnt30517_router

app = FastAPI()

engine = QNT30517MultiFundEngine()
app.include_router(build_qnt30517_router(engine))
