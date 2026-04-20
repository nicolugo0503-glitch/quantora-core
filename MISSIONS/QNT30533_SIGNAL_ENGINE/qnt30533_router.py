from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, List

class SignalRequest(BaseModel):
    prices: Dict[str, List[float]] = {}
    universe: List[str] = ["BTCUSD", "ETHUSD", "SOLUSD"]

class TickRequest(BaseModel):
    fund_id: str = "FUND1"
    capital: float = 100000.0
    prices: Dict[str, List[float]] = {}
    universe: List[str] = ["BTCUSD", "ETHUSD", "SOLUSD"]
    dry_run: bool = True

def build_qnt30533_router(engine):
    r = APIRouter(tags=["QNT30533 Signal Engine"])

    @r.post("/api/signals/generate")
    def generate(req: SignalRequest):
        return engine.generate_signals(prices=req.prices, universe=req.universe)

    @r.post("/api/signals/build-tick")
    def build_tick(req: TickRequest):
        return engine.build_tick_payload(
            fund_id=req.fund_id,
            capital=req.capital,
            prices=req.prices,
            universe=req.universe,
            dry_run=req.dry_run,
        )

    @r.get("/api/signals/last")
    def last():
        return engine.get_last_signal()

    @r.get("/api/signals/history")
    def history():
        return engine.get_history()

    return r
