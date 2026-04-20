from fastapi import FastAPI
from MISSIONS.QNT30534_PERFORMANCE_PNL_ENGINE.qnt30534_performance_engine import QNT30534PerformanceEngine
from MISSIONS.QNT30534_PERFORMANCE_PNL_ENGINE.qnt30534_router import build_qnt30534_router

app = FastAPI()
engine = QNT30534PerformanceEngine()
app.include_router(build_qnt30534_router(engine))
