from fastapi import FastAPI
from MISSIONS.QNT30533_SIGNAL_ENGINE.qnt30533_signal_engine import QNT30533SignalEngine
from MISSIONS.QNT30533_SIGNAL_ENGINE.qnt30533_router import build_qnt30533_router

app = FastAPI()
engine = QNT30533SignalEngine()
app.include_router(build_qnt30533_router(engine))
